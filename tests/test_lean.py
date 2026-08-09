from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from proofweave.certifiers.lean import (
    _dependency_fingerprint,
    environment_fingerprint,
    run_batch,
)
from proofweave.core import CoreError
from tests.common import ProjectCase


class LeanBackendTests(ProjectCase):
    def test_environment_fingerprint_accepts_posix_toolchain_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lean-toolchain").write_text("leanprover/lean4:v4.32.2", encoding="utf-8")
            for name in ("lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            toolchain = root / "toolchain"
            (toolchain / "bin").mkdir(parents=True)
            (toolchain / "lib" / "lean").mkdir(parents=True)
            (toolchain / "lib" / "lean" / "Init.olean").write_text("init", encoding="utf-8")
            for name in ("lean", "lake"):
                (toolchain / "bin" / name).write_text(name, encoding="utf-8")
            with patch("proofweave.certifiers.lean.sys.platform", "linux"), patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch(
                "proofweave.certifiers.lean._dependency_fingerprint",
                return_value=({"dependency/closure": "closure"}, True),
            ):
                environment = environment_fingerprint(root)
        self.assertTrue(environment["available"])
        self.assertNotEqual("MISSING", environment["files"]["toolchain/lean"])
        self.assertNotEqual("MISSING", environment["files"]["toolchain/lake"])

    def test_environment_fingerprint_rejects_unpinned_path_shims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lean-toolchain").write_text("leanprover/lean4:v4.32.2", encoding="utf-8")
            for name in ("lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            with patch("proofweave.certifiers.lean._toolchain_directory", return_value=None), patch(
                "proofweave.certifiers.lean._dependency_fingerprint",
                return_value=({"dependency/closure": "closure"}, True),
            ):
                environment = environment_fingerprint(root)
        self.assertFalse(environment["available"])
        self.assertIsNone(environment["lake_path"])
        self.assertIsNone(environment["toolchain_path"])

    def test_environment_fingerprint_uses_toolchain_lake_without_path_shim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lean-toolchain").write_text("leanprover/lean4:v4.32.2", encoding="utf-8")
            for name in ("lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            toolchain = root / "toolchain"
            (toolchain / "bin").mkdir(parents=True)
            (toolchain / "lib" / "lean").mkdir(parents=True)
            (toolchain / "lib" / "lean" / "Init.olean").write_text("init", encoding="utf-8")
            suffix = ".exe" if os.name == "nt" else ""
            for name in ("lean", "lake"):
                (toolchain / "bin" / f"{name}{suffix}").write_text(name, encoding="utf-8")
            with patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch(
                "proofweave.certifiers.lean._dependency_fingerprint",
                return_value=({"dependency/closure": "closure"}, True),
            ):
                environment = environment_fingerprint(root)
        self.assertTrue(environment["available"])
        self.assertEqual(
            str((toolchain / "bin" / f"lake{suffix}").resolve()),
            environment["lake_path"],
        )

    def test_environment_fingerprint_binds_library_and_dependency_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lean-toolchain").write_text("leanprover/lean4:v4.32.2", encoding="utf-8")
            for name in ("lakefile.toml", "lake-manifest.json"):
                (root / name).write_text(name, encoding="utf-8")
            (root / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (root / ".lake" / "packages" / "mathlib" / "Mathlib.lean").write_text("", encoding="utf-8")
            toolchain = root / "toolchain"
            (toolchain / "bin").mkdir(parents=True)
            (toolchain / "lib" / "lean").mkdir(parents=True)
            suffix = ".exe" if os.name == "nt" else ""
            for name in ("lean", "lake"):
                (toolchain / "bin" / f"{name}{suffix}").write_text(name, encoding="utf-8")
            library = toolchain / "lib" / "lean" / "Init.olean"
            library.write_text("first", encoding="utf-8")
            with patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch(
                "proofweave.certifiers.lean._dependency_fingerprint",
                return_value=({"dependency/closure": "first"}, True),
            ):
                first = environment_fingerprint(root)
                timestamps = library.stat()
                library.write_text("other", encoding="utf-8")
                os.utime(library, ns=(timestamps.st_atime_ns, timestamps.st_mtime_ns))
                second = environment_fingerprint(root)
            with patch(
                "proofweave.certifiers.lean._toolchain_directory", return_value=toolchain
            ), patch(
                "proofweave.certifiers.lean._dependency_fingerprint",
                return_value=({"dependency/closure": "second"}, True),
            ):
                dependency_changed = environment_fingerprint(root)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(second["fingerprint"], dependency_changed["fingerprint"])

    def test_dependency_fingerprint_rejects_path_or_revision_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = (
                (".", "0" * 40),
                ("..", "0" * 40),
                ("../mathlib", "0" * 40),
                ("mathlib", "not-a-commit"),
            )
            for name, revision in cases:
                with self.subTest(name=name, revision=revision):
                    manifest = {
                        "packages": [{
                            "name": name,
                            "scope": "leanprover-community",
                            "url": "https://github.com/leanprover-community/mathlib4",
                            "rev": revision,
                            "inputRev": "v4.32.2",
                        }],
                    }
                    (root / "lake-manifest.json").write_text(
                        json.dumps(manifest), encoding="utf-8"
                    )
                    files, valid = _dependency_fingerprint(root)
                    self.assertFalse(valid)
                    self.assertIn("dependency/closure", files)

    def test_dependency_fingerprint_rejects_ancestor_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision = "0" * 40
            manifest = {
                "packages": [{
                    "name": "mathlib",
                    "scope": "leanprover-community",
                    "url": "https://github.com/leanprover-community/mathlib4",
                    "rev": revision,
                    "inputRev": "v4.32.2",
                }],
            }
            (root / "lake-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            package = root / ".lake" / "packages" / "mathlib"
            artifacts = package / ".lake" / "build" / "lib" / "lean"
            artifacts.mkdir(parents=True)
            (artifacts / "Mathlib.olean").write_text("artifact", encoding="utf-8")
            responses = (
                (0, str(root)),
                (0, revision),
                (0, ""),
            )
            with patch("proofweave.certifiers.lean._git_output", side_effect=responses):
                files, valid = _dependency_fingerprint(root)
        self.assertFalse(valid)
        self.assertIn("dependency/mathlib", files)

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
        result = run_batch(repository, [
            {"id": "true", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1", "tactic": "ring", "exact": None},
            {"id": "false", "target": "forall x : Int, (x + 1)^2 = x^2 + 2*x + 2", "tactic": "ring", "exact": None},
        ])
        if result["outcome"] == "HOST_LIMITED":
            if os.environ.get("PROOFWEAVE_REQUIRE_LEAN") == "1":
                self.fail(f"PROOFWEAVE_REQUIRE_LEAN=1 but pinned Lean/Mathlib is unavailable: {result}")
            self.skipTest("Pinned Mathlib cache is not installed")
        self.assertEqual("FAILED", result["outcome"])
        self.assertEqual("PASSED", result["results"]["true"])
        self.assertEqual("FAILED", result["results"]["false"])
