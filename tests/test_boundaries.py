from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from proofweave.certifiers import lean
from proofweave.certify import certify, run_consistency_errors
from proofweave.cli import main as cli_main
from proofweave.core import CoreError, atomic_write_text, find_root, hash_file, parse_input, read_json, verify_artifacts
from proofweave.pipeline import _valid_claim, check_project, initialize, run_proof, status
from tests.common import FakeRunner, ProjectCase


REPOSITORY = Path(__file__).resolve().parents[1]


class CoreValidationBoundaryTests(ProjectCase):
    def _rewrite(self, transform) -> Path:
        path = self.theorem()
        path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")
        return path

    def test_read_json_and_atomic_write_fail_closed(self) -> None:
        invalid = self.root / "invalid.json"
        invalid.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "Cannot read JSON"):
            read_json(invalid)
        invalid.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "JSON object required"):
            read_json(invalid)
        target = self.root / "atomic.txt"
        with patch("proofweave.core.os.replace", side_effect=OSError("blocked")), self.assertRaises(OSError):
            atomic_write_text(target, "value")
        self.assertEqual([], list(self.root.glob("atomic.txt.*")))

    def test_find_root_accepts_file_and_rejects_uninitialized_directory(self) -> None:
        path = self.theorem()
        self.assertTrue(os.path.samefile(self.root, find_root(path)))
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(CoreError, "Not a ProofWeave project"):
            find_root(directory)

    def test_front_matter_list_validation(self) -> None:
        changes = (
            ('assumptions = ["x is an integer"]', 'assumptions = "bad"', "array of strings"),
            ('assumptions = ["x is an integer"]', "assumptions = []", "must be explicit"),
            ('quantifiers = ["for every integer x"]', 'quantifiers = ["x", "x"]', "duplicates"),
        )
        for old, new, message in changes:
            with self.subTest(message=message):
                with self.assertRaisesRegex(CoreError, message):
                    parse_input(self._rewrite(lambda text, old=old, new=new: text.replace(old, new)))

    def test_certificate_validation_boundaries(self) -> None:
        fence = '```proofweave-lean\ntarget = "True"\ntactic = "norm_num"\n```'
        cases = (
            (lambda text: text.replace(fence, fence + "\n" + fence), "At most one"),
            (lambda text: text.replace('tactic = "ring"', 'tactic = ["ring"'), "Invalid proofweave-lean TOML"),
            (lambda text: text.replace('tactic = "ring"', 'tactic = "ring"\nowner = "x"'), "Unknown certificate fields"),
            (lambda text: text + "\n## Statement\n\nAgain.\n", "Duplicate ## Statement"),
        )
        for transform, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(CoreError, message):
                path = self.theorem(target="True", tactic="norm_num") if message == "At most one" else self.theorem()
                path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")
                parse_input(path)

    def test_node_structure_rejections_and_prelude(self) -> None:
        invalid = (
            ("### a [semantic]\nAlias: b\nText.\n\n### b [semantic]\nText.", "Only alias nodes"),
            ("### a [semantic]\n", "has no text"),
            ("   ", "at least one proof step"),
            ("### a [semantic]\nA.\n\n### a [bridge]\nB.", "IDs must be unique"),
            ("### a [semantic]\nDepends: missing\nA.", "references unknown nodes"),
            ("### a [semantic]\nDepends: a\nA.", "cannot reference itself"),
        )
        for proof, message in invalid:
            with self.subTest(message=message), self.assertRaisesRegex(CoreError, message):
                parse_input(self.theorem(proof=proof, target=None))
        parsed = parse_input(self.theorem(proof="Prelude.\n\n### formal [computational]\nCalculation.", target=None))
        self.assertEqual(["preamble", "formal"], [node["id"] for node in parsed["proof_ir"]["nodes"]])

    def test_document_level_rejections(self) -> None:
        invalid_utf8 = self.root / "bad.md"
        invalid_utf8.write_bytes(b"\xff")
        with self.assertRaisesRegex(CoreError, "UTF-8"):
            parse_input(invalid_utf8)
        cases = (
            (lambda text: text.replace("+++\n", "", 1), "must begin"),
            (lambda text: text.replace('claim_id = "claim"', 'claim_id = ["claim"'), "Invalid front matter TOML"),
            (lambda text: text.replace('claim_id = "claim"', 'claim_id = "bad id"'), "claim_id must match"),
            (lambda text: text.replace('title = "Claim"', 'title = ""'), "title must be"),
            (lambda text: text.replace("dependencies = []", 'dependencies = ["claim"]'), "cannot depend on itself"),
            (lambda text: text.replace("## Statement", "## Other"), "requires ## Statement"),
            (lambda text: text.replace("For every integer x, (x + 1)^2 = x^2 + 2x + 1.", ""), "must not be empty"),
            (lambda text: text.replace("```\n", "```\nextra\n", 1), "may contain only"),
            (lambda text: text.split("## Certificate")[0] + "## Certificate\n", "requires a proofweave-lean"),
        )
        for transform, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(CoreError, message):
                parse_input(self._rewrite(transform))

    def test_artifact_verification_all_failure_shapes(self) -> None:
        existing = self.root / "artifact.txt"
        existing.write_text("value", encoding="utf-8")
        self.assertEqual(["artifacts must be an object"], verify_artifacts(self.root, {"artifacts": []}))
        errors = verify_artifacts(self.root, {"artifacts": {1: 2, "missing.txt": "0" * 64, "artifact.txt": "0" * 64}})
        self.assertTrue(any("must be strings" in error for error in errors))
        self.assertTrue(any("missing artifact" in error for error in errors))
        self.assertTrue(any("hash mismatch" in error for error in errors))
        self.assertEqual([], verify_artifacts(self.root, {"artifacts": {"artifact.txt": hash_file(existing)}}))


class CertificationBoundaryTests(ProjectCase):
    def test_run_consistency_reports_each_invariant_violation(self) -> None:
        self.assertIn("requires coverage", run_consistency_errors({})[0])
        malformed_counts = {
            "proof_status": "CERTIFIED", "coverage": {
                "deductive_total": True, "certified": 0, "failed": 0, "unsupported": 0,
                "host_limited": 0, "percentage": 0.0,
            }, "certificate": {"results": {}},
        }
        self.assertIn("non-negative integers", run_consistency_errors(malformed_counts)[0])
        inconsistent = {
            "proof_status": "CERTIFIED", "coverage": {
                "deductive_total": 2, "certified": 1, "failed": 0, "unsupported": 0,
                "host_limited": 0, "percentage": 99.0,
            }, "certificate": {"results": [], "outcome": "FAILED"},
        }
        errors = run_consistency_errors(inconsistent)
        self.assertTrue(any("do not sum" in error for error in errors))
        self.assertTrue(any("percentage" in error for error in errors))
        self.assertTrue(any("results must be" in error for error in errors))
        self.assertTrue(any("partial-as-certified" in error for error in errors))
        for proof_status, failed, certified, total, fragment in (
            ("FAILED", 0, 0, 1, "no failed obligation"),
            ("PARTIAL", 0, 1, 1, "fully certified"),
            ("UNKNOWN", 0, 0, 1, "invalid proof_status"),
        ):
            run = {
                "proof_status": proof_status,
                "coverage": {"deductive_total": total, "certified": certified, "failed": failed, "unsupported": total - certified - failed, "host_limited": 0, "percentage": 100.0 * certified / total},
                "certificate": {"results": {"x": "PASSED"} if certified else {}, "outcome": "PASSED"},
            }
            self.assertTrue(any(fragment in error for error in run_consistency_errors(run)))

    def test_certification_without_ready_dependencies_or_explicit_runner_is_partial(self) -> None:
        parsed = parse_input(self.theorem())
        blocked = certify(self.root, parsed, dependency_digests={"dep": "x"}, dependencies_ready=False, runner=FakeRunner())
        self.assertEqual("PARTIAL", blocked["proof_status"])
        self.assertEqual(1, blocked["coverage"]["unsupported"])
        host = certify(self.root, parsed, dependency_digests={}, dependencies_ready=True)
        self.assertEqual("PARTIAL", host["proof_status"])
        self.assertEqual(1, host["coverage"]["host_limited"])
        empty = copy_parsed = dict(parsed)
        copy_parsed["top_certificate"] = None
        copy_parsed["proof_ir"] = {"nodes": []}
        zero = certify(self.root, empty, dependency_digests={}, dependencies_ready=True, runner=FakeRunner())
        self.assertEqual(0.0, zero["coverage"]["percentage"])


class LeanBoundaryTests(ProjectCase):
    def test_empty_batch_exact_and_extra_exact_validation(self) -> None:
        self.assertEqual("UNSUPPORTED", lean.run_batch(self.root, [])["outcome"])
        bad_specs = (
            ({"id": "x", "target": "", "tactic": "ring", "exact": None}, "non-empty target"),
            ({"id": "x", "target": "True", "tactic": "exact", "exact": "missing"}, "earlier certified"),
            ({"id": "x", "target": "True", "tactic": "ring", "exact": "other"}, "may use `exact` only"),
        )
        for spec, message in bad_specs:
            with self.subTest(message=message), self.assertRaisesRegex(CoreError, message):
                lean.run_batch(self.root, [spec])

    def test_error_line_parser_and_subprocess_failure_are_fail_closed(self) -> None:
        lines, diagnostics, unlocated = lean._error_lines(
            "not-json\n" + json.dumps({"severity": "warning"}) + "\n"
            + json.dumps({"severity": "error", "pos": {"line": 4}}) + "\n"
            + json.dumps({"severity": "error", "message": "global"})
        )
        self.assertEqual({4}, lines)
        self.assertEqual(2, len(diagnostics))
        self.assertTrue(unlocated)
        environment = {
            "available": True, "lake_path": "lake", "expected_version": "4.32.1",
            "fingerprint": "x", "files": {},
        }
        spec = {"id": "goal", "target": "True", "tactic": "norm_num", "exact": None}
        with patch("proofweave.certifiers.lean.environment_fingerprint", return_value=environment), patch(
            "proofweave.certifiers.lean.subprocess.run", side_effect=OSError("missing")
        ):
            result = lean.run_batch(self.root, [spec])
        self.assertEqual("HOST_LIMITED", result["outcome"])
        self.assertEqual(1, result["invocations"])

    def test_version_failure_or_mismatch_is_host_limited_before_compile(self) -> None:
        environment = {
            "available": True, "lake_path": "lake", "expected_version": "4.32.1",
            "fingerprint": "x", "files": {},
        }
        spec = {"id": "goal", "target": "True", "tactic": "norm_num", "exact": None}
        compile_success = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        versions = (
            subprocess.CompletedProcess([], 1, stdout="", stderr="version failed"),
            subprocess.CompletedProcess([], 0, stdout="Lean (version 4.32.10)", stderr=""),
        )
        for version in versions:
            with self.subTest(version=version), patch(
                "proofweave.certifiers.lean.environment_fingerprint", return_value=environment
            ), patch(
                "proofweave.certifiers.lean.subprocess.run", side_effect=[version, compile_success]
            ) as mocked_run:
                result = lean.run_batch(self.root, [spec])
            self.assertEqual("HOST_LIMITED", result["outcome"])
            self.assertEqual("HOST_LIMITED", result["results"]["goal"])
            self.assertIsNone(result["toolchain_version"])
            self.assertEqual(1, mocked_run.call_count)

    def test_version_probe_timeout_is_fail_closed_before_compile(self) -> None:
        environment = {
            "available": True, "lake_path": "lake", "expected_version": "4.32.1",
            "fingerprint": "x", "files": {},
        }
        spec = {"id": "goal", "target": "True", "tactic": "norm_num", "exact": None}
        with patch(
            "proofweave.certifiers.lean.environment_fingerprint", return_value=environment
        ), patch(
            "proofweave.certifiers.lean.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["lake", "env", "lean", "--version"], 60),
        ) as mocked_run:
            result = lean.run_batch(self.root, [spec])
        self.assertEqual("HOST_LIMITED", result["outcome"])
        self.assertEqual("HOST_LIMITED", result["results"]["goal"])
        self.assertEqual([{"message": "TimeoutExpired"}], result["diagnostics"])
        self.assertEqual(1, mocked_run.call_count)
        self.assertEqual(60, lean.VERSION_PROBE_TIMEOUT)
        self.assertEqual(lean.VERSION_PROBE_TIMEOUT, mocked_run.call_args.kwargs["timeout"])


class PipelineIntegrityBoundaryTests(ProjectCase):
    def test_alignment_revocation_duplicate_active_and_cache_digest_boundaries(self) -> None:
        with self.assertRaisesRegex(CoreError, "requires a whole-claim"):
            run_proof(self.theorem(target=None), root=self.root, confirm_alignment=True, runner=FakeRunner())
        path = self.theorem()
        run_proof(path, root=self.root, confirm_alignment=True, runner=FakeRunner())
        self.assertEqual("CONFIRMED", run_proof(path, root=self.root, runner=FakeRunner())["alignment"])
        claim_path = next((self.root / "workspace" / "claims").glob("*.json"))
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["alignment"] = "STALE"
        claim_path.write_text(json.dumps(claim), encoding="utf-8")
        self.assertEqual("STALE", run_proof(path, root=self.root, runner=FakeRunner())["alignment"])
        claim["lifecycle"] = "REVOKED"
        claim_path.write_text(json.dumps(claim), encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "REVOKED"):
            run_proof(path, root=self.root, runner=FakeRunner())
        claim["lifecycle"] = "ACTIVE"
        claim_path.write_text(json.dumps(claim), encoding="utf-8")
        duplicate = claim_path.with_name("duplicate.json")
        duplicate.write_text(json.dumps(claim), encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "Multiple ACTIVE"):
            run_proof(path, root=self.root, runner=FakeRunner())

    def test_run_digest_mismatch_and_unknown_status_are_fail_closed(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        first = run_proof(path, root=self.root, runner=runner)
        run_path = Path(first["artifact_directory"], "run.json")
        run_path.write_text(run_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        second = run_proof(path, root=self.root, runner=runner)
        self.assertFalse(second["cache_hit"])
        self.assertEqual(2, runner.calls)
        with self.assertRaisesRegex(CoreError, "Unknown claim_id"):
            status(self.root, "unknown")

    def test_invalid_claim_record_reports_all_identity_errors(self) -> None:
        errors = _valid_claim({
            "claim_id": "x", "revision_id": "wrong", "statement": "S", "assumptions": [],
            "quantifiers": [], "dependencies": [], "statement_hash": "wrong", "alignment": "BAD",
            "proof_status": "CERTIFIED", "lifecycle": "BAD", "certificate_digest": None,
        })
        for fragment in ("invalid alignment", "invalid lifecycle", "statement_hash mismatch", "revision_id mismatch", "lacks certificate_digest"):
            self.assertTrue(any(fragment in error for error in errors), fragment)
        missing = _valid_claim({})
        self.assertTrue(any("missing claim field" in error for error in missing))

    def test_check_project_reports_static_record_graph_and_artifact_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root)
            shutil.copytree(REPOSITORY / "proofweave", root / "proofweave")
            shutil.copytree(REPOSITORY / "schemas", root / "schemas")
            (root / "schemas" / "claim.schema.json").write_text("{}", encoding="utf-8")
            (root / "schemas" / "run.schema.json").write_text("{", encoding="utf-8")
            (root / "proofweave" / "extra.py").write_text("# extra\n", encoding="utf-8")
            cli = root / "proofweave" / "cli.py"
            cli.write_text(cli.read_text(encoding="utf-8").replace('commands.add_parser("check"', 'commands.alias("check"') + ("# filler\n" * 2600) + "\nimport tools\n", encoding="utf-8")
            (root / "agents").mkdir()
            record = {
                "schema_version": 2, "claim_id": "a", "revision_id": "bad", "statement": "A",
                "assumptions": [], "quantifiers": [], "dependencies": ["b"], "statement_hash": "bad",
                "alignment": "UNCONFIRMED", "proof_status": "UNVERIFIED", "lifecycle": "ACTIVE",
            }
            claims = root / "workspace" / "claims"
            (claims / "a.json").write_text(json.dumps(record), encoding="utf-8")
            record_b = dict(record, claim_id="b", dependencies=["a"])
            (claims / "b.json").write_text(json.dumps(record_b), encoding="utf-8")
            (claims / "a-duplicate.json").write_text(json.dumps(record), encoding="utf-8")
            bad_digest = root / "artifacts" / "bad" / "run"
            bad_digest.mkdir(parents=True)
            (bad_digest / "run.json").write_text("{}", encoding="utf-8")
            valid_digest = root / "artifacts" / "bad" / "identity"
            valid_digest.mkdir()
            run = {"run_id": "wrong", "cache_key": "wrong", "artifacts": [], "coverage": {}, "certificate": {}, "proof_status": "CERTIFIED"}
            run_path = valid_digest / "run.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            (valid_digest / "run.sha256").write_text(hash_file(run_path), encoding="utf-8")
            report = check_project(root)
        self.assertEqual("FAIL", report["result"])
        joined = "\n".join(report["errors"])
        for fragment in (
            "wrong schema draft", "invalid schema", "production module budget", "cli.py exceeds",
            "production file reaches", "production LOC exceeds", "removed v1 tree", "multiple ACTIVE",
            "claim dependency cycle", "run digest mismatch", "run identity/path mismatch",
            "artifact outside run directory", "runtime imports migration tools", "top-level command budget",
        ):
            self.assertIn(fragment, joined)


class CliBoundaryTests(ProjectCase):
    def test_init_status_and_check_commands(self) -> None:
        with patch("proofweave.cli.initialize", return_value={"result": "initialized"}):
            self.assertEqual(0, cli_main(["init", "--root", str(self.root)]))
        with patch("proofweave.cli.status", return_value={"claims": []}):
            self.assertEqual(0, cli_main(["status", "x", "--root", str(self.root)]))
        with patch("proofweave.cli.check_project", return_value={"result": "PASS", "errors": []}):
            self.assertEqual(0, cli_main(["check", "--root", str(self.root)]))
        with patch("proofweave.cli.check_project", return_value={"result": "FAIL", "errors": ["bad"]}):
            self.assertEqual(1, cli_main(["check", "--root", str(self.root)]))

    def test_package_main_delegates_exit_code(self) -> None:
        with patch("proofweave.cli.main", return_value=7), self.assertRaises(SystemExit) as raised:
            runpy.run_module("proofweave.__main__", run_name="__main__")
        self.assertEqual(7, raised.exception.code)
