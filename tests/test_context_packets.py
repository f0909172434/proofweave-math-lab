from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mathlab.context_packets import (
    TOKEN_BUDGETS,
    build_context_packet,
    check_context_packet,
    chunk_long_content,
    explain_context_packet,
)
from mathlab.errors import ValidationError


def _fact(fact_id: str, status: str, dependencies: list[str] | None = None) -> dict:
    return {
        "fact_id": fact_id,
        "title": f"Title {fact_id}",
        "kind": "lemma",
        "statement": f"Exact statement {fact_id}",
        "normalized_statement": f"normalized {fact_id}",
        "assumptions": [f"assumption {fact_id}"],
        "quantifiers": ["for every test input"],
        "mathematical_domain": "test",
        "proof": f"Proof {fact_id}",
        "dependencies": dependencies or [],
        "source_dependencies": [],
        "status": status,
        "verification_status": status,
    }


class ContextPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "agents").mkdir()
        (self.root / "state").mkdir()
        for relative in (
            "AGENTS.md",
            "docs/mathematical_quality_standard.md",
            "docs/agent_contracts.md",
            "docs/model_routing_guide.md",
        ):
            path = self.root / relative
            path.write_text(f"policy {relative}\n", encoding="utf-8")
        (self.root / "agents" / "theorem_verifier.md").write_text(
            "# theorem_verifier\nCold-start independent verification.\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _graph(self, facts: list[dict]) -> Path:
        path = self.root / "state" / "fact_graph.jsonl"
        path.write_text(
            "\n".join(json.dumps(fact, ensure_ascii=False) for fact in facts) + "\n",
            encoding="utf-8",
        )
        return path

    def _build(self, facts: list[dict], **kwargs: object) -> dict:
        graph = self._graph(facts)
        task = {"task_id": "t1", "target_fact_id": "target", "goal": "Audit it"}
        return build_context_packet(
            task,
            "theorem_verifier",
            graph,
            project_root=self.root,
            **kwargs,
        )

    def test_build_is_deterministic_and_content_addressed(self) -> None:
        facts = [_fact("dep", "VERIFIED"), _fact("target", "PROPOSED", ["dep"])]
        first = self._build(facts)
        second = self._build(facts)
        self.assertEqual(first, second)
        self.assertEqual(f"sha256:{first['packet_digest']}", first["packet_id"])
        self.assertEqual([], check_context_packet(first)["errors"])
        self.assertEqual("READY", check_context_packet(first)["status"])
        self.assertEqual("build/context-cache/" + first["cache_key"] + ".json", first["cache_path"])

    def test_verified_transitive_closure_has_exact_fields_but_not_proofs(self) -> None:
        facts = [
            _fact("root", "VERIFIED"),
            _fact("middle", "VERIFIED", ["root"]),
            _fact("target", "PROPOSED", ["middle"]),
        ]
        packet = self._build(facts)
        self.assertEqual(["middle", "root"], [item["fact_id"] for item in packet["verified_dependencies"]])
        self.assertEqual("Exact statement root", packet["verified_dependencies"][1]["statement"])
        self.assertEqual(["assumption root"], packet["verified_dependencies"][1]["assumptions"])
        self.assertEqual("VERIFIED", packet["verified_dependencies"][1]["status"])
        self.assertNotIn("proof", packet["verified_dependencies"][1])
        self.assertEqual("Proof target", packet["target_fact"]["proof"])

    def test_nonverified_dependency_is_excluded_and_requires_review(self) -> None:
        facts = [_fact("dep", "PROPOSED"), _fact("target", "PROPOSED", ["dep"])]
        packet = self._build(facts)
        self.assertEqual([], packet["verified_dependencies"])
        self.assertEqual("NEEDS_CONTEXT_REVIEW", packet["status"])
        self.assertTrue(any("not VERIFIED" in item["reason"] for item in packet["exclusions"]))
        self.assertEqual("NEEDS_CONTEXT_REVIEW", check_context_packet(packet)["status"])

    def test_secret_chat_cot_and_status_material_are_not_emitted(self) -> None:
        facts = [_fact("target", "PROPOSED")]
        status_path = self.root / "state" / "STATUS.md"
        status_path.write_text("must not appear", encoding="utf-8")
        task = {
            "target_fact_id": "target",
            "api_key": "sk-" + "supersecretvalue1234",
            "chat_history": ["private chat"],
            "chain_of_thought": "hidden steps",
        }
        packet = build_context_packet(
            task,
            "theorem_verifier",
            self._graph(facts),
            project_root=self.root,
            artifacts=[status_path],
        )
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn("supersecretvalue", serialized)
        self.assertNotIn("private chat", serialized)
        self.assertNotIn("hidden steps", serialized)
        self.assertNotIn("must not appear", serialized)
        self.assertIn("[REDACTED]", serialized)
        self.assertEqual([], check_context_packet(packet)["errors"])

    def test_all_material_inputs_change_cache_key(self) -> None:
        facts = [_fact("target", "PROPOSED")]
        artifact = self.root / "proof.md"
        artifact.write_text("version one", encoding="utf-8")
        first = self._build(facts, artifacts=[artifact])
        artifact.write_text("version two", encoding="utf-8")
        second = self._build(facts, artifacts=[artifact])
        self.assertNotEqual(first["cache_key"], second["cache_key"])
        self.assertNotEqual(first["packet_digest"], second["packet_digest"])

    def test_budget_overage_is_soft_and_never_truncates(self) -> None:
        facts = [_fact("target", "PROPOSED")]
        marker = "z" * 40_000
        packet = self._build(facts, artifacts=[marker], budget="fast")
        self.assertEqual(TOKEN_BUDGETS["fast"], packet["budget"]["limit_tokens"])
        self.assertGreater(packet["budget"]["estimated_tokens"], TOKEN_BUDGETS["fast"])
        self.assertEqual("NEEDS_CONTEXT_REVIEW", packet["status"])
        self.assertFalse(packet["budget"]["truncated"])
        self.assertIn(marker, packet["artifacts"][0]["content"])

    def test_markdown_task_and_explicit_sources_are_supported(self) -> None:
        facts = [_fact("target", "PROPOSED")]
        source = self.root / "source.md"
        source.write_text("opened source claim", encoding="utf-8")
        packet = build_context_packet(
            "# Task\nAudit target.",
            "theorem_verifier",
            self._graph(facts),
            target_fact_id="target",
            project_root=self.root,
            sources=[source],
        )
        self.assertEqual("markdown", packet["task"]["format"])
        self.assertEqual("opened source claim", packet["sources"][0]["content"])
        self.assertIn("Target fact: target", explain_context_packet(packet))

    def test_check_detects_tampering(self) -> None:
        packet = self._build([_fact("target", "PROPOSED")])
        packet["target_fact"]["statement"] = "tampered"
        report = check_context_packet(packet)
        self.assertFalse(report["valid"])
        self.assertEqual("NEEDS_CONTEXT_REVIEW", report["status"])
        self.assertTrue(any("digest" in error for error in report["errors"]))

    def test_unknown_target_and_budget_fail_closed(self) -> None:
        graph = self._graph([_fact("target", "PROPOSED")])
        with self.assertRaises(ValidationError):
            build_context_packet(
                {"target_fact_id": "missing"},
                "theorem_verifier",
                graph,
                project_root=self.root,
            )
        with self.assertRaises(ValidationError):
            build_context_packet(
                {"target_fact_id": "target"},
                "theorem_verifier",
                graph,
                project_root=self.root,
                budget="unlimited",
            )

    def test_long_prose_chunks_semantically_with_hashes_and_overlap(self) -> None:
        content = "\n\n".join(
            f"Section {index}. " + ("Evidence sentence. " * 220)
            for index in range(45)
        )
        chunks = chunk_long_content(content, kind="literature")
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["estimated_tokens"] <= 12_000 for chunk in chunks))
        self.assertTrue(all(len(chunk["digest"]) == 64 for chunk in chunks))
        self.assertTrue(any(chunk["overlap_tokens"] > 0 for chunk in chunks[1:]))

    def test_long_proof_requires_manual_handoff_instead_of_blind_chunking(self) -> None:
        with self.assertRaisesRegex(ValidationError, "manual long-context handoff"):
            chunk_long_content("proof step. " * 50_000, kind="mathematical_proof")


if __name__ == "__main__":
    unittest.main()
