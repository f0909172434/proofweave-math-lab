from __future__ import annotations

import os
from pathlib import Path

from proofweave.certifiers.lean import environment_fingerprint, run_batch
from proofweave.core import CoreError
from tests.common import ProjectCase


class LeanBackendTests(ProjectCase):
    def test_sorry_admit_axiom_and_arbitrary_tactic_are_rejected_before_host_check(self) -> None:
        for target in ("True := by sorry", "True := by admit", "axiom bad : True"):
            with self.subTest(target=target), self.assertRaises(CoreError):
                run_batch(self.root, [{"id": "bad", "target": target, "tactic": "ring", "exact": None}])
        with self.assertRaisesRegex(CoreError, "unsupported tactic"):
            run_batch(self.root, [{"id": "bad", "target": "True", "tactic": "aesop", "exact": None}])

    def test_missing_lean_is_host_limited_not_certified(self) -> None:
        result = run_batch(self.root, [{"id": "goal", "target": "True", "tactic": "norm_num", "exact": None}])
        self.assertEqual("HOST_LIMITED", result["outcome"])
        self.assertEqual("HOST_LIMITED", result["results"]["goal"])

    def test_pinned_mathlib_true_and_false_algebra(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        if not environment_fingerprint(repository)["available"]:
            if os.environ.get("PROOFWEAVE_REQUIRE_LEAN") == "1":
                self.fail("PROOFWEAVE_REQUIRE_LEAN=1 but pinned Lean/Mathlib is unavailable")
            self.skipTest("Pinned Mathlib cache is not installed")
        result = run_batch(repository, [
            {"id": "true", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1", "tactic": "ring", "exact": None},
            {"id": "false", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 2", "tactic": "ring", "exact": None},
        ])
        self.assertEqual("FAILED", result["outcome"])
        self.assertEqual("PASSED", result["results"]["true"])
        self.assertEqual("FAILED", result["results"]["false"])
