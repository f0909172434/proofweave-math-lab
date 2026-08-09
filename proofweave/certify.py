from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .certifiers.lean import CERTIFIER_NAME, CERTIFIER_VERSION, run_batch
from .core import PROOF_STATUSES, hash_json

Runner = Callable[[Path, list[dict[str, Any]]], dict[str, Any]]


def run_consistency_errors(run: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    coverage, certificate = run.get("coverage"), run.get("certificate")
    if not isinstance(coverage, dict) or not isinstance(certificate, dict):
        return ["run requires coverage and certificate objects"]
    status = run.get("proof_status")
    keys = ("deductive_total", "certified", "failed", "unsupported", "host_limited")
    counts = tuple(coverage.get(key) for key in keys)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        return ["coverage counts must be non-negative integers"]
    total, certified, failed, unsupported, host_limited = counts
    if certified + failed + unsupported + host_limited != total:
        errors.append("coverage counts do not sum to deductive_total")
    expected_percentage = round(100.0 * certified / total, 2) if total else 0.0
    if coverage.get("percentage") != expected_percentage:
        errors.append("coverage percentage mismatch")
    results = certificate.get("results")
    if not isinstance(results, dict):
        errors.append("certificate results must be an object")
        results = {}
    for result, key in (("PASSED", "certified"), ("FAILED", "failed"), ("HOST_LIMITED", "host_limited")):
        if list(results.values()).count(result) != coverage.get(key):
            errors.append(f"certificate {result} count does not match coverage")
    if status == "CERTIFIED" and not (
        total > 0 and certified == total and failed == unsupported == host_limited == 0
        and certificate.get("outcome") == "PASSED"
    ):
        errors.append("partial-as-certified")
    elif status == "FAILED" and failed == 0:
        errors.append("FAILED run has no failed obligation")
    elif status == "PARTIAL" and total > 0 and certified == total:
        errors.append("fully certified run is marked PARTIAL")
    elif status not in PROOF_STATUSES:
        errors.append("invalid proof_status")
    return errors


def _spec(identifier: str, certificate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": identifier,
        "target": certificate.get("target"),
        "tactic": certificate.get("tactic"),
        "exact": certificate.get("exact"),
    }


def certificate_view(parsed: dict[str, Any], fast_path: bool) -> dict[str, Any]:
    if fast_path:
        return {"claim": parsed["top_certificate"]}
    return {
        "nodes": [
            {
                "id": node["id"],
                "role": node["role"],
                "text": node["text"],
                "depends_on": node["depends_on"],
                "alias_of": node["alias_of"],
                "certificate": node["certificate"],
            }
            for node in parsed["proof_ir"]["nodes"]
        ]
    }


def certify(
    root: Path,
    parsed: dict[str, Any],
    *,
    dependency_digests: dict[str, str],
    dependencies_ready: bool,
    runner: Runner | None = None,
) -> dict[str, Any]:
    fast_path = parsed["top_certificate"] is not None
    if fast_path:
        obligations = ["claim"]
        specs = [_spec("claim", parsed["top_certificate"])]
    else:
        nodes = parsed["proof_ir"]["nodes"]
        obligations = [node["id"] for node in nodes if node["role"] != "alias"]
        specs = [_spec(node["id"], node["certificate"]) for node in nodes if node["role"] != "alias" and node["certificate"]]
    if not dependencies_ready:
        specs = []
    backend = runner(root, specs) if runner else run_batch(root, specs)
    results = backend.get("results", {})
    certified = [identifier for identifier in obligations if results.get(identifier) == "PASSED"]
    failed = [identifier for identifier in obligations if results.get(identifier) == "FAILED"]
    host_limited = [identifier for identifier in obligations if results.get(identifier) == "HOST_LIMITED"]
    unsupported = [
        identifier
        for identifier in obligations
        if identifier not in certified and identifier not in failed and identifier not in host_limited
    ]
    total = len(obligations)
    if failed:
        proof_status = "FAILED"
    elif total and len(certified) == total:
        proof_status = "CERTIFIED"
    else:
        proof_status = "PARTIAL"
    coverage = {
        "deductive_total": total,
        "certified": len(certified),
        "failed": len(failed),
        "unsupported": len(unsupported),
        "host_limited": len(host_limited),
        "percentage": round(100.0 * len(certified) / total, 2) if total else 0.0,
        "certified_ids": certified,
        "failed_ids": failed,
        "unsupported_ids": unsupported,
        "host_limited_ids": host_limited,
        "dependencies_ready": dependencies_ready,
    }
    environment = backend.get("environment", {})
    key_material = {
        "schema_version": 2,
        "statement": parsed["statement"],
        "quantifiers": parsed["quantifiers"],
        "assumptions": parsed["assumptions"],
        "dependencies": dependency_digests,
        "certificate_view": certificate_view(parsed, fast_path),
        "certifier": CERTIFIER_NAME,
        "certifier_version": CERTIFIER_VERSION,
        "toolchain_version": backend.get("toolchain_version"),
        "toolchain_fingerprint": environment.get("fingerprint"),
    }
    certificate_key = hash_json(key_material)
    certificate = {
        "backend": CERTIFIER_NAME,
        "certifier_version": CERTIFIER_VERSION,
        "toolchain_version": backend.get("toolchain_version"),
        "toolchain_fingerprint": environment.get("fingerprint"),
        "cache_key": certificate_key,
        "outcome": backend.get("outcome", "UNSUPPORTED"),
        "results": results,
        "diagnostics": backend.get("diagnostics", []),
    }
    return {
        "fast_path": fast_path,
        "proof_status": proof_status,
        "coverage": coverage,
        "certificate": certificate,
        "certificate_source": backend.get("source", ""),
        "certifier_invocations": int(backend.get("invocations", 0)),
    }
