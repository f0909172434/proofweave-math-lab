from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mathlab.errors import IntegrityError, ValidationError
from mathlab.fact_graph import FactGraph
from mathlab.source_registry import SourceRegistry
from tests.common import accept_report, fact


class FactGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "facts.jsonl"
        self.graph = FactGraph(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cycle_is_rejected_when_adding_edge(self) -> None:
        self.graph.add(fact("a", status="DRAFT"))
        self.graph.add(fact("b", status="DRAFT", dependencies=["a"]))
        with self.assertRaises(IntegrityError):
            self.graph.add_dependency("a", "b")

    def test_proposed_fact_cannot_be_formal_dependency(self) -> None:
        self.graph.add(fact("a"))
        with self.assertRaises(IntegrityError):
            self.graph.add(fact("b", dependencies=["a"]))

    def test_formal_claim_requires_assumptions(self) -> None:
        value = fact("a")
        value["assumptions"] = []
        with self.assertRaises(ValidationError):
            self.graph.add(value)

    def test_only_independent_theorem_verifier_can_promote(self) -> None:
        self.graph.add(fact("a", created_by="alice"))
        with self.assertRaises(IntegrityError):
            self.graph.promote("a", verifier="bob", verifier_role="orchestrator", report=accept_report("a"))
        with self.assertRaises(IntegrityError):
            self.graph.promote("a", verifier="alice", verifier_role="theorem_verifier", report=accept_report("a", "alice"))
        result = self.graph.promote("a", verifier="bob", verifier_role="theorem_verifier", report=accept_report("a", "bob"))
        self.assertEqual("VERIFIED", result["status"])

    def test_numerical_evidence_cannot_enter_truth_layer(self) -> None:
        value = fact("numeric")
        value["kind"] = "numerical_evidence"
        self.graph.add(value)
        with self.assertRaises(IntegrityError):
            self.graph.promote(
                "numeric",
                verifier="bob",
                verifier_role="theorem_verifier",
                report=accept_report("numeric", "bob"),
            )

    def test_accept_report_with_failed_check_is_rejected(self) -> None:
        self.graph.add(fact("a"))
        report = accept_report("a", "bob")
        report["checklist"][0]["result"] = "FAIL"
        with self.assertRaises(IntegrityError):
            self.graph.promote(
                "a", verifier="bob", verifier_role="theorem_verifier", report=report
            )

    def test_accept_report_identity_must_match(self) -> None:
        self.graph.add(fact("a"))
        report = accept_report("different", "bob")
        with self.assertRaises(IntegrityError):
            self.graph.promote(
                "a", verifier="bob", verifier_role="theorem_verifier", report=report
            )

    def test_persisted_nonexistent_source_dependency_blocks_promotion(self) -> None:
        value = FactGraph._defaulted(fact("a"))
        value["source_dependencies"] = ["source-does-not-exist"]
        self.path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        graph = FactGraph(self.path)
        with self.assertRaises(IntegrityError):
            graph.promote(
                "a",
                verifier="bob",
                verifier_role="theorem_verifier",
                report=accept_report("a", "bob", sources=["source-does-not-exist"]),
            )

    def test_verified_refutation_cannot_support_a_formal_claim(self) -> None:
        refutation = fact("refuted")
        refutation["kind"] = "refuted_claim"
        self.graph.add(refutation)
        self.graph.promote(
            "refuted",
            verifier="bob",
            verifier_role="theorem_verifier",
            report=accept_report("refuted", "bob"),
        )
        with self.assertRaises(IntegrityError):
            self.graph.add(fact("theorem", dependencies=["refuted"]))

    def test_review_api_does_not_rewrite_report_outcome(self) -> None:
        self.graph.add(fact("a"))
        report = accept_report("a", "bob")
        with self.assertRaises(IntegrityError):
            self.graph.review_failure("a", verifier="bob", outcome="REJECT", report=report)

    def test_accept_report_covers_sources_of_transitive_dependencies(self) -> None:
        SourceRegistry(self.path.parent / "source_registry.jsonl").add(
            {
                "source_id": "s1",
                "title": "Test source",
                "authors_or_organization": "Test",
                "publication_date": "2026-07-24",
                "url": "https://example.com/source",
                "accessed_at": "2026-07-24T00:00:00Z",
                "opened_at": "2026-07-24T00:00:00Z",
                "verified_at": "2026-07-24T00:00:00Z",
                "verified_by": "source-auditor",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "trust_level": "PRIMARY_HIGH",
                "project_use": "test",
                "exact_claim_supported": "test claim",
                "status": "VERIFIED",
            }
        )
        first = fact("a")
        first["source_dependencies"] = ["s1"]
        self.graph.add(first)
        self.graph.promote(
            "a",
            verifier="v-a",
            verifier_role="theorem_verifier",
            report=accept_report("a", "v-a", sources=["s1"]),
        )
        self.graph.add(fact("b", dependencies=["a"]))
        with self.assertRaises(IntegrityError):
            self.graph.promote(
                "b",
                verifier="v-b",
                verifier_role="theorem_verifier",
                report=accept_report("b", "v-b", dependencies=["a"]),
            )

    def test_reject_report_must_cover_dependency_closure(self) -> None:
        self.graph.add(fact("a"))
        self.graph.promote(
            "a",
            verifier="v-a",
            verifier_role="theorem_verifier",
            report=accept_report("a", "v-a"),
        )
        self.graph.add(fact("b", dependencies=["a"]))
        report = accept_report("b", "v-b")
        report["outcome"] = "REJECT"
        report["checklist"][0]["result"] = "FAIL"
        report["fatal_gap"] = "invalid proof step"
        with self.assertRaises(IntegrityError):
            self.graph.review_failure("b", verifier="v-b", outcome="REJECT", report=report)


if __name__ == "__main__":
    unittest.main()
