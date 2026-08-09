from __future__ import annotations

import hashlib
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
PINNED_TOOLCHAIN = re.compile(r"leanprover/lean4:v([0-9]+\.[0-9]+\.[0-9]+)")
LEAN_VERSION = re.compile(r"Lean \(version ([0-9]+\.[0-9]+\.[0-9]+)(?:, [^)]*)?\)")
VERSION_PROBE_TIMEOUT = 60


def _toolchain_directory(root: Path) -> Path | None:
    toolchain = root / "lean-toolchain"
    if not toolchain.is_file():
        return None
    name = toolchain.read_text(encoding="utf-8").strip().replace("/", "--").replace(":", "---")
    configured_home = os.environ.get("ELAN_HOME")
    elan_home = Path(configured_home) if configured_home else Path(
        os.environ.get("USERPROFILE", Path.home())
    ) / ".elan"
    candidate = elan_home / "toolchains" / name
    return candidate if candidate.is_dir() else None


def _semantic_tree_digest(root: Path, *, all_files: bool = False) -> str:
    root = root.resolve()
    if not root.is_dir():
        return "MISSING"
    try:
        paths = sorted(
            (
                path for path in root.rglob("*")
                if path.is_file() and (
                    all_files
                    or path.name.endswith((".olean", ".olean.private", ".dll", ".so", ".dylib"))
                )
            ),
            key=lambda path: path.relative_to(root).as_posix(),
        )
        if not paths:
            return "MISSING"
        content = hashlib.sha256()
        for path in paths:
            content.update(path.relative_to(root).as_posix().encode("utf-8"))
            content.update(b"\0")
            content.update(hash_file(path).encode("ascii"))
            content.update(b"\0")
        return content.hexdigest()
    except OSError:
        return "MISSING"


def _git_output(
    directory: Path, *arguments: str, executable: str | None = None
) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            [executable or "git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return (
        completed.returncode if not completed.stderr.strip() else 1,
        completed.stdout.strip(),
    )


def _dependency_fingerprint(root: Path) -> tuple[dict[str, str], bool]:
    discovered_git = shutil.which("git")
    git_path = Path(discovered_git).resolve() if discovered_git else None
    if not git_path or not git_path.is_file():
        return {"dependency/git-executable": "MISSING", "dependency/closure": "INVALID"}, False
    manifest_path = root / "lake-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"dependency/closure": "INVALID"}, False
    packages = manifest.get("packages") if isinstance(manifest, dict) else None
    if not isinstance(packages, list) or not packages:
        return {"dependency/closure": "INVALID"}, False
    fingerprints: dict[str, str] = {"dependency/git-executable": hash_file(git_path)}
    records: list[dict[str, Any]] = []
    valid = True
    seen: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            valid = False
            continue
        identity = {key: package.get(key) for key in ("name", "scope", "url", "rev", "inputRev")}
        name, revision = identity["name"], identity["rev"]
        if (
            not all(isinstance(value, str) and value for value in identity.values())
            or not isinstance(name, str)
            or name in seen
            or re.fullmatch(r"[A-Za-z0-9_.-]+", name) is None
            or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        ):
            valid = False
            continue
        seen.add(name)
        packages_root = root / ".lake" / "packages"
        package_root = packages_root / name
        if name in {".", ".."} or package_root.parent.resolve() != packages_root.resolve():
            valid = False
            continue
        toplevel_code, toplevel = _git_output(
            package_root, "rev-parse", "--show-toplevel", executable=str(git_path)
        )
        head_code, head = _git_output(
            package_root, "rev-parse", "HEAD", executable=str(git_path)
        )
        status_code, status = _git_output(
            package_root, "status", "--porcelain=v1", "--untracked-files=all",
            executable=str(git_path),
        )
        artifact_digest = _semantic_tree_digest(package_root / ".lake" / "build" / "lib" / "lean")
        toplevel_matches = (
            toplevel_code == 0
            and bool(toplevel)
            and Path(toplevel).resolve() == package_root.resolve()
        )
        package_valid = (
            toplevel_matches
            and head_code == 0
            and status_code == 0
            and head == revision
            and not status
        )
        valid = valid and package_valid
        record = {
            **identity,
            "actual_head": head,
            "git_toplevel_matches": toplevel_matches,
            "clean": status_code == 0 and not status,
            "lean_artifacts": artifact_digest,
            "valid": package_valid,
        }
        records.append(record)
        fingerprints[f"dependency/{name}"] = hash_json(record)
    valid = valid and "mathlib" in seen and len(seen) == len(packages)
    fingerprints["dependency/closure"] = hash_json(sorted(records, key=lambda item: str(item["name"])))
    return fingerprints, valid


def environment_fingerprint(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    files: dict[str, str] = {}
    for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json"):
        path = root / name
        files[name] = hash_file(path) if path.is_file() else "MISSING"
    pin_path = root / "lean-toolchain"
    pin = pin_path.read_text(encoding="utf-8").strip() if pin_path.is_file() else ""
    pin_match = PINNED_TOOLCHAIN.fullmatch(pin)
    expected_version = pin_match.group(1) if pin_match else None
    toolchain = _toolchain_directory(root)
    suffix = ".exe" if sys.platform == "win32" else ""
    executables: dict[str, Path | None] = {}
    for name in ("lean", "lake"):
        path = toolchain / "bin" / f"{name}{suffix}" if toolchain else Path("MISSING")
        executables[name] = path.resolve() if path.is_file() else None
        files[f"toolchain/{name}"] = hash_file(path) if path.is_file() else "MISSING"
    files["toolchain/bin-tree"] = (
        _semantic_tree_digest(toolchain / "bin", all_files=True) if toolchain else "MISSING"
    )
    files["toolchain/library-tree"] = (
        _semantic_tree_digest(toolchain / "lib" / "lean") if toolchain else "MISSING"
    )
    dependency_files, dependency_valid = _dependency_fingerprint(root)
    files.update(dependency_files)
    lake = executables["lake"]
    mathlib = root / ".lake" / "packages" / "mathlib" / "Mathlib.lean"
    available = bool(
        lake
        and expected_version
        and dependency_valid
        and all(value != "MISSING" for value in files.values())
        and all(value != "INVALID" for value in files.values())
        and mathlib.is_file()
    )
    return {
        "available": available,
        "fingerprint": hash_json(files),
        "files": files,
        "lake_path": str(lake) if lake else None,
        "expected_version": expected_version,
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


def run_batch(root: Path, specs: list[dict[str, Any]], *, timeout: int = 300) -> dict[str, Any]:
    if not specs:
        environment = environment_fingerprint(root)
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
    environment = environment_fingerprint(root)
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
                timeout=VERSION_PROBE_TIMEOUT,
                check=False,
            )
            version_text = (version.stdout or version.stderr).strip()
            version_match = LEAN_VERSION.fullmatch(version_text)
            if (
                version.returncode != 0
                or version_match is None
                or version_match.group(1) != environment["expected_version"]
            ):
                return {
                    "outcome": "HOST_LIMITED",
                    "toolchain_version": None,
                    "environment": environment,
                    "results": {spec["id"]: "HOST_LIMITED" for spec in specs},
                    "diagnostics": [{
                        "message": "Pinned Lean version check failed",
                        "expected": environment["expected_version"],
                        "observed": version_text,
                        "returncode": version.returncode,
                    }],
                    "invocations": 1,
                    "source": source,
                }
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
        "toolchain_version": version_text,
        "environment": environment,
        "results": results,
        "diagnostics": diagnostics,
        "invocations": 1,
        "source": source,
    }
