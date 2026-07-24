from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.issue_ledger import IssueLedger
from mathlab.schemas import load_schema, validate_all_schemas, validate_instance
from mathlab.validation import validate_experiments


class SchemaTests(unittest.TestCase):
    def test_all_project_schemas_parse_as_draft_2020_12(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual([], validate_all_schemas(root))

    def test_fact_schema_requires_full_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        errors = validate_instance({"fact_id": "x"}, load_schema("fact", root))
        self.assertTrue(any("statement" in error for error in errors))

    def test_experiment_without_reproduction_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "experiments" / "configs" / "bad.yml"
            config.parent.mkdir(parents=True)
            config.write_text("experiment_id: bad\nenvironment: {}\nparameters: {}\nlimitations: [test]\n", encoding="utf-8")
            checks = validate_experiments(root)
            self.assertTrue(any(check.status == "FAIL" and "reproduction" in check.check_id for check in checks))

    def test_issue_ledger_tracks_revision_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = IssueLedger(Path(temp) / "issues.jsonl")
            ledger.add({
                "issue_id": "i1", "severity": "MAJOR", "status": "OPEN", "location": "paper",
                "affected_claims": ["f1"], "explanation": "gap", "failed_step": "step 2",
                "required_fix": "prove it", "verification_after_fix": "independent recheck"
            })
            ledger.update("i1", "IN_PROGRESS")
            fixed = ledger.update("i1", "FIXED", fix_artifacts=["proof-v2"])
            self.assertEqual("FIXED", fixed["status"])

    def test_validator_enforces_unique_items_formats_and_numeric_bounds(self) -> None:
        self.assertTrue(
            validate_instance(["x", "x"], {"type": "array", "uniqueItems": True})
        )
        self.assertTrue(
            validate_instance("not-a-date", {"type": "string", "format": "date-time"})
        )
        self.assertTrue(validate_instance("relative", {"type": "string", "format": "uri"}))
        self.assertTrue(validate_instance(-1, {"type": "integer", "minimum": 0}))
        self.assertTrue(validate_instance(11, {"type": "integer", "maximum": 10}))


if __name__ == "__main__":
    unittest.main()
