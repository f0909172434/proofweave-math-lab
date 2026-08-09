from __future__ import annotations

import json
from pathlib import Path

from proofweave.core import CoreError
from proofweave.pipeline import check_project, run_proof, status
from tests.common import FakeRunner, ProjectCase


class PipelineTests(ProjectCase):
    def test_fast_path_and_unchanged_rerun(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        cold = run_proof(path, root=self.root, runner=runner)
        warm = run_proof(path, root=self.root, runner=runner)
        self.assertTrue(cold["fast_path"])
        self.assertEqual("CERTIFIED", cold["proof_status"])
        self.assertEqual(1, cold["invocations"]["certifier"])
        self.assertTrue(warm["cache_hit"])
        self.assertEqual({"model": 0, "semantic_extraction": 0, "certifier": 0}, warm["invocations"])
        self.assertEqual(1, runner.calls)

    def test_statement_mutation_invalidates_and_supersedes(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        first = run_proof(path, root=self.root, runner=runner)
        path = self.theorem(statement="For every integer x, (x + 2)^2 = x^2 + 4x + 4.", target="∀ x : ℤ, (x + 2)^2 = x^2 + 4*x + 4")
        second = run_proof(path, root=self.root, runner=runner)
        self.assertNotEqual(first["cache_key"], second["cache_key"])
        states = status(self.root)["claims"]
        self.assertEqual({"ACTIVE", "SUPERSEDED"}, {item["lifecycle"] for item in states})
        self.assertEqual(2, runner.calls)

    def test_assumption_removal_can_fail_certification(self) -> None:
        path = self.theorem(assumptions=["x = 0"], target="∀ x : ℤ, x = 0 → x^2 = 0", tactic="norm_num")
        run_proof(path, root=self.root, runner=FakeRunner())
        path = self.theorem(assumptions=["none"], target="False", tactic="norm_num")
        result = run_proof(path, root=self.root, runner=FakeRunner())
        self.assertEqual("FAILED", result["proof_status"])

    def test_dependency_mutation_invalidates_cache(self) -> None:
        runner = FakeRunner()
        dependency = self.theorem("dep", statement="1 = 1.", assumptions=["none"], quantifiers=[], target="(1 : ℤ) = 1", tactic="norm_num")
        run_proof(dependency, root=self.root, runner=runner)
        main = self.theorem("main", dependencies=["dep"])
        first = run_proof(main, root=self.root, runner=runner)
        dependency = self.theorem("dep", statement="2 = 2.", assumptions=["none"], quantifiers=[], target="(2 : ℤ) = 2", tactic="norm_num")
        run_proof(dependency, root=self.root, runner=runner)
        second = run_proof(main, root=self.root, runner=runner)
        self.assertNotEqual(first["cache_key"], second["cache_key"])

    def test_claim_cycle_is_rejected(self) -> None:
        runner = FakeRunner()
        run_proof(self.theorem("b"), root=self.root, runner=runner)
        record_path = next((self.root / "workspace" / "claims").glob("b--*.json"))
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["dependencies"] = ["a"]
        record_path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "Claim dependency cycle"):
            run_proof(self.theorem("a", dependencies=["b"]), root=self.root, runner=runner)

    def test_unsupported_node_is_partial_and_traceable(self) -> None:
        proof = """### premise [semantic]
Use the stated hypothesis.

### short-name [alias]
Alias: premise

### calculation [computational]
Depends: short-name
Compute the polynomial.
```proofweave-lean
target = "(1 + 1 : ℤ) = 2"
tactic = "norm_num"
```"""
        result = run_proof(self.theorem(proof=proof, target=None), root=self.root, runner=FakeRunner())
        self.assertEqual("PARTIAL", result["proof_status"])
        self.assertEqual(1, result["coverage"]["unsupported"])
        concept = (Path(result["artifact_directory"]) / "concept_map.md").read_text(encoding="utf-8")
        self.assertIn("presentation-to-certificate", concept.lower())
        self.assertIn("short-name", concept)

    def test_false_algebraic_claim_is_failed(self) -> None:
        result = run_proof(self.theorem(target="False"), root=self.root, runner=FakeRunner())
        self.assertEqual("FAILED", result["proof_status"])
        self.assertEqual(1, result["coverage"]["failed"])

    def test_alignment_confirmation_and_source_staleness(self) -> None:
        path = self.theorem()
        unconfirmed = run_proof(path, root=self.root, runner=FakeRunner())
        confirmed = run_proof(path, root=self.root, confirm_alignment=True, runner=FakeRunner())
        self.assertEqual("UNCONFIRMED", unconfirmed["alignment"])
        self.assertEqual("CONFIRMED", confirmed["alignment"])
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertEqual("STALE", status(self.root, "claim")["claims"][0]["alignment"])

    def test_toolchain_fingerprint_change_invalidates(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        first = run_proof(path, root=self.root, runner=runner)
        (self.root / "lean-toolchain").write_text("leanprover/lean4:v4.32.2\n", encoding="utf-8")
        second = run_proof(path, root=self.root, runner=runner)
        self.assertNotEqual(first["cache_key"], second["cache_key"])
        self.assertEqual(2, runner.calls)

    def test_tampered_artifact_is_not_reused(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        first = run_proof(path, root=self.root, runner=runner)
        paper = Path(first["artifact_directory"]) / "paper_proof.md"
        paper.write_text("tampered", encoding="utf-8")
        second = run_proof(path, root=self.root, runner=runner)
        self.assertFalse(second["cache_hit"])
        self.assertEqual(2, runner.calls)

    def test_warm_cache_restores_claim_state_and_rejects_inconsistent_run(self) -> None:
        runner = FakeRunner()
        path = self.theorem()
        first = run_proof(path, root=self.root, runner=runner)
        claim_path = next((self.root / "workspace" / "claims").glob("claim--*.json"))
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["proof_status"] = "UNVERIFIED"
        claim["certificate_digest"] = None
        claim_path.write_text(json.dumps(claim), encoding="utf-8")
        warm = run_proof(path, root=self.root, runner=runner)
        restored = json.loads(claim_path.read_text(encoding="utf-8"))
        self.assertTrue(warm["cache_hit"])
        self.assertEqual("CERTIFIED", restored["proof_status"])

        run_path = Path(first["artifact_directory"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["coverage"]["unsupported"] = 1
        run_path.write_text(json.dumps(run), encoding="utf-8")
        (run_path.parent / "run.sha256").write_text(
            __import__("hashlib").sha256(run_path.read_bytes()).hexdigest() + "\n", encoding="utf-8"
        )
        rerun = run_proof(path, root=self.root, runner=runner)
        self.assertFalse(rerun["cache_hit"])
        self.assertEqual(2, runner.calls)

    def test_repository_complexity_check(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        report = check_project(repository)
        self.assertEqual("PASS", report["result"], report["errors"])
        self.assertEqual(10, report["metrics"]["production_modules"])
        self.assertEqual(3, report["metrics"]["schemas"])
        self.assertLessEqual(report["metrics"]["production_loc"], 2500)
