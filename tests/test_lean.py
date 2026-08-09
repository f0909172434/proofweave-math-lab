from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from proofweave.certifiers.lean import environment_fingerprint, run_batch
from proofweave.core import CoreError
from tests.common import ProjectCase


class LeanBackendTests(ProjectCase):
    def test_environment_fingerprint_accepts_posix_toolchain_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            toolchain = root / "toolchain"
            (toolchain / "bin").mkdir(parents=True)
            for name in ("lean", "lake"):
                (toolchain / "bin" / name).write_text(name, encoding="utf-8")
            with patch("proofweave.certifiers.lean.sys.platform", "linux"), patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch("proofweave.certifiers.lean.shutil.which", return_value=str(toolchain / "bin" / "lake")):
                environment = environment_fingerprint(root)
        self.assertTrue(environment["available"])
        self.assertNotEqual("MISSING", environment["files"]["toolchain/lean"])
        self.assertNotEqual("MISSING", environment["files"]["toolchain/lake"])

    def test_environment_fingerprint_falls_back_to_path_shims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            shims = root / "shims"
            shims.mkdir()
            for name in ("lean", "lake"):
                (shims / name).write_text(name, encoding="utf-8")
            with patch("proofweave.certifiers.lean._toolchain_directory", return_value=None), patch(
                "proofweave.certifiers.lean.shutil.which", side_effect=lambda name: str(shims / name)
            ):
                environment = environment_fingerprint(root)
        self.assertTrue(environment["available"])
        self.assertIsNone(environment["toolchain_path"])

    def test_environment_fingerprint_uses_toolchain_lake_without_path_shim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            toolchain = root / "toolchain"
            (toolchain / "bin").mkdir(parents=True)
            suffix = ".exe" if os.name == "nt" else ""
            for name in ("lean", "lake"):
                (toolchain / "bin" / f"{name}{suffix}").write_text(name, encoding="utf-8")
            with patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch("proofweave.certifiers.lean.shutil.which", return_value=None):
                environment = environment_fingerprint(root)
        self.assertTrue(environment["available"])
        self.assertEqual(
            str((toolchain / "bin" / f"lake{suffix}").resolve()),
            environment["lake_path"],
        )

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
        environment = environment_fingerprint(repository)
        if not environment["available"]:
            if os.environ.get("PROOFWEAVE_REQUIRE_LEAN") == "1":
                self.fail(f"PROOFWEAVE_REQUIRE_LEAN=1 but pinned Lean/Mathlib is unavailable: {environment}")
            self.skipTest("Pinned Mathlib cache is not installed")
        result = run_batch(repository, [
            {"id": "true", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1", "tactic": "ring", "exact": None},
            {"id": "false", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 2", "tactic": "ring", "exact": None},
        ])
        self.assertEqual("FAILED", result["outcome"])
        self.assertEqual("PASSED", result["results"]["true"])
        self.assertEqual("FAILED", result["results"]["false"])
