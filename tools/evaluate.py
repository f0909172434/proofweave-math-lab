"""Build reproducible ProofWeave Core and theorem-pack evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from proofweave.certifiers.lean import ALLOWED_TACTICS, environment_fingerprint, run_batch
from proofweave.core import CoreError, hash_file, hash_json, parse_input
from proofweave.pipeline import initialize, run_proof, status

SCHEMA_VERSION = 1
CATEGORY_COUNTS = {"positive": 14, "negative": 14, "attack": 8, "fail_closed": 6}
RESEARCH_STATUSES = {"OPEN", "PROPOSED", "COMPUTATIONAL", "VERIFIED"}
PROOF_STATUSES = {"UNVERIFIED", "PARTIAL", "CERTIFIED", "FAILED"}
Backend = Callable[[Path, list[dict[str, Any]]], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _repository() -> Path:
    return Path(__file__).resolve().parents[1]


def _git(repository: Path) -> dict[str, Any]:
    def command(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments], cwd=repository, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )

    revision = command("rev-parse", "HEAD")
    state = command("status", "--porcelain=v1", "--untracked-files=no")
    return {
        "commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "dirty": state.returncode != 0 or bool(state.stdout.strip()),
    }


def _environment(repository: Path) -> dict[str, Any]:
    lean = environment_fingerprint(repository)
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "lean_available": lean["available"],
        "lean_fingerprint": lean["fingerprint"],
        "lean_files": lean["files"],
    }


def load_corpus(path: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    corpus_path = path or _repository() / "tests" / "corpus" / "core_cases.toml"
    raw = corpus_path.read_bytes()
    value = tomllib.loads(raw.decode("utf-8"))
    cases = value.get("cases")
    if value.get("schema_version") != 1 or not isinstance(cases, list):
        raise ValueError("core corpus requires schema_version=1 and [[cases]]")
    identifiers = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(identifiers) != len(cases) or any(not isinstance(item, str) or not item for item in identifiers):
        raise ValueError("every corpus case requires a non-empty id")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("corpus case IDs must be unique")
    counts = {name: sum(case.get("category") == name for case in cases) for name in CATEGORY_COUNTS}
    if counts != CATEGORY_COUNTS or len(cases) != sum(CATEGORY_COUNTS.values()):
        raise ValueError(f"wrong corpus partition: {counts}")
    positive_tactics = {name: 0 for name in ALLOWED_TACTICS}
    for case in cases:
        category = case.get("category")
        if category in {"positive", "negative", "attack"}:
            if not all(isinstance(case.get(key), str) for key in ("target", "tactic", "expected")):
                raise ValueError(f"{case['id']}: malformed formal/attack case")
        if category == "positive":
            tactic = case["tactic"]
            if tactic not in positive_tactics:
                raise ValueError(f"{case['id']}: positive case uses non-allowlisted tactic")
            positive_tactics[tactic] += 1
        if category == "fail_closed" and not isinstance(case.get("scenario"), str):
            raise ValueError(f"{case['id']}: fail-closed case requires scenario")
    if set(positive_tactics.values()) != {2}:
        raise ValueError(f"positive tactic distribution must be two each: {positive_tactics}")
    return cases, _sha256(raw)


def _spec(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"], "target": case["target"], "tactic": case["tactic"],
        "exact": case.get("exact"),
    }


def _theorem(
    root: Path, claim_id: str, *, target: str | None = "True", tactic: str = "norm_num",
    proof: str = "The formal target is checked by the pinned certifier.", dependencies: list[str] | None = None,
) -> Path:
    certificate = ""
    if target is not None:
        certificate = (
            "\n## Certificate\n\n```proofweave-lean\n"
            f"target = {json.dumps(target)}\n"
            f"tactic = {json.dumps(tactic)}\n```\n"
        )
    text = (
        "+++\n" f"claim_id = {json.dumps(claim_id)}\n" f"title = {json.dumps(claim_id)}\n"
        "assumptions = [\"none\"]\nquantifiers = []\n"
        f"dependencies = {json.dumps(dependencies or [])}\n+++\n\n"
        f"## Statement\n\n{claim_id} statement.\n\n## Proof\n\n{proof}\n{certificate}"
    )
    path = root / f"{claim_id}.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class _DeterministicRunner:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, root: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
        if specs:
            self.calls += 1
        results = {spec["id"]: "PASSED" for spec in specs}
        return {
            "outcome": "PASSED" if specs else "UNSUPPORTED",
            "toolchain_version": "Lean (evaluator state fixture)",
            "environment": {"fingerprint": "0" * 64},
            "results": results,
            "diagnostics": [],
            "invocations": 1 if specs else 0,
            "source": "-- deterministic evaluator state fixture\n" if specs else "",
        }


def _evaluate_fail_closed(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in cases:
        observed = "ERROR"
        try:
            with tempfile.TemporaryDirectory(prefix="proofweave-evaluate-state-") as directory:
                root = Path(directory)
                initialize(root)
                runner = _DeterministicRunner()
                scenario = case["scenario"]
                if scenario == "partial_unsupported":
                    result = run_proof(_theorem(root, "partial", target=None), root=root, runner=runner)
                    observed = result["proof_status"]
                elif scenario == "host_limited":
                    result = run_batch(root, [{"id": "host", "target": "True", "tactic": "norm_num", "exact": None}])
                    observed = result["outcome"]
                elif scenario == "stale_alignment":
                    path = _theorem(root, "stale")
                    run_proof(path, root=root, confirm_alignment=True, runner=runner)
                    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                    observed = status(root, "stale")["claims"][0]["alignment"]
                elif scenario == "dependency_missing":
                    try:
                        run_proof(_theorem(root, "dependent", dependencies=["missing"]), root=root, runner=runner)
                    except CoreError:
                        observed = "REJECTED"
                elif scenario == "artifact_tamper":
                    path = _theorem(root, "tamper")
                    first = run_proof(path, root=root, runner=runner)
                    Path(first["artifact_directory"], "paper_proof.md").write_text("tampered", encoding="utf-8")
                    second = run_proof(path, root=root, runner=runner)
                    observed = "RECOMPUTED" if not second["cache_hit"] and runner.calls == 2 else "REUSED"
                elif scenario == "dag_cycle":
                    proof = "### a [semantic]\nDepends: b\nA.\n\n### b [bridge]\nDepends: a\nB."
                    try:
                        parse_input(_theorem(root, "cycle", target=None, proof=proof))
                    except CoreError:
                        observed = "REJECTED"
                else:
                    raise ValueError(f"unknown fail-closed scenario {scenario!r}")
        except Exception as exc:  # evidence must record a failed case, not hide it
            observed = f"ERROR:{type(exc).__name__}"
        records.append({
            "id": case["id"], "category": "fail_closed", "expected": case["expected"],
            "observed": observed, "passed": observed == case["expected"],
        })
    return records


def _cold_warm(repository: Path, backend: Backend) -> tuple[dict[str, Any], str]:
    with tempfile.TemporaryDirectory(prefix="proofweave-evaluate-cache-") as directory:
        root = Path(directory)
        initialize(root)
        path = _theorem(root, "cold-warm", target="(20 + 22 : Int) = 42")

        def repository_backend(_root: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
            return backend(repository, specs)

        cold = run_proof(path, root=root, runner=repository_backend)
        warm = run_proof(path, root=root, runner=repository_backend)
        source_path = Path(cold["artifact_directory"], "certificate.lean")
        source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
        return {
            "cold_status": cold["proof_status"],
            "cold_invocations": cold["invocations"],
            "warm_cache_hit": warm["cache_hit"],
            "warm_invocations": warm["invocations"],
            "same_run_id": cold["run_id"] == warm["run_id"],
        }, source


def evaluate_core(repository: Path | None = None, *, backend: Backend = run_batch) -> dict[str, Any]:
    repo = (repository or _repository()).resolve()
    cases, corpus_digest = load_corpus(repo / "tests" / "corpus" / "core_cases.toml")
    formal = [case for case in cases if case["category"] in {"positive", "negative"}]
    batch = backend(repo, [_spec(case) for case in formal])
    records: list[dict[str, Any]] = []
    for case in formal:
        observed = batch.get("results", {}).get(case["id"], batch.get("outcome", "MISSING"))
        records.append({
            "id": case["id"], "category": case["category"], "tactic": case["tactic"],
            "expected": case["expected"], "observed": observed, "passed": observed == case["expected"],
        })
    for case in (item for item in cases if item["category"] == "attack"):
        try:
            attack = backend(repo, [_spec(case)])
            observed = attack.get("results", {}).get(case["id"], attack.get("outcome", "MISSING"))
        except (CoreError, ValueError):
            observed = "REJECTED"
        records.append({
            "id": case["id"], "category": "attack", "expected": case["expected"],
            "observed": observed,
            "passed": case["expected"] == "NOT_PASSED" and observed != "PASSED",
        })
    records.extend(_evaluate_fail_closed([case for case in cases if case["category"] == "fail_closed"]))
    cache, cache_source = _cold_warm(repo, backend)
    positives = [record for record in records if record["category"] == "positive"]
    negatives = [record for record in records if record["category"] == "negative"]
    attacks = [record for record in records if record["category"] == "attack"]
    states = [record for record in records if record["category"] == "fail_closed"]
    certificate_sources = {
        "formal-corpus.lean": batch.get("source", ""),
        "cold-warm.lean": cache_source,
    }
    certificate_digests = {
        name: _sha256(source.encode("utf-8")) for name, source in certificate_sources.items() if source
    }
    metrics = {
        "case_total": len(records),
        "case_passed": sum(record["passed"] for record in records),
        "positive_total": len(positives),
        "positive_passed": sum(record["passed"] for record in positives),
        "negative_total": len(negatives),
        "false_certifications": sum(record["observed"] == "PASSED" for record in negatives),
        "attack_total": len(attacks),
        "attack_acceptances": sum(record["observed"] == "PASSED" for record in attacks),
        "fail_closed_total": len(states),
        "fail_closed_passed": sum(record["passed"] for record in states),
        "formal_lean_invocations": batch.get("invocations", 0),
        "cold_warm": cache,
    }
    cache_passed = (
        cache["cold_status"] == "CERTIFIED"
        and cache["cold_invocations"] == {"model": 0, "semantic_extraction": 0, "certifier": 1}
        and cache["warm_cache_hit"] and cache["same_run_id"]
        and cache["warm_invocations"] == {"model": 0, "semantic_extraction": 0, "certifier": 0}
    )
    passed = all(record["passed"] for record in records) and cache_passed
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "mode": "core",
        "result": "PASS" if passed else "FAIL",
        "corpus_digest": corpus_digest,
        "certificate_digests": certificate_digests,
        "case_results": {record["id"]: record["observed"] for record in records},
        "metrics": metrics,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "core",
        "result": normalized["result"],
        "generated_at": _utc_now(),
        "repository": _git(repo),
        "environment": _environment(repo),
        "corpus_digest": corpus_digest,
        "cases": records,
        "metrics": metrics,
        "normalized": normalized,
        "_certificate_sources": certificate_sources,
    }


def _inside(base: Path, candidate: Path) -> bool:
    base, candidate = base.resolve(), candidate.resolve()
    return candidate == base or base in candidate.parents


def _load_pack(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    pack_path = path.resolve()
    base = pack_path.parent
    manifest = tomllib.loads(pack_path.read_text(encoding="utf-8"))
    required = {"schema_version", "pack_id", "title", "sources", "research_status", "dependencies", "claims"}
    if set(manifest) != required or manifest.get("schema_version") != 1:
        raise ValueError(f"pack manifest fields must be exactly {sorted(required)}")
    for name in ("pack_id", "title"):
        if not isinstance(manifest[name], str) or not manifest[name].strip():
            raise ValueError(f"{name} must be a non-empty string")
    if manifest["research_status"] not in RESEARCH_STATUSES:
        raise ValueError(f"invalid research_status {manifest['research_status']!r}")
    for name in ("sources", "dependencies"):
        if not isinstance(manifest[name], list) or any(
            not isinstance(item, str) or not item.strip() for item in manifest[name]
        ):
            raise ValueError(f"{name} must be an array of non-empty strings")
    if not manifest["sources"]:
        raise ValueError("sources must not be empty")
    if not isinstance(manifest["claims"], list) or not manifest["claims"]:
        raise ValueError("pack requires at least one [[claims]] entry")
    inputs: dict[str, str] = {pack_path.name: hash_file(pack_path)}
    claims: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for claim in manifest["claims"]:
        allowed = {"id", "path", "expected_proof_status", "alignment_attestation"}
        if not isinstance(claim, dict) or not set(claim).issubset(allowed) or not {"id", "path", "expected_proof_status"}.issubset(claim):
            raise ValueError("each claim requires id, path, expected_proof_status, and optional alignment_attestation")
        for name in ("id", "path", "expected_proof_status"):
            if not isinstance(claim[name], str) or not claim[name].strip():
                raise ValueError(f"each claim {name} must be a non-empty string")
        if "alignment_attestation" in claim and (
            not isinstance(claim["alignment_attestation"], str) or not claim["alignment_attestation"].strip()
        ):
            raise ValueError("alignment_attestation must be a non-empty string when present")
        if claim["id"] in identifiers:
            raise ValueError(f"duplicate pack claim id {claim['id']!r}")
        identifiers.add(claim["id"])
        if claim["expected_proof_status"] not in PROOF_STATUSES:
            raise ValueError(f"{claim['id']}: invalid expected_proof_status")
        source = (base / claim["path"]).resolve()
        if not _inside(base, source) or not source.is_file():
            raise ValueError(f"{claim['id']}: claim path escapes pack or is missing")
        inputs[Path(claim["path"]).as_posix()] = hash_file(source)
        item = dict(claim)
        item["source"] = source
        if claim.get("alignment_attestation"):
            attestation = (base / claim["alignment_attestation"]).resolve()
            if not _inside(base, attestation) or not attestation.is_file():
                raise ValueError(f"{claim['id']}: alignment attestation escapes pack or is missing")
            inputs[Path(claim["alignment_attestation"]).as_posix()] = hash_file(attestation)
            item["attestation"] = attestation
        claims.append(item)
    return manifest, claims, _sha256(_canonical(inputs))


def _attestation(path: Path | None, parsed: dict[str, Any]) -> str:
    if path is None:
        return "ABSENT"
    value = tomllib.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version", "attestation_id", "claim_id", "statement_hash", "formal_target_hash",
        "alignment_hash", "reviewer", "reviewed_at",
    }
    if set(value) != required or value.get("schema_version") != 1:
        return "INVALID"
    identity_fields = (value.get("attestation_id"), value.get("reviewer"), value.get("reviewed_at"))
    if any(not isinstance(item, str) or not item.strip() for item in identity_fields):
        return "INVALID"
    try:
        reviewed_at = datetime.fromisoformat(value["reviewed_at"].replace("Z", "+00:00"))
    except ValueError:
        return "INVALID"
    if reviewed_at.tzinfo is None:
        return "INVALID"
    target = (parsed.get("top_certificate") or {}).get("target")
    formal_hash = hash_json(target) if isinstance(target, str) else None
    pair_hash = hash_json({"statement_hash": parsed["statement_hash"], "formal_target_hash": formal_hash}) if formal_hash else None
    expected = {
        "claim_id": parsed["claim_id"], "statement_hash": parsed["statement_hash"],
        "formal_target_hash": formal_hash, "alignment_hash": pair_hash,
    }
    return "VALID" if all(value.get(key) == expected_value for key, expected_value in expected.items()) else "INVALID"


def evaluate_pack(pack_path: Path, repository: Path | None = None, *, backend: Backend = run_batch) -> dict[str, Any]:
    repo = (repository or _repository()).resolve()
    manifest, claims, corpus_digest = _load_pack(pack_path)
    records: list[dict[str, Any]] = []
    certificate_sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="proofweave-evaluate-pack-") as directory:
        root = Path(directory)
        initialize(root)

        def repository_backend(_root: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
            return backend(repo, specs)

        for claim in claims:
            parsed = parse_input(claim["source"])
            if parsed["claim_id"] != claim["id"]:
                raise ValueError(f"manifest id {claim['id']!r} does not match claim_id {parsed['claim_id']!r}")
            # Deliberately never pass confirm_alignment=True. Human alignment is
            # an independently validated, hash-bound pack input.
            result = run_proof(claim["source"], root=root, confirm_alignment=False, runner=repository_backend)
            alignment = _attestation(claim.get("attestation"), parsed)
            source_path = Path(result["artifact_directory"], "certificate.lean")
            source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
            if source:
                certificate_sources[f"{claim['id']}.lean"] = source
            observed = result["proof_status"]
            records.append({
                "id": claim["id"],
                "expected_proof_status": claim["expected_proof_status"],
                "observed_proof_status": observed,
                "runtime_alignment": result["alignment"],
                "human_alignment_attestation": alignment,
                "passed": observed == claim["expected_proof_status"],
                "certificate_digest": result["certificate"]["cache_key"] if observed == "CERTIFIED" else None,
                "dependency_closure_ready": result["coverage"]["dependencies_ready"],
            })
    prerequisites_observed = all(
        record["observed_proof_status"] == "CERTIFIED"
        and record["human_alignment_attestation"] == "VALID"
        and record["dependency_closure_ready"]
        for record in records
    )
    # The initial pack format can bind formal targets and human alignment, but
    # it intentionally has no authority to encode novelty review, an
    # independent human review, or a retained cold-start replay. Therefore a
    # pack that claims VERIFIED is rejected even when the observable formal
    # prerequisites pass. Later schema versions may add those evidence types.
    verified_gate = manifest["research_status"] != "VERIFIED"
    passed = all(record["passed"] for record in records) and verified_gate
    certificate_digests = {
        name: _sha256(source.encode("utf-8")) for name, source in certificate_sources.items()
    }
    metrics = {
        "claim_total": len(records),
        "claim_expected_status_matched": sum(record["passed"] for record in records),
        "certified": sum(record["observed_proof_status"] == "CERTIFIED" for record in records),
        "valid_alignment_attestations": sum(record["human_alignment_attestation"] == "VALID" for record in records),
        "verified_gate_passed": verified_gate,
        "verified_prerequisites_observed": prerequisites_observed,
        "verified_gate_reason": (
            None if manifest["research_status"] != "VERIFIED"
            else "VERIFIED is unsupported until cold-start replay, literature novelty recheck, and independent human review are version-bound"
        ),
    }
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "mode": "pack",
        "pack_id": manifest["pack_id"],
        "research_status": manifest["research_status"],
        "result": "PASS" if passed else "FAIL",
        "corpus_digest": corpus_digest,
        "certificate_digests": certificate_digests,
        "claim_results": {
            record["id"]: {
                "proof_status": record["observed_proof_status"],
                "alignment_attestation": record["human_alignment_attestation"],
                "certificate_digest": record["certificate_digest"],
            }
            for record in records
        },
        "metrics": metrics,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "pack",
        "pack_id": manifest["pack_id"],
        "title": manifest["title"],
        "sources": manifest["sources"],
        "research_status": manifest["research_status"],
        "dependencies": manifest["dependencies"],
        "result": normalized["result"],
        "generated_at": _utc_now(),
        "repository": _git(repo),
        "environment": _environment(repo),
        "corpus_digest": corpus_digest,
        "claims": records,
        "metrics": metrics,
        "normalized": normalized,
        "_certificate_sources": certificate_sources,
    }


def _summary(report: dict[str, Any]) -> str:
    lines = [
        f"# ProofWeave {report['mode'].title()} Evaluation",
        "",
        f"- Result: **{report['result']}**",
        f"- Corpus digest: `{report['corpus_digest']}`",
        f"- Commit: `{report['repository']['commit'] or 'UNKNOWN'}`",
        f"- Tracked tree dirty: `{str(report['repository']['dirty']).lower()}`",
        f"- Lean available: `{str(report['environment']['lean_available']).lower()}`",
        "",
        "Finite-corpus results are `COMPUTATIONAL`, not a global soundness proof. A Lean certificate proves only its formal target. Natural-language alignment requires a hash-bound human attestation. Failure to find a prior solution is not proof of novelty.",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(f"- {key}: `{json.dumps(value, ensure_ascii=False, sort_keys=True)}`" for key, value in report["metrics"].items())
    return "\n".join(lines) + "\n"


def _environment_text(environment: dict[str, Any]) -> str:
    lines = [f"{key}={json.dumps(value, ensure_ascii=False, sort_keys=True)}" for key, value in sorted(environment.items())]
    return "\n".join(lines) + "\n"


def write_bundle(report: dict[str, Any], output: Path) -> Path:
    directory = output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    certificates = directory / "certificates"
    if certificates.exists():
        shutil.rmtree(certificates)
    certificates.mkdir()
    sources = report.pop("_certificate_sources", {})
    for name, source in sorted(sources.items()):
        if source:
            (certificates / name).write_text(source, encoding="utf-8", newline="\n")
    (directory / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (directory / "summary.md").write_text(_summary(report), encoding="utf-8", newline="\n")
    (directory / "environment.txt").write_text(_environment_text(report["environment"]), encoding="utf-8", newline="\n")
    checksum = directory / "SHA256SUMS"
    entries = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file() and item != checksum):
        entries.append(f"{hash_file(path)}  {path.relative_to(directory).as_posix()}")
    checksum.write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")
    return directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    core = commands.add_parser("core", help="evaluate the fixed 42-case Core corpus")
    core.add_argument("--output", required=True, type=Path)
    pack = commands.add_parser("pack", help="evaluate a theorem evidence pack")
    pack.add_argument("pack", type=Path)
    pack.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = evaluate_core() if args.mode == "core" else evaluate_pack(args.pack)
        directory = write_bundle(report, args.output)
    except (CoreError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(json.dumps({"result": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"result": report["result"], "output": str(directory)}, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
