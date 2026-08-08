from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .certifiers.lean import CERTIFIER_NAME, CERTIFIER_VERSION, environment_fingerprint
from .certify import Runner, certify, run_consistency_errors
from .core import (
    ALIGNMENTS,
    LIFECYCLES,
    PROOF_STATUSES,
    CoreError,
    atomic_write_text,
    cycle_path,
    find_root,
    hash_bytes,
    hash_file,
    hash_json,
    parse_input,
    read_json,
    utc_now,
    verify_artifacts,
    write_json,
)
from .distill import distill
from .render import render_concept_map, render_paper

PIPELINE_VERSION = "2.0.0"
FORBIDDEN_TREES = {
    ".agents", ".claude", ".codex", "agents", "benchmarks", "config", "experiments",
    "literature", "mathlab", "paper", "prompts", "research", "reviews", "scripts", "state", "workflows",
}


def initialize(root: Path | str) -> dict[str, Any]:
    project = Path(root).resolve()
    created: list[str] = []
    for relative in (Path("workspace/claims"), Path("artifacts")):
        path = project / relative
        if not path.exists():
            path.mkdir(parents=True)
            created.append(relative.as_posix())
    return {"result": "initialized", "root": str(project), "created": created}


def _records(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / "workspace" / "claims").glob("*.json")):
        records.append((path, read_json(path)))
    return records


def _active(records: list[tuple[Path, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    active: dict[str, dict[str, Any]] = {}
    for _, record in records:
        if record.get("lifecycle") != "ACTIVE":
            continue
        claim_id = record.get("claim_id")
        if claim_id in active:
            raise CoreError(f"Multiple ACTIVE revisions for claim {claim_id}")
        active[claim_id] = record
    return active


def _dependency_snapshot(
    parsed: dict[str, Any], records: list[tuple[Path, dict[str, Any]]]
) -> tuple[dict[str, str], bool]:
    active = _active(records)
    missing = sorted(set(parsed["dependencies"]) - set(active))
    if missing:
        raise CoreError(f"Unknown ACTIVE dependencies: {', '.join(missing)}")
    graph = {claim_id: value.get("dependencies", []) for claim_id, value in active.items()}
    graph[parsed["claim_id"]] = parsed["dependencies"]
    cycle = cycle_path(graph)
    if cycle:
        raise CoreError(f"Claim dependency cycle: {' -> '.join(cycle)}")
    digests = {
        dependency: active[dependency].get("certificate_digest")
        or f"UNVERIFIED:{active[dependency].get('revision_id')}"
        for dependency in parsed["dependencies"]
    }
    ready = all(active[item].get("proof_status") == "CERTIFIED" for item in parsed["dependencies"])
    return digests, ready


def _alignment(parsed: dict[str, Any], existing: dict[str, Any] | None, confirm: bool) -> tuple[str, str | None, str | None]:
    target = (parsed.get("top_certificate") or {}).get("target")
    formal_hash = hash_json(target) if isinstance(target, str) else None
    pair_hash = hash_json(
        {"statement_hash": parsed["statement_hash"], "formal_target_hash": formal_hash}
    ) if formal_hash else None
    if confirm:
        if not pair_hash:
            raise CoreError("--confirm-alignment requires a whole-claim ## Certificate target")
        return "CONFIRMED", formal_hash, pair_hash
    if existing and existing.get("alignment") == "CONFIRMED":
        return ("CONFIRMED" if existing.get("alignment_hash") == pair_hash else "STALE"), formal_hash, pair_hash
    if existing and existing.get("alignment") == "STALE":
        return "STALE", formal_hash, pair_hash
    return "UNCONFIRMED", formal_hash, pair_hash


def _cached(root: Path, directory: Path, expected_key: str) -> dict[str, Any] | None:
    run_path, digest_path = directory / "run.json", directory / "run.sha256"
    if not run_path.is_file() or not digest_path.is_file():
        return None
    if hash_file(run_path) != digest_path.read_text(encoding="utf-8").strip():
        return None
    run = read_json(run_path)
    prefix = directory.relative_to(root).as_posix() + "/"
    artifact_names = run.get("artifacts", {})
    if (
        run.get("cache_key") != expected_key
        or run.get("run_id") != expected_key
        or not isinstance(artifact_names, dict)
        or any(not isinstance(name, str) or not name.startswith(prefix) for name in artifact_names)
        or run_consistency_errors(run)
        or verify_artifacts(root, run)
    ):
        return None
    reused = dict(run)
    reused["cache_hit"] = True
    reused["artifact_directory"] = str(directory)
    reused["invocations"] = {"model": 0, "semantic_extraction": 0, "certifier": 0}
    return reused


def _write_artifact(root: Path, path: Path, text: str, artifacts: dict[str, str]) -> None:
    atomic_write_text(path, text)
    artifacts[path.relative_to(root).as_posix()] = hash_file(path)


def _save_claim(
    root: Path,
    records: list[tuple[Path, dict[str, Any]]],
    parsed: dict[str, Any],
    run: dict[str, Any],
    alignment: str,
    formal_hash: str | None,
    pair_hash: str | None,
) -> None:
    for path, record in records:
        if record.get("claim_id") == parsed["claim_id"] and record.get("lifecycle") == "REVOKED":
            raise CoreError(f"Claim {parsed['claim_id']} is REVOKED")
        if (
            record.get("claim_id") == parsed["claim_id"]
            and record.get("lifecycle") == "ACTIVE"
            and record.get("revision_id") != parsed["revision_id"]
        ):
            record["lifecycle"] = "SUPERSEDED"
            record["updated_at"] = utc_now()
            write_json(path, record)
    record = {
        "schema_version": 2,
        "claim_id": parsed["claim_id"],
        "revision_id": parsed["revision_id"],
        "title": parsed["title"],
        "statement": parsed["statement"],
        "assumptions": parsed["assumptions"],
        "quantifiers": parsed["quantifiers"],
        "dependencies": parsed["dependencies"],
        "statement_hash": parsed["statement_hash"],
        "source_path": parsed["source_path"],
        "source_hash": parsed["source_hash"],
        "formal_target_hash": formal_hash,
        "alignment_hash": pair_hash if alignment == "CONFIRMED" else None,
        "alignment": alignment,
        "proof_status": run["proof_status"],
        "lifecycle": "ACTIVE",
        "latest_run_id": run["run_id"],
        "certificate_digest": run["certificate"]["cache_key"] if run["proof_status"] == "CERTIFIED" else None,
        "updated_at": utc_now(),
    }
    name = f"{parsed['claim_id']}--{parsed['revision_id'][:16]}.json"
    write_json(root / "workspace" / "claims" / name, record)


def run_proof(
    input_path: Path | str,
    *,
    root: Path | str | None = None,
    confirm_alignment: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    parsed = parse_input(input_path)
    project = Path(root).resolve() if root else find_root(parsed["source_path"])
    records = _records(project)
    existing = next(
        (record for _, record in records if record.get("claim_id") == parsed["claim_id"] and record.get("revision_id") == parsed["revision_id"]),
        None,
    )
    dependency_digests, dependencies_ready = _dependency_snapshot(parsed, records)
    alignment, formal_hash, pair_hash = _alignment(parsed, existing, confirm_alignment)
    environment = environment_fingerprint(project)
    run_key = hash_json(
        {
            "pipeline": PIPELINE_VERSION,
            "source_hash": parsed["source_hash"],
            "revision_id": parsed["revision_id"],
            "dependencies": dependency_digests,
            "alignment": alignment,
            "alignment_hash": pair_hash if alignment == "CONFIRMED" else None,
            "certifier": CERTIFIER_NAME,
            "certifier_version": CERTIFIER_VERSION,
            "environment": environment["fingerprint"],
        }
    )
    directory = project / "artifacts" / parsed["claim_id"] / run_key
    cached = _cached(project, directory, run_key)
    if cached:
        _save_claim(project, records, parsed, cached, alignment, formal_hash, pair_hash)
        return cached
    result = certify(
        project,
        parsed,
        dependency_digests=dependency_digests,
        dependencies_ready=dependencies_ready,
        runner=runner,
    )
    distilled = {"nodes": [], "presentation_to_certificate": {}}
    if not result["fast_path"]:
        distilled = distill(parsed["proof_ir"], result["certificate"])
    directory.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    _write_artifact(project, directory / "input.md", parsed["source_text"], artifacts)
    _write_artifact(project, directory / "paper_proof.md", render_paper(parsed, distilled, result, alignment), artifacts)
    _write_artifact(project, directory / "concept_map.md", render_concept_map(parsed, distilled, result, alignment), artifacts)
    _write_artifact(project, directory / "coverage.json", json.dumps(result["coverage"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", artifacts)
    _write_artifact(project, directory / "certificate.json", json.dumps(result["certificate"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", artifacts)
    if result["certificate_source"]:
        _write_artifact(project, directory / "certificate.lean", result["certificate_source"], artifacts)
    if not result["fast_path"]:
        _write_artifact(project, directory / "proof_ir.json", json.dumps(parsed["proof_ir"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", artifacts)
    run = {
        "schema_version": 2,
        "run_id": run_key,
        "claim_id": parsed["claim_id"],
        "source_hash": parsed["source_hash"],
        "statement_hash": parsed["statement_hash"],
        "cache_key": run_key,
        "cache_hit": False,
        "fast_path": result["fast_path"],
        "alignment": alignment,
        "proof_status": result["proof_status"],
        "coverage": result["coverage"],
        "certificate": result["certificate"],
        "invocations": {"model": 0, "semantic_extraction": 0 if result["fast_path"] else 1, "certifier": result["certifier_invocations"]},
        "artifacts": artifacts,
        "created_at": utc_now(),
    }
    write_json(directory / "run.json", run)
    atomic_write_text(directory / "run.sha256", hash_file(directory / "run.json") + "\n")
    _save_claim(project, records, parsed, run, alignment, formal_hash, pair_hash)
    returned = dict(run)
    returned["artifact_directory"] = str(directory)
    return returned


def status(root: Path | str | None = None, claim_id: str | None = None) -> dict[str, Any]:
    project = Path(root).resolve() if root else find_root()
    values: list[dict[str, Any]] = []
    for _, record in _records(project):
        if claim_id and record.get("claim_id") != claim_id:
            continue
        value = dict(record)
        source = Path(value.get("source_path", ""))
        if value.get("alignment") == "CONFIRMED" and source.is_file() and hash_file(source) != value.get("source_hash"):
            value["alignment"] = "STALE"
        values.append(value)
    if claim_id and not values:
        raise CoreError(f"Unknown claim_id: {claim_id}")
    values.sort(key=lambda item: (item.get("claim_id", ""), item.get("revision_id", "")))
    return {
        "claims": values,
        "counts": {
            "alignment": dict(Counter(item["alignment"] for item in values)),
            "proof_status": dict(Counter(item["proof_status"] for item in values)),
            "lifecycle": dict(Counter(item["lifecycle"] for item in values)),
        },
    }


def _valid_claim(record: dict[str, Any]) -> list[str]:
    required = {"claim_id", "revision_id", "statement", "assumptions", "quantifiers", "dependencies", "alignment", "proof_status", "lifecycle"}
    errors = [f"missing claim field {name}" for name in sorted(required - set(record))]
    if record.get("alignment") not in ALIGNMENTS:
        errors.append("invalid alignment")
    if record.get("proof_status") not in PROOF_STATUSES:
        errors.append("invalid proof_status")
    if record.get("lifecycle") not in LIFECYCLES:
        errors.append("invalid lifecycle")
    statement, quantifiers = record.get("statement"), record.get("quantifiers")
    assumptions, dependencies = record.get("assumptions"), record.get("dependencies")
    if isinstance(statement, str) and isinstance(quantifiers, list):
        expected_statement = hash_json({"statement": statement, "quantifiers": quantifiers})
        if record.get("statement_hash") != expected_statement:
            errors.append("statement_hash mismatch")
        if isinstance(assumptions, list) and isinstance(dependencies, list):
            expected_revision = hash_json(
                {"statement_hash": expected_statement, "assumptions": assumptions, "dependencies": dependencies}
            )
            if record.get("revision_id") != expected_revision:
                errors.append("revision_id mismatch")
    if record.get("proof_status") == "CERTIFIED" and not record.get("certificate_digest"):
        errors.append("CERTIFIED claim lacks certificate_digest")
    return errors


def check_project(root: Path | str | None = None) -> dict[str, Any]:
    project = Path(root).resolve() if root else find_root()
    errors: list[str] = []
    schema_files = sorted((project / "schemas").glob("*.json"))
    for path in schema_files:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"wrong schema draft: {path.name}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid schema {path.name}: {exc}")
    modules = sorted((project / "proofweave").rglob("*.py"))
    line_counts = {path.relative_to(project).as_posix(): len(path.read_text(encoding="utf-8").splitlines()) for path in modules}
    if len(modules) != 10:
        errors.append(f"production module budget: {len(modules)} != 10")
    if len(schema_files) != 3:
        errors.append(f"schema budget: {len(schema_files)} != 3")
    if line_counts.get("proofweave/cli.py", 0) > 200:
        errors.append("cli.py exceeds 200 lines")
    for name, count in line_counts.items():
        if count >= 400:
            errors.append(f"production file reaches 400 lines: {name} ({count})")
    if sum(line_counts.values()) > 2500:
        errors.append(f"production LOC exceeds 2500: {sum(line_counts.values())}")
    for name in sorted(FORBIDDEN_TREES):
        if (project / name).exists():
            errors.append(f"removed v1 tree still exists: {name}")
    records = _records(project)
    active: dict[str, int] = Counter(record.get("claim_id") for _, record in records if record.get("lifecycle") == "ACTIVE")
    errors.extend(f"multiple ACTIVE revisions: {key}" for key, count in active.items() if count > 1)
    graph: dict[str, list[str]] = {}
    active_records = {record.get("claim_id"): record for _, record in records if record.get("lifecycle") == "ACTIVE"}
    for path, record in records:
        errors.extend(f"{path.name}: {message}" for message in _valid_claim(record))
        if record.get("lifecycle") == "ACTIVE":
            graph[record["claim_id"]] = record.get("dependencies", [])
            missing = set(record.get("dependencies", [])) - set(active_records)
            if missing:
                errors.append(f"{record['claim_id']}: missing ACTIVE dependencies {sorted(missing)}")
    cycle = cycle_path(graph)
    if cycle:
        errors.append(f"claim dependency cycle: {' -> '.join(cycle)}")
    for run_path in sorted((project / "artifacts").glob("*/*/run.json")):
        digest = run_path.with_name("run.sha256")
        if not digest.is_file() or hash_file(run_path) != digest.read_text(encoding="utf-8").strip():
            errors.append(f"run digest mismatch: {run_path.relative_to(project)}")
            continue
        run = read_json(run_path)
        if run.get("run_id") != run_path.parent.name or run.get("cache_key") != run_path.parent.name:
            errors.append(f"run identity/path mismatch: {run_path.relative_to(project)}")
        prefix = run_path.parent.relative_to(project).as_posix() + "/"
        artifact_names = run.get("artifacts", {})
        if not isinstance(artifact_names, dict) or any(
            not isinstance(name, str) or not name.startswith(prefix) for name in artifact_names
        ):
            errors.append(f"artifact outside run directory: {run_path.relative_to(project)}")
        errors.extend(f"{run_path.relative_to(project)}: {message}" for message in verify_artifacts(project, run))
        errors.extend(
            f"{run_path.relative_to(project)}: {message}" for message in run_consistency_errors(run)
        )
    source = "\n".join(path.read_text(encoding="utf-8") for path in modules)
    forbidden_imports = ("from " + "tools", "import " + "tools")
    if any(pattern in source for pattern in forbidden_imports):
        errors.append("runtime imports migration tools")
    cli_text = (project / "proofweave" / "cli.py").read_text(encoding="utf-8")
    command_count = cli_text.count('commands.add_parser("')
    if command_count != 4:
        errors.append(f"top-level command budget: {command_count} != 4")
    metrics = {
        "production_modules": len(modules),
        "production_loc": sum(line_counts.values()),
        "largest_file": max(line_counts.items(), key=lambda item: item[1]) if line_counts else None,
        "cli_lines": line_counts.get("proofweave/cli.py", 0),
        "schemas": len(schema_files),
        "commands": command_count,
        "mandatory_role_workflow_files": 0,
    }
    return {"result": "PASS" if not errors else "FAIL", "errors": errors, "metrics": metrics}
