from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..core import CoreError, hash_file, hash_json

CERTIFIER_NAME = "lean"
CERTIFIER_VERSION = "2.0.0"
ALLOWED_TACTICS = {"ring", "ring_nf", "norm_num", "linarith", "nlinarith", "positivity", "exact"}
BANNED = re.compile(
    r"(?i)(\bsorry\b|\badmit\b|\baxiom\b|\bunsafe\b|\brun_tac\b|"
    r"\bnative_decide\b|\bimport\b|\btheorem\b|\bdef\b|\bnamespace\b|"
    r"\bsection\b|\bend\b|\bby\b|:=|#|;)"
)


def _toolchain_directory(root: Path) -> Path | None:
    toolchain = root / "lean-toolchain"
    if not toolchain.is_file():
        return None
    name = toolchain.read_text(encoding="utf-8").strip().replace("/", "--").replace(":", "---")
    home = Path(os.environ.get("USERPROFILE", Path.home()))
    candidate = home / ".elan" / "toolchains" / name
    return candidate if candidate.is_dir() else None


def environment_fingerprint(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    files: dict[str, str] = {}
    for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json"):
        path = root / name
        files[name] = hash_file(path) if path.is_file() else "MISSING"
    toolchain = _toolchain_directory(root)
    suffix = ".exe" if sys.platform == "win32" else ""
    for name in ("lean", "lake"):
        path = toolchain / "bin" / f"{name}{suffix}" if toolchain else Path("MISSING")
        files[f"toolchain/{name}"] = hash_file(path) if path.is_file() else "MISSING"
    lake = shutil.which("lake")
    mathlib = root / ".lake" / "packages" / "mathlib" / "Mathlib.lean"
    available = bool(
        lake
        and toolchain
        and all(value != "MISSING" for value in files.values())
        and mathlib.is_file()
    )
    return {
        "available": available,
        "fingerprint": hash_json(files),
        "files": files,
        "lake_path": str(Path(lake).resolve()) if lake else None,
        "toolchain_path": str(toolchain) if toolchain else None,
    }


def _validate_spec(spec: dict[str, Any], known: set[str]) -> None:
    target, tactic = spec.get("target"), spec.get("tactic")
    if not isinstance(target, str) or not target.strip():
        raise CoreError(f"Certificate {spec.get('id')} requires a non-empty target")
    if "\n" in target or "\r" in target or BANNED.search(target):
        raise CoreError(f"Certificate {spec.get('id')} contains forbidden Lean syntax")
    if tactic not in ALLOWED_TACTICS:
        raise CoreError(f"Certificate {spec.get('id')} uses unsupported tactic {tactic!r}")
    exact = spec.get("exact")
    if tactic == "exact":
        if not isinstance(exact, str) or exact not in known:
            raise CoreError(f"Certificate {spec.get('id')} exact target must be an earlier certified node")
    elif exact is not None:
        raise CoreError(f"Certificate {spec.get('id')} may use `exact` only with tactic=\"exact\"")


def _source(specs: list[dict[str, Any]]) -> tuple[str, dict[str, tuple[int, int]], dict[str, str]]:
    lines = ["import Mathlib", "set_option autoImplicit false", ""]
    spans: dict[str, tuple[int, int]] = {}
    names = {spec["id"]: f"pw_{index}_{hash_json(spec)[:10]}" for index, spec in enumerate(specs, 1)}
    known: set[str] = set()
    for spec in specs:
        _validate_spec(spec, known)
        start = len(lines) + 1
        lines.append(f"theorem {names[spec['id']]} : ({spec['target']}) := by")
        tactic = spec["tactic"]
        lines.append(
            f"  exact {names[spec['exact']]}"
            if tactic == "exact"
            else f"  intros <;> {tactic}"
        )
        lines.append("")
        spans[spec["id"]] = (start, len(lines))
        known.add(spec["id"])
    return "\n".join(lines), spans, names


def _error_lines(output: str) -> tuple[set[int], list[dict[str, Any]], bool]:
    lines: set[int] = set()
    diagnostics: list[dict[str, Any]] = []
    unlocated = False
    for raw in output.splitlines():
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or value.get("severity") != "error":
            continue
        diagnostics.append(value)
        line = (value.get("pos") or {}).get("line")
        if isinstance(line, int):
            lines.add(line)
        else:
            unlocated = True
    return lines, diagnostics, unlocated


def run_batch(root: Path, specs: list[dict[str, Any]], *, timeout: int = 120) -> dict[str, Any]:
    environment = environment_fingerprint(root)
    if not specs:
        return {
            "outcome": "UNSUPPORTED",
            "toolchain_version": None,
            "environment": environment,
            "results": {},
            "diagnostics": [],
            "invocations": 0,
            "source": "",
        }
    source, spans, _ = _source(specs)
    if not environment["available"]:
        return {
            "outcome": "HOST_LIMITED",
            "toolchain_version": None,
            "environment": environment,
            "results": {spec["id"]: "HOST_LIMITED" for spec in specs},
            "diagnostics": [],
            "invocations": 0,
            "source": source,
        }
    lake = environment["lake_path"]
    process_environment = os.environ.copy()
    process_environment.pop("LEAN_PATH", None)
    with tempfile.TemporaryDirectory(prefix="proofweave-lean-") as directory:
        target = Path(directory) / "Certificate.lean"
        target.write_text(source, encoding="utf-8", newline="\n")
        try:
            version = subprocess.run(
                [lake, "env", "lean", "--version"],
                cwd=root,
                env=process_environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            completed = subprocess.run(
                [lake, "env", "lean", "--json", "-R", directory, str(target)],
                cwd=root,
                env=process_environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "outcome": "HOST_LIMITED",
                "toolchain_version": None,
                "environment": environment,
                "results": {spec["id"]: "HOST_LIMITED" for spec in specs},
                "diagnostics": [{"message": type(exc).__name__}],
                "invocations": 1,
                "source": source,
            }
    output = completed.stdout + "\n" + completed.stderr
    error_lines, diagnostics, unlocated = _error_lines(output)
    results: dict[str, str] = {}
    for spec in specs:
        start, end = spans[spec["id"]]
        results[spec["id"]] = "FAILED" if any(start <= line <= end for line in error_lines) else "PASSED"
    if completed.returncode and (unlocated or not error_lines):
        results = {spec["id"]: "FAILED" for spec in specs}
    failed = any(value == "FAILED" for value in results.values())
    return {
        "outcome": "FAILED" if failed else "PASSED",
        "toolchain_version": (version.stdout or version.stderr).strip() if version.returncode == 0 else None,
        "environment": environment,
        "results": results,
        "diagnostics": diagnostics,
        "invocations": 1,
        "source": source,
    }
