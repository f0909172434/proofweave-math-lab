from __future__ import annotations

import json

from proofweave.core import parse_input
from tests.common import ProjectCase
from tools.migrate_v1 import migrate


class MigrationTests(ProjectCase):
    def test_v1_verified_never_maps_to_certified(self) -> None:
        source = self.root / "fact_graph.jsonl"
        rows = [
            {
                "fact_id": "old-theorem",
                "title": "Old theorem",
                "kind": "theorem",
                "statement": "For every n, n = n.",
                "assumptions": ["none"],
                "quantifiers": ["for every n"],
                "dependencies": [],
                "proof": "Reflexivity.",
                "status": "VERIFIED",
                "verification_status": "VERIFIED",
            },
            {"fact_id": "scan", "kind": "numerical_evidence", "statement": "A finite scan.", "dependencies": []},
        ]
        source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        report = migrate(source, self.root)
        record_path = next((self.root / "workspace" / "claims").glob("old-theorem--*.json"))
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual("UNVERIFIED", record["proof_status"])
        self.assertEqual("UNCONFIRMED", record["alignment"])
        self.assertFalse(report["v1_verified_mapped_to_certified"])
        self.assertEqual("scan", report["skipped"][0]["fact_id"])
        parse_input(self.root / "workspace" / "claims" / "old-theorem.md")

    def test_migration_cycle_fails_before_writes(self) -> None:
        source = self.root / "fact_graph.jsonl"
        rows = [
            {"fact_id": "a", "kind": "theorem", "statement": "A", "assumptions": ["none"], "dependencies": ["b"]},
            {"fact_id": "b", "kind": "lemma", "statement": "B", "assumptions": ["none"], "dependencies": ["a"]},
        ]
        source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            migrate(source, self.root)
        self.assertEqual([], list((self.root / "workspace" / "claims").glob("*.json")))

    def test_revoked_maps_only_to_lifecycle(self) -> None:
        source = self.root / "fact_graph.jsonl"
        row = {"fact_id": "revoked", "kind": "theorem", "statement": "A", "assumptions": ["none"], "dependencies": [], "status": "REVOKED"}
        source.write_text(json.dumps(row), encoding="utf-8")
        migrate(source, self.root)
        record = json.loads(next((self.root / "workspace" / "claims").glob("revoked--*.json")).read_text(encoding="utf-8"))
        self.assertEqual("REVOKED", record["lifecycle"])
        self.assertEqual("UNVERIFIED", record["proof_status"])

    def test_nonformal_dependency_exclusion_is_transitive(self) -> None:
        source = self.root / "fact_graph.jsonl"
        rows = [
            {"fact_id": "scan", "kind": "numerical_evidence", "statement": "scan", "dependencies": []},
            {"fact_id": "lemma", "kind": "lemma", "statement": "L", "assumptions": ["none"], "dependencies": ["scan"]},
            {"fact_id": "theorem", "kind": "theorem", "statement": "T", "assumptions": ["none"], "dependencies": ["lemma"]},
        ]
        source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        report = migrate(source, self.root)
        self.assertEqual([], list((self.root / "workspace" / "claims").glob("*.json")))
        self.assertEqual({"scan", "lemma", "theorem"}, {item["fact_id"] for item in report["skipped"]})
