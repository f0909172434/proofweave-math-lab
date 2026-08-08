"""One-time v1 fact_graph.jsonl to Core v2 migration. Never imported by runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMAL_KINDS = {"theorem", "lemma", "proposition", "corollary"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def cycle(graph: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    trail: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        trail.append(node)
        for dependency in graph.get(node, []):
            if state.get(dependency) == 1:
                index = trail.index(dependency)
                return trail[index:] + [dependency]
            if state.get(dependency, 0) == 0:
                found = visit(dependency)
                if found:
                    return found
        trail.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None


def markdown(record: dict[str, Any]) -> str:
    claim_id = record.get("fact_id", record.get("id"))
    assumptions = record.get("assumptions") or ["none recorded in v1"]
    quantifiers = record.get("quantifiers") or []
    dependencies = record.get("dependencies") or []
    proof = record.get("proof") or "No proof was supplied in v1."
    return (
        "+++\n"
        f"claim_id = {json.dumps(claim_id, ensure_ascii=False)}\n"
        f"title = {json.dumps(record.get('title') or claim_id, ensure_ascii=False)}\n"
        f"assumptions = {json.dumps(assumptions, ensure_ascii=False)}\n"
        f"quantifiers = {json.dumps(quantifiers, ensure_ascii=False)}\n"
        f"dependencies = {json.dumps(dependencies, ensure_ascii=False)}\n"
        "+++\n\n"
        f"## Statement\n\n{record.get('statement', '').strip()}\n\n"
        f"## Proof\n\n{str(proof).strip()}\n"
    )


def migrate(source: Path | str, root: Path | str) -> dict[str, Any]:
    source_path, project = Path(source).resolve(), Path(root).resolve()
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL line {number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Line {number} is not an object")
        rows.append(value)
    identifiers = [row.get("fact_id", row.get("id")) for row in rows]
    if any(not isinstance(item, str) or not item for item in identifiers):
        raise ValueError("Every v1 record requires fact_id or id")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate v1 fact IDs")
    all_ids = set(identifiers)
    for row in rows:
        missing = set(row.get("dependencies") or []) - all_ids
        if missing:
            raise ValueError(f"{row.get('fact_id', row.get('id'))}: missing dependencies {sorted(missing)}")
    formal = {
        row.get("fact_id", row.get("id")): row
        for row in rows
        if row.get("kind") in FORMAL_KINDS
    }
    invalid = {
        identifier
        for identifier, row in formal.items()
        if set(row.get("dependencies") or []) - set(formal)
    }
    changed = True
    while changed:
        changed = False
        for identifier, row in formal.items():
            if identifier not in invalid and set(row.get("dependencies") or []) & invalid:
                invalid.add(identifier)
                changed = True
    graph = {
        identifier: list(row.get("dependencies") or [])
        for identifier, row in formal.items()
        if identifier not in invalid
    }
    found_cycle = cycle(graph)
    if found_cycle:
        raise ValueError(f"v1 dependency cycle: {' -> '.join(found_cycle)}")
    destination = project / "workspace" / "claims"
    existing = [path for path in destination.glob("*") if path.name != ".gitkeep"] if destination.exists() else []
    if existing:
        raise ValueError("workspace/claims must be empty before migration")
    migrated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="proofweave-migrate-", dir=project) as temporary:
        staging = Path(temporary)
        for row in rows:
            identifier = row.get("fact_id", row.get("id"))
            if identifier not in formal or identifier in invalid:
                reason = "non-formal evidence" if identifier not in formal else "depends on non-formal evidence"
                skipped.append({"fact_id": identifier, "reason": reason})
                continue
            text = markdown(row)
            md_name = f"{identifier}.md"
            (staging / md_name).write_text(text, encoding="utf-8", newline="\n")
            assumptions = row.get("assumptions") or ["none recorded in v1"]
            quantifiers = row.get("quantifiers") or []
            dependencies = row.get("dependencies") or []
            statement = str(row.get("statement", "")).strip()
            statement_hash = digest({"statement": statement, "quantifiers": quantifiers})
            revision_id = digest(
                {"statement_hash": statement_hash, "assumptions": assumptions, "dependencies": dependencies}
            )
            old_status = row.get("status", row.get("verification_status", "UNKNOWN"))
            lifecycle = old_status if old_status in {"REVOKED", "SUPERSEDED"} else "ACTIVE"
            record = {
                "schema_version": 2,
                "claim_id": identifier,
                "revision_id": revision_id,
                "title": row.get("title") or identifier,
                "statement": statement,
                "assumptions": assumptions,
                "quantifiers": quantifiers,
                "dependencies": dependencies,
                "statement_hash": statement_hash,
                "source_path": str((destination / md_name).resolve()),
                "source_hash": digest(text.encode("utf-8")),
                "formal_target_hash": None,
                "alignment_hash": None,
                "alignment": "UNCONFIRMED",
                "proof_status": "UNVERIFIED",
                "lifecycle": lifecycle,
                "latest_run_id": None,
                "certificate_digest": None,
                "updated_at": now(),
            }
            json_name = f"{identifier}--{revision_id[:16]}.json"
            (staging / json_name).write_text(
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            migrated.append(
                {"fact_id": identifier, "v1_status": old_status, "proof_status": "UNVERIFIED", "lifecycle": lifecycle}
            )
        destination.mkdir(parents=True, exist_ok=True)
        for path in staging.iterdir():
            os.replace(path, destination / path.name)
    report = {
        "source": str(source_path),
        "migrated": migrated,
        "skipped": skipped,
        "v1_verified_mapped_to_certified": False,
        "created_at": now(),
    }
    report_path = project / "artifacts" / "migration_v1_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fact_graph")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        report = migrate(args.fact_graph, args.root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"result": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
