from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ALIGNMENTS = {"UNCONFIRMED", "CONFIRMED", "STALE"}
PROOF_STATUSES = {"UNVERIFIED", "PARTIAL", "CERTIFIED", "FAILED"}
LIFECYCLES = {"ACTIVE", "SUPERSEDED", "REVOKED"}
NODE_ROLES = {"semantic", "bridge", "computational", "alias"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SECTION_RE = re.compile(r"(?m)^##\s+(Statement|Proof|Certificate)\s*$")
NODE_RE = re.compile(
    r"(?m)^###\s+([A-Za-z0-9][A-Za-z0-9._-]{0,63})\s+"
    r"\[(semantic|bridge|computational|alias)\]\s*$"
)
LEAN_FENCE_RE = re.compile(
    r"```proofweave-lean\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE
)


class CoreError(Exception):
    """A safe, user-facing Core validation error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_json(value: Any) -> str:
    return hash_bytes(canonical_json(value).encode("utf-8"))


def hash_file(path: Path) -> str:
    return hash_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoreError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CoreError(f"JSON object required: {path}")
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def find_root(start: Path | str | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "workspace" / "claims").is_dir() and (candidate / "artifacts").is_dir():
            return candidate
    raise CoreError("Not a ProofWeave project; run `proofweave init` first")


def _string_list(meta: dict[str, Any], name: str, *, nonempty: bool = False) -> list[str]:
    value = meta.get(name)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CoreError(f"Front matter `{name}` must be an array of strings")
    if nonempty and not value:
        raise CoreError(f"Front matter `{name}` must be explicit; use [\"none\"] when appropriate")
    if len(set(value)) != len(value):
        raise CoreError(f"Front matter `{name}` contains duplicates")
    return value


def _certificate_from(text: str) -> tuple[dict[str, Any] | None, str]:
    matches = list(LEAN_FENCE_RE.finditer(text))
    if len(matches) > 1:
        raise CoreError("At most one proofweave-lean block is allowed per proof node/section")
    if not matches:
        return None, text.strip()
    try:
        certificate = tomllib.loads(matches[0].group(1))
    except tomllib.TOMLDecodeError as exc:
        raise CoreError(f"Invalid proofweave-lean TOML: {exc}") from exc
    allowed = {"target", "tactic", "exact"}
    unknown = sorted(set(certificate) - allowed)
    if unknown:
        raise CoreError(f"Unknown certificate fields: {', '.join(unknown)}")
    cleaned = text[: matches[0].start()] + text[matches[0].end() :]
    return certificate, cleaned.strip()


def _sections(body: str) -> dict[str, tuple[str, int]]:
    matches = list(SECTION_RE.finditer(body))
    values: dict[str, tuple[str, int]] = {}
    for index, match in enumerate(matches):
        name = match.group(1).lower()
        if name in values:
            raise CoreError(f"Duplicate ## {match.group(1)} section")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[match.end() : end].strip("\n")
        line = body.count("\n", 0, match.end()) + 2
        values[name] = (content, line)
    return values


def _node(chunk: str, node_id: str, role: str, line: int, previous: str | None) -> dict[str, Any]:
    depends_match = re.search(r"(?m)^Depends:\s*(.*?)\s*$", chunk)
    alias_match = re.search(r"(?m)^Alias:\s*([A-Za-z0-9._-]+)\s*$", chunk)
    if depends_match:
        depends = [item.strip() for item in depends_match.group(1).split(",") if item.strip()]
        chunk = chunk[: depends_match.start()] + chunk[depends_match.end() :]
    else:
        depends = [previous] if previous else []
    if alias_match:
        alias_of = alias_match.group(1)
        chunk = chunk[: alias_match.start()] + chunk[alias_match.end() :]
    else:
        alias_of = None
    certificate, text = _certificate_from(chunk)
    if role == "alias" and not alias_of:
        raise CoreError(f"Alias node {node_id!r} requires `Alias: NODE_ID`")
    if role != "alias" and alias_of:
        raise CoreError(f"Only alias nodes may contain `Alias:` ({node_id})")
    if not text and role != "alias":
        raise CoreError(f"Proof node {node_id!r} has no text")
    return {
        "id": node_id,
        "role": role,
        "text": text,
        "depends_on": depends,
        "alias_of": alias_of,
        "source_span": {"start_line": line, "end_line": line + chunk.count("\n")},
        "certificate": certificate,
    }


def _proof_nodes(proof: str, start_line: int) -> list[dict[str, Any]]:
    matches = list(NODE_RE.finditer(proof))
    nodes: list[dict[str, Any]] = []
    previous: str | None = None
    if matches:
        prelude = proof[: matches[0].start()].strip()
        if prelude:
            nodes.append(_node(prelude, "preamble", "semantic", start_line, None))
            previous = "preamble"
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(proof)
            chunk = proof[match.end() : end].strip("\n")
            line = start_line + proof.count("\n", 0, match.end())
            nodes.append(_node(chunk, match.group(1), match.group(2), line, previous))
            previous = match.group(1)
    else:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", proof) if part.strip()]
        for index, paragraph in enumerate(paragraphs, 1):
            node_id = f"step-{index}"
            line = start_line + proof.find(paragraph)
            nodes.append(_node(paragraph, node_id, "semantic", line, previous))
            previous = node_id
    if not nodes:
        raise CoreError("## Proof must contain at least one proof step")
    return nodes


def cycle_path(graph: dict[str, Iterable[str]]) -> list[str] | None:
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

    for key in graph:
        if state.get(key, 0) == 0:
            found = visit(key)
            if found:
                return found
    return None


def parse_input(path: Path | str) -> dict[str, Any]:
    source_path = Path(path).resolve()
    raw = source_path.read_bytes()
    try:
        text = raw.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise CoreError("Input must be UTF-8") from exc
    front = re.match(r"\A\+\+\+\n(.*?)\n\+\+\+\n?", text, re.DOTALL)
    if not front:
        raise CoreError("Input must begin with +++ TOML front matter +++")
    try:
        meta = tomllib.loads(front.group(1))
    except tomllib.TOMLDecodeError as exc:
        raise CoreError(f"Invalid front matter TOML: {exc}") from exc
    allowed = {"claim_id", "title", "assumptions", "quantifiers", "dependencies"}
    unknown = sorted(set(meta) - allowed)
    if unknown:
        raise CoreError(f"Unknown front matter fields: {', '.join(unknown)}")
    claim_id, title = meta.get("claim_id"), meta.get("title")
    if not isinstance(claim_id, str) or not ID_RE.fullmatch(claim_id):
        raise CoreError("claim_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    if not isinstance(title, str) or not title.strip():
        raise CoreError("title must be a non-empty string")
    assumptions = _string_list(meta, "assumptions", nonempty=True)
    quantifiers = _string_list(meta, "quantifiers")
    dependencies = _string_list(meta, "dependencies")
    if claim_id in dependencies:
        raise CoreError("A claim cannot depend on itself")
    sections = _sections(text[front.end() :])
    if "statement" not in sections or "proof" not in sections:
        raise CoreError("Input requires ## Statement and ## Proof sections")
    statement = sections["statement"][0].strip()
    if not statement:
        raise CoreError("## Statement must not be empty")
    top_certificate = None
    if "certificate" in sections:
        top_certificate, remainder = _certificate_from(sections["certificate"][0])
        if remainder:
            raise CoreError("## Certificate may contain only one proofweave-lean block")
        if not top_certificate:
            raise CoreError("## Certificate requires a proofweave-lean block")
    nodes = _proof_nodes(sections["proof"][0], sections["proof"][1])
    ids = {node["id"] for node in nodes}
    if len(ids) != len(nodes):
        raise CoreError("Proof node IDs must be unique")
    for node in nodes:
        refs = [*node["depends_on"], *([node["alias_of"]] if node["alias_of"] else [])]
        missing = sorted(set(refs) - ids)
        if missing:
            raise CoreError(f"Node {node['id']} references unknown nodes: {', '.join(missing)}")
        if node["id"] in refs:
            raise CoreError(f"Node {node['id']} cannot reference itself")
    graph = {node["id"]: node["depends_on"] for node in nodes}
    cycle = cycle_path(graph)
    if cycle:
        raise CoreError(f"Proof dependency cycle: {' -> '.join(cycle)}")
    statement_hash = hash_json({"statement": statement, "quantifiers": quantifiers})
    revision_id = hash_json(
        {"statement_hash": statement_hash, "assumptions": assumptions, "dependencies": dependencies}
    )
    return {
        "claim_id": claim_id,
        "title": title.strip(),
        "statement": statement,
        "assumptions": assumptions,
        "quantifiers": quantifiers,
        "dependencies": dependencies,
        "statement_hash": statement_hash,
        "revision_id": revision_id,
        "source_path": str(source_path),
        "source_hash": hash_bytes(raw),
        "source_text": text,
        "top_certificate": top_certificate,
        "proof_ir": {"schema_version": 2, "claim_id": claim_id, "statement_hash": statement_hash, "nodes": nodes},
    }


def verify_artifacts(root: Path, run: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = root.resolve()
    artifacts = run.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return ["artifacts must be an object"]
    for relative, expected in artifacts.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            errors.append("artifact paths and digests must be strings")
            continue
        path = (project / relative).resolve()
        if path != project and project not in path.parents:
            errors.append(f"artifact escapes project root: {relative}")
            continue
        if not path.is_file():
            errors.append(f"missing artifact: {relative}")
        elif hash_file(path) != expected:
            errors.append(f"artifact hash mismatch: {relative}")
    return errors
