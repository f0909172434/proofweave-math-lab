from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mathlab.issue_ledger import IssueLedger
from mathlab.validation import (
    build_release_manifest,
    release_checks,
    validate_experiments,
    validate_runtime_policy,
)
from tests.common import write_json


class ReleaseGateTests(unittest.TestCase):
    def test_content_manifest_is_stable_and_change_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "artifact.txt").write_text("version one\n", encoding="utf-8")
            first = build_release_manifest(root)
            second = build_release_manifest(root)
            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            (root / "artifact.txt").write_text("version two\n", encoding="utf-8")
            third = build_release_manifest(root)
            self.assertNotEqual(first["snapshot_id"], third["snapshot_id"])
            (root / "delivered.pdf").write_bytes(b"pdf-version-one")
            pdf_first = build_release_manifest(root)
            (root / "delivered.pdf").write_bytes(b"pdf-version-two")
            pdf_second = build_release_manifest(root)
            self.assertNotEqual(pdf_first["snapshot_id"], pdf_second["snapshot_id"])

    def test_release_metadata_does_not_mark_content_snapshot_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state").mkdir(parents=True)
            (root / "artifact.txt").write_text("research content\n", encoding="utf-8")
            (root / "state" / "release_manifest.json").write_text("{}\n", encoding="utf-8")
            (root / "state" / "release_report.json").write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "ProofWeave Test"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "baseline"],
                cwd=root,
                check=True,
                capture_output=True,
            )

            (root / "state" / "release_report.json").write_text(
                '{"updated": true}\n', encoding="utf-8"
            )
            self.assertFalse(build_release_manifest(root)["git_dirty"])

            (root / "artifact.txt").write_text("changed research content\n", encoding="utf-8")
            self.assertTrue(build_release_manifest(root)["git_dirty"])

    def test_release_gate_rejects_open_fatal_and_unreviewed_live_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state").mkdir(parents=True)
            (root / "config").mkdir(parents=True)
            (root / "paper").mkdir(parents=True)
            (root / "experiments" / "configs").mkdir(parents=True)
            for name in ("fact_graph.jsonl", "source_registry.jsonl", "issue_ledger.jsonl"):
                (root / "state" / name).write_text("", encoding="utf-8")
            IssueLedger(root / "state" / "issue_ledger.jsonl").add(
                {
                    "issue_id": "fatal-1",
                    "severity": "FATAL",
                    "status": "OPEN",
                    "location": "paper/main.tex",
                    "affected_claims": [],
                    "explanation": "test blocker",
                    "failed_step": "verification",
                    "required_fix": "repair",
                    "verification_after_fix": "rerun",
                }
            )
            write_json(root / "config" / "runtime_policy.json", {"allow_api_routing": True})
            (root / "paper" / "claim_map.yml").write_text("claims: []\n", encoding="utf-8")
            checks = release_checks(root, run_external_gates=False)
            self.assertTrue(any(c.check_id == "open-blocking-issue" and c.status == "FAIL" for c in checks))
            self.assertTrue(any(c.check_id == "runtime-policy" and c.status == "FAIL" for c in checks))

    def test_bogus_external_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir(parents=True)
            write_json(
                root / "config" / "runtime_policy.json",
                {
                    "allow_api_routing": True,
                    "external_execution_review": {
                        "approved": True,
                        "approved_by": "",
                        "approved_at": "",
                        "maximum_cost": None,
                        "approved_actions": ["allow_api_routing"],
                    },
                },
            )
            checks = validate_runtime_policy(root)
            self.assertTrue(any(c.status == "FAIL" for c in checks))

    def test_experiment_gate_rejects_missing_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "experiments" / "configs").mkdir(parents=True)
            config = {
                "experiment_id": "bad-path",
                "question": "Does the gate reject missing artifacts?",
                "status": "COMPLETE",
                "config_path": "experiments/configs/bad.json",
                "script_path": "experiments/scripts/missing.py",
                "report_path": "experiments/reports/missing.md",
                "environment": {},
                "parameters": {},
                "raw_data_paths": [],
                "output_paths": [],
                "reproduction_command": "python experiments/scripts/missing.py",
                "limitations": ["gate test"],
                "created_at": "2026-07-24T00:00:00Z",
            }
            write_json(root / "experiments" / "configs" / "bad.json", config)
            checks = validate_experiments(root, execute_commands=False)
            self.assertTrue(any(c.check_id == "experiment-path" and c.status == "FAIL" for c in checks))

    def test_experiment_gate_executes_recorded_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "experiments" / "configs").mkdir(parents=True)
            (root / "experiments" / "scripts").mkdir(parents=True)
            (root / "experiments" / "reports").mkdir(parents=True)
            (root / "experiments" / "scripts" / "fail.py").write_text(
                "raise SystemExit(7)\n", encoding="utf-8"
            )
            (root / "experiments" / "reports" / "fail.md").write_text("failed\n", encoding="utf-8")
            config = {
                "experiment_id": "bad-command",
                "question": "Does the gate execute the command?",
                "status": "FAILED",
                "config_path": "experiments/configs/fail.json",
                "script_path": "experiments/scripts/fail.py",
                "report_path": "experiments/reports/fail.md",
                "environment": {},
                "parameters": {},
                "raw_data_paths": [],
                "output_paths": [],
                "reproduction_command": (
                    "python experiments/scripts/fail.py --config experiments/configs/fail.json"
                ),
                "limitations": ["gate test"],
                "created_at": "2026-07-24T00:00:00Z",
            }
            write_json(root / "experiments" / "configs" / "fail.json", config)
            checks = validate_experiments(root, execute_commands=True)
            self.assertTrue(any(c.check_id == "experiment-execution" and c.status == "FAIL" for c in checks))

    def test_experiment_command_must_bind_declared_script_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "experiments" / "configs").mkdir(parents=True)
            (root / "experiments" / "scripts").mkdir(parents=True)
            (root / "experiments" / "reports").mkdir(parents=True)
            (root / "experiments" / "scripts" / "declared.py").write_text("pass\n", encoding="utf-8")
            (root / "experiments" / "reports" / "report.md").write_text("report\n", encoding="utf-8")
            config = {
                "experiment_id": "unbound-command",
                "question": "Is the command bound to declared artifacts?",
                "status": "COMPLETE",
                "config_path": "experiments/configs/unbound.json",
                "script_path": "experiments/scripts/declared.py",
                "report_path": "experiments/reports/report.md",
                "environment": {},
                "parameters": {},
                "raw_data_paths": [],
                "output_paths": [],
                "reproduction_command": "python -c pass",
                "limitations": ["gate test"],
                "created_at": "2026-07-24T00:00:00Z",
            }
            write_json(root / "experiments" / "configs" / "unbound.json", config)
            checks = validate_experiments(root, execute_commands=False)
            self.assertTrue(any(c.check_id == "experiment-command-binding" and c.status == "FAIL" for c in checks))

    def test_python_dash_c_cannot_fake_script_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "experiments" / "configs").mkdir(parents=True)
            (root / "experiments" / "scripts").mkdir(parents=True)
            (root / "experiments" / "reports").mkdir(parents=True)
            (root / "experiments" / "scripts" / "declared.py").write_text(
                "raise SystemExit(9)\n", encoding="utf-8"
            )
            (root / "experiments" / "reports" / "report.md").write_text("report\n", encoding="utf-8")
            config_path = root / "experiments" / "configs" / "bypass.json"
            write_json(
                config_path,
                {
                    "experiment_id": "binding-bypass",
                    "question": "Can arguments fake execution?",
                    "status": "COMPLETE",
                    "config_path": "experiments/configs/bypass.json",
                    "script_path": "experiments/scripts/declared.py",
                    "report_path": "experiments/reports/report.md",
                    "environment": {},
                    "parameters": {},
                    "raw_data_paths": [],
                    "output_paths": [],
                    "reproduction_command": (
                        "python -c pass experiments/scripts/declared.py experiments/configs/bypass.json"
                    ),
                    "limitations": ["gate test"],
                    "created_at": "2026-07-24T00:00:00Z",
                },
            )
            checks = validate_experiments(root, execute_commands=True)
            self.assertTrue(any(c.check_id == "experiment-command-binding" and c.status == "FAIL" for c in checks))


if __name__ == "__main__":
    unittest.main()
