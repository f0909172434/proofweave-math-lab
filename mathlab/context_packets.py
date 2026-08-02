from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .errors import ValidationError
from .io import find_project_root
from .schemas import load_schema, validate_instance


SCHEMA_VERSION = "1.0"
COMPILER_VERSION = "context-packet-v1"
TOKEN_BUDGETS = {
    "fast": 8_000,
    "standard": 16_000,
    "deep": 24_000,
    "max": 32_000,
}
CHUNKABLE_LONG_CONTENT_KINDS = {"summary", "literature", "scientific_writing"}
UNSPLITTABLE_LONG_CONTENT_KINDS = {"mathematical_proof", "dependency_chain"}

_POLICY_PATHS = (
    "AGENTS.md",
    "docs/mathematical_quality_standard.md",
    "docs/agent_contracts.md",
    "docs/model_routing_guide.md",
)
_FORBIDDEN_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "hidden_chain_of_thought",
    "hidden_reasoning",
    "scratchpad",
    "chat",
    "chat_history",
    "conversation",
    "conversation_history",
    "messages",
}
_SECRET_KEY_RE = re.compile(
    r"(?i)(?:^|[_-])(?:api[_-]?key|api[_-]?token|access[_-]?token|auth[_-]?token|"
    r"refresh[_-]?token|id[_-]?token|token|secret|password|passwd|cookie|authorization|"
    r"bearer|credential|credentials|private[_-]?key)$"
)
_SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?:api[_-]?key|api[_-]?token|access[_-]?token|auth[_-]?token|refresh[_-]?token|"
    r"secret|password|passwd|authorization|bearer|private[_-]?key)\s*[:=]\s*[^\s,;]+)"
)
_FORBIDDEN_FILE_NAMES = {
    "status.md",
    ".env",
    "credentials.json",
    "secrets.json",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _digest_bytes(_canonical_bytes(value))


def estimate_tokens(value: Any) -> int:
    """Estimate tokens as ceil(canonical UTF-8 bytes / 4)."""

    return math.ceil(len(_canonical_bytes(value)) / 4)


def _text_tokens(value: str) -> int:
    return math.ceil(len(value.encode("utf-8")) / 4)


def chunk_long_content(
    content: str,
    *,
    kind: str,
    threshold_tokens: int = 32_000,
    max_chunk_tokens: int = 12_000,
    overlap_fraction: float = 0.10,
) -> list[dict[str, Any]]:
    """Split eligible prose on semantic boundaries and content-address chunks.

    Mathematical proofs and dependency chains fail closed instead of being
    sliced.  Oversized indivisible sentences also require manual context review.
    """

    if not isinstance(content, str):
        raise ValidationError("long content must be UTF-8 text")
    if kind in UNSPLITTABLE_LONG_CONTENT_KINDS:
        if _text_tokens(content) > threshold_tokens:
            raise ValidationError(
                "mathematical proofs and dependency chains require a smaller proposition or manual long-context handoff"
            )
    elif kind not in CHUNKABLE_LONG_CONTENT_KINDS:
        raise ValidationError(f"Unknown long-content kind: {kind!r}")
    if not 0 <= overlap_fraction < 0.5:
        raise ValidationError("overlap_fraction must be in [0, 0.5)")
    if max_chunk_tokens < 1 or threshold_tokens < 1:
        raise ValidationError("token thresholds must be positive")

    if _text_tokens(content) <= threshold_tokens:
        return [
            {
                "index": 1,
                "count": 1,
                "kind": kind,
                "estimated_tokens": _text_tokens(content),
                "overlap_tokens": 0,
                "digest": _digest_bytes(content.encode("utf-8")),
                "content": content,
            }
        ]

    paragraph_units = [unit.strip() for unit in re.split(r"\n\s*\n", content) if unit.strip()]
    units: list[str] = []
    core_limit = max(1, math.floor(max_chunk_tokens * (1 - overlap_fraction)))
    for paragraph in paragraph_units:
        if _text_tokens(paragraph) <= core_limit:
            units.append(paragraph)
            continue
        sentences = [
            unit.strip()
            for unit in re.split(r"(?<=[.!?。！？])\s+|(?<=。)|(?<=！)|(?<=？)", paragraph)
            if unit.strip()
        ]
        if not sentences or any(_text_tokens(sentence) > core_limit for sentence in sentences):
            raise ValidationError(
                "an indivisible semantic unit exceeds the 12k chunk policy; manual context review is required"
            )
        units.extend(sentences)

    cores: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for unit in units:
        unit_tokens = _text_tokens(unit + "\n\n")
        if current and current_tokens + unit_tokens > core_limit:
            cores.append(current)
            current = []
            current_tokens = 0
        current.append(unit)
        current_tokens += unit_tokens
    if current:
        cores.append(current)

    overlap_limit = math.floor(max_chunk_tokens * overlap_fraction)
    rendered: list[tuple[str, int]] = []
    previous_core: list[str] = []
    for core in cores:
        overlap: list[str] = []
        overlap_tokens = 0
        for unit in reversed(previous_core):
            candidate_tokens = _text_tokens(unit + "\n\n")
            if overlap_tokens + candidate_tokens > overlap_limit:
                break
            overlap.insert(0, unit)
            overlap_tokens += candidate_tokens
        chunk = "\n\n".join([*overlap, *core])
        if _text_tokens(chunk) > max_chunk_tokens:
            raise ValidationError("semantic chunk exceeds max_chunk_tokens")
        rendered.append((chunk, overlap_tokens))
        previous_core = core

    count = len(rendered)
    return [
        {
            "index": index,
            "count": count,
            "kind": kind,
            "estimated_tokens": _text_tokens(chunk),
            "overlap_tokens": overlap_tokens,
            "digest": _digest_bytes(chunk.encode("utf-8")),
            "content": chunk,
        }
        for index, (chunk, overlap_tokens) in enumerate(rendered, 1)
    ]


def _safe_label(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _confine_path(path: Path, root: Path, kind: str) -> Path:
    """Resolve a context input and reject reads outside the project root."""

    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{kind} path must stay inside the project root: {path}") from exc
    return resolved


def _looks_forbidden_path(path: Path) -> str | None:
    lowered = [part.lower() for part in path.parts]
    filename = path.name.lower()
    if path.name.lower() in _FORBIDDEN_FILE_NAMES:
        return "STATUS/secrets files are excluded"
    if (
        any(part in {"chat", "chats", "conversation", "conversations"} for part in lowered)
        or "chat_history" in filename
        or "conversation_history" in filename
    ):
        return "chat or conversation history is excluded"
    if any("chain-of-thought" in part or "chain_of_thought" in part for part in lowered):
        return "chain-of-thought material is excluded"
    return None


def _scrub(value: Any, location: str, exclusions: list[dict[str, str]]) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            child_location = f"{location}.{key}"
            if lowered in _FORBIDDEN_KEYS:
                exclusions.append(
                    {"input": child_location, "reason": "chat/chain-of-thought field excluded"}
                )
                continue
            if _SECRET_KEY_RE.search(key):
                result[key] = "[REDACTED]"
                exclusions.append(
                    {"input": child_location, "reason": "secret-bearing field redacted"}
                )
                continue
            result[key] = _scrub(item, child_location, exclusions)
        return result
    if isinstance(value, list):
        return [_scrub(item, f"{location}[{index}]", exclusions) for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return [_scrub(item, f"{location}[{index}]", exclusions) for index, item in enumerate(value)]
    if isinstance(value, str) and _SECRET_VALUE_RE.search(value):
        exclusions.append({"input": location, "reason": "secret-like value redacted"})
        return _SECRET_VALUE_RE.sub("[REDACTED]", value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _read_path(path: Path) -> tuple[bytes, Any, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"Cannot read context input {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"Context input is not UTF-8: {path}") from exc
    if path.suffix.lower() == ".json":
        try:
            return raw, json.loads(text), "json"
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid task/source JSON {path}: {exc}") from exc
    return raw, text, "markdown" if path.suffix.lower() in {".md", ".markdown"} else "text"


def _resolve_text_input(
    value: Any,
    *,
    kind: str,
    root: Path,
    exclusions: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    path: Path | None = None
    if isinstance(value, Path):
        path = value if value.is_absolute() else root / value
    elif isinstance(value, str):
        candidate = Path(value)
        rooted = candidate if candidate.is_absolute() else root / candidate
        if rooted.is_file():
            path = rooted
        elif kind == "role" and re.fullmatch(r"[A-Za-z0-9_-]+", value):
            role_path = root / "agents" / f"{value}.md"
            if role_path.is_file():
                path = role_path

    if path is not None:
        path = _confine_path(path, root, kind)
        forbidden = _looks_forbidden_path(path)
        raw, parsed, format_name = _read_path(path)
        label = _safe_label(path, root)
        if forbidden:
            exclusions.append({"input": label, "reason": forbidden})
            parsed = "[EXCLUDED]"
        payload = _scrub(parsed, kind, exclusions)
        descriptor = {
            "kind": kind,
            "label": label,
            "format": format_name,
            "raw_digest": _digest_bytes(raw),
        }
        return {"format": format_name, "source": label, "payload": payload}, descriptor

    if isinstance(value, Mapping):
        raw = _canonical_bytes(value)
        payload = _scrub(deepcopy(dict(value)), kind, exclusions)
        return (
            {"format": "json", "source": "inline", "payload": payload},
            {
                "kind": kind,
                "label": "inline",
                "format": "json",
                "raw_digest": _digest_bytes(raw),
            },
        )
    if isinstance(value, str):
        raw = value.encode("utf-8")
        stripped = value.lstrip()
        if stripped.startswith("{"):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Invalid inline {kind} JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValidationError(f"Inline {kind} JSON must be an object")
            format_name = "json"
        else:
            parsed = value
            format_name = "markdown"
        return (
            {
                "format": format_name,
                "source": "inline",
                "payload": _scrub(parsed, kind, exclusions),
            },
            {
                "kind": kind,
                "label": "inline",
                "format": format_name,
                "raw_digest": _digest_bytes(raw),
            },
        )
    raise ValidationError(f"{kind} must be a mapping, UTF-8 path, JSON string, or Markdown string")


def _load_fact_graph(value: Any, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if value is None:
        value = root / "state" / "fact_graph.jsonl"
    if isinstance(value, (str, Path)):
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        path = _confine_path(path, root, "fact_graph")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValidationError(f"Cannot read fact graph {path}: {exc}") from exc
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Invalid fact graph JSONL at line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValidationError(f"Fact graph record at line {line_number} is not an object")
            records.append(record)
        descriptor = {
            "kind": "fact_graph",
            "label": _safe_label(path, root),
            "format": "jsonl",
            "raw_digest": _digest_bytes(raw),
        }
        return records, descriptor
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        records = [deepcopy(dict(record)) for record in value]
        raw = _canonical_bytes(records)
        return records, {
            "kind": "fact_graph",
            "label": "inline",
            "format": "json",
            "raw_digest": _digest_bytes(raw),
        }
    raise ValidationError("fact_graph must be a JSONL path or iterable of fact mappings")


def _infer_root(fact_graph: Any, project_root: Path | str | None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()
    if isinstance(fact_graph, (Path, str)):
        path = Path(fact_graph)
        if path.name == "fact_graph.jsonl" and path.parent.name == "state":
            return path.resolve().parent.parent
    return find_project_root()


def _infer_target_fact_id(task_payload: Any) -> str | None:
    if not isinstance(task_payload, Mapping):
        return None
    for key in ("target_fact_id", "fact_id", "target_claim_id", "claim_id"):
        value = task_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    target = task_payload.get("target_fact")
    if isinstance(target, str) and target.strip():
        return target.strip()
    if isinstance(target, Mapping):
        value = target.get("fact_id", target.get("id"))
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _fact_status(record: Mapping[str, Any]) -> str:
    status = record.get("status")
    verification_status = record.get("verification_status")
    if status is not None and verification_status is not None and status != verification_status:
        return "STATUS_MISMATCH"
    return str(status if status is not None else verification_status or "UNKNOWN")


def _project_fact(record: Mapping[str, Any], *, target: bool) -> dict[str, Any]:
    keys = [
        "fact_id",
        "title",
        "kind",
        "statement",
        "normalized_statement",
        "assumptions",
        "quantifiers",
        "mathematical_domain",
        "dependencies",
        "source_dependencies",
    ]
    if target:
        keys.append("proof")
    projected = {key: deepcopy(record.get(key)) for key in keys}
    projected["status"] = _fact_status(record)
    return projected


def _safe_project_fact(
    record: Mapping[str, Any],
    *,
    target: bool,
    location: str,
    exclusions: list[dict[str, str]],
) -> dict[str, Any]:
    projected = _scrub(_project_fact(record, target=target), location, exclusions)
    projected["digest"] = _digest(projected)
    return projected


def _dependency_closure(
    target_id: str,
    facts: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    verified: set[str] = set()
    invalid: set[str] = set()
    missing: set[str] = set()
    active: set[str] = set()
    visited: set[str] = set()

    def visit(fact_id: str) -> None:
        if fact_id in active:
            invalid.add(fact_id)
            return
        if fact_id in visited:
            return
        visited.add(fact_id)
        record = facts.get(fact_id)
        if record is None:
            missing.add(fact_id)
            return
        active.add(fact_id)
        for dependency in record.get("dependencies", []):
            if isinstance(dependency, str):
                visit(dependency)
        active.remove(fact_id)
        if fact_id != target_id:
            if _fact_status(record) == "VERIFIED":
                verified.add(fact_id)
            else:
                invalid.add(fact_id)

    visit(target_id)
    return sorted(verified), sorted(invalid), sorted(missing)


def _normalize_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, Path, Mapping)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    raise ValidationError("artifacts and sources must be a value or sequence")


def _task_items(task_payload: Any, keys: Sequence[str]) -> list[Any]:
    if not isinstance(task_payload, Mapping):
        return []
    found: list[Any] = []
    for key in keys:
        if key in task_payload:
            found.extend(_normalize_items(task_payload[key]))
    return found


def _materialize_items(
    values: Sequence[Any],
    *,
    kind: str,
    root: Path,
    exclusions: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    descriptors: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        label = f"inline-{index + 1}"
        path: Path | None = None
        if isinstance(value, Path):
            path = value if value.is_absolute() else root / value
        elif isinstance(value, str):
            candidate = Path(value)
            rooted = candidate if candidate.is_absolute() else root / candidate
            try:
                if rooted.is_file():
                    path = rooted
            except OSError:
                # Inline content can be far longer than a platform's path limit.
                # Older Python versions propagate that filesystem error from
                # Path.is_file(), while newer versions return False.
                path = None
        if path is not None:
            path = _confine_path(path, root, kind)
            raw, parsed, format_name = _read_path(path)
            label = _safe_label(path, root)
            descriptor = {
                "kind": kind,
                "label": label,
                "format": format_name,
                "raw_digest": _digest_bytes(raw),
            }
            forbidden = _looks_forbidden_path(path)
            if forbidden:
                exclusions.append({"input": label, "reason": forbidden})
                descriptors.append(descriptor)
                continue
            content = _scrub(parsed, f"{kind}.{label}", exclusions)
        else:
            raw = _canonical_bytes(value) if not isinstance(value, str) else value.encode("utf-8")
            format_name = "json" if isinstance(value, Mapping) else "text"
            descriptor = {
                "kind": kind,
                "label": label,
                "format": format_name,
                "raw_digest": _digest_bytes(raw),
            }
            content = _scrub(deepcopy(value), f"{kind}.{label}", exclusions)
        output.append(
            {
                "label": label,
                "format": format_name,
                "content": content,
                "digest": _digest(content),
            }
        )
        descriptors.append(descriptor)
    return output, descriptors


def _load_policy(
    root: Path,
    policy_files: Sequence[Path | str] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = list(policy_files) if policy_files is not None else list(_POLICY_PATHS)
    documents: list[dict[str, str]] = []
    descriptors: list[dict[str, Any]] = []
    for item in paths:
        path = Path(item)
        if not path.is_absolute():
            path = root / path
        path = _confine_path(path, root, "policy")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValidationError(f"Cannot read policy input {path}: {exc}") from exc
        label = _safe_label(path, root)
        raw_digest = _digest_bytes(raw)
        documents.append({"path": label, "digest": raw_digest})
        descriptors.append(
            {"kind": "policy", "label": label, "format": "text", "raw_digest": raw_digest}
        )
    policy = {"documents": documents, "digest": _digest(documents)}
    return policy, descriptors


def _cache_key(input_manifest: Sequence[Mapping[str, Any]], options: Mapping[str, Any]) -> str:
    return _digest({"compiler": COMPILER_VERSION, "inputs": list(input_manifest), "options": options})


def _packet_digest(packet: Mapping[str, Any]) -> str:
    content = {key: value for key, value in packet.items() if key not in {"packet_digest", "packet_id"}}
    return _digest(content)


def _set_budget_metrics(packet: dict[str, Any], *, force_review: bool = False) -> None:
    budget = packet["budget"]
    for _ in range(10):
        byte_count = len(_canonical_bytes(packet))
        token_count = math.ceil(byte_count / 4)
        status = (
            "READY"
            if token_count <= budget["limit_tokens"] and not force_review
            else "NEEDS_CONTEXT_REVIEW"
        )
        current = (budget["utf8_bytes"], budget["estimated_tokens"], packet["status"])
        replacement = (byte_count, token_count, status)
        budget["utf8_bytes"], budget["estimated_tokens"], packet["status"] = replacement
        if current == replacement:
            return


def build_context_packet(
    task: Mapping[str, Any] | str | Path,
    role: Mapping[str, Any] | str | Path,
    fact_graph: Iterable[Mapping[str, Any]] | str | Path | None = None,
    *,
    target_fact_id: str | None = None,
    artifacts: Sequence[Any] | Any | None = None,
    sources: Sequence[Any] | Any | None = None,
    policy_files: Sequence[Path | str] | None = None,
    budget: str = "standard",
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, content-addressed, non-truncating context packet.

    The function only reads supplied inputs and returns a value.  Callers may
    persist it under ``build/context-cache/<cache_key>.json`` if desired.
    """

    if budget not in TOKEN_BUDGETS:
        raise ValidationError(f"Unknown context budget {budget!r}; choose {sorted(TOKEN_BUDGETS)}")
    root = _infer_root(fact_graph, project_root)
    exclusions: list[dict[str, str]] = []
    task_record, task_descriptor = _resolve_text_input(
        task, kind="task", root=root, exclusions=exclusions
    )
    role_record, role_descriptor = _resolve_text_input(
        role, kind="role", root=root, exclusions=exclusions
    )
    records, graph_descriptor = _load_fact_graph(fact_graph, root)
    facts: dict[str, Mapping[str, Any]] = {}
    for record in records:
        fact_id = record.get("fact_id", record.get("id"))
        if not isinstance(fact_id, str) or not fact_id:
            raise ValidationError("Every fact graph record needs a non-empty fact_id")
        if fact_id in facts:
            raise ValidationError(f"Duplicate fact_id in context input: {fact_id}")
        facts[fact_id] = record

    target_id = target_fact_id or _infer_target_fact_id(task_record["payload"])
    if not target_id:
        raise ValidationError("target_fact_id is required or must be declared in task JSON")
    if target_id not in facts:
        raise ValidationError(f"Unknown target fact_id: {target_id}")

    verified_ids, invalid_ids, missing_ids = _dependency_closure(target_id, facts)
    target_status_mismatch = _fact_status(facts[target_id]) == "STATUS_MISMATCH"
    if target_status_mismatch:
        exclusions.append(
            {
                "input": f"fact_graph:{target_id}",
                "reason": "target status and verification_status disagree",
            }
        )
    for fact_id in invalid_ids:
        exclusions.append(
            {
                "input": f"fact_graph:{fact_id}",
                "reason": f"dependency is {_fact_status(facts[fact_id])}, not VERIFIED",
            }
        )
    for fact_id in missing_ids:
        exclusions.append(
            {"input": f"fact_graph:{fact_id}", "reason": "dependency record is missing"}
        )

    task_payload = task_record["payload"]
    artifact_values = _normalize_items(artifacts) if artifacts is not None else _task_items(
        task_payload, ("artifacts", "input_artifacts", "context_artifacts")
    )
    source_values = _normalize_items(sources) if sources is not None else _task_items(
        task_payload, ("sources", "source_artifacts", "opened_sources")
    )
    artifact_records, artifact_descriptors = _materialize_items(
        artifact_values, kind="artifact", root=root, exclusions=exclusions
    )
    source_records, source_descriptors = _materialize_items(
        source_values, kind="source", root=root, exclusions=exclusions
    )
    policy, policy_descriptors = _load_policy(root, policy_files)

    input_manifest = [
        task_descriptor,
        role_descriptor,
        graph_descriptor,
        *artifact_descriptors,
        *source_descriptors,
        *policy_descriptors,
    ]
    options = {"target_fact_id": target_id, "budget": budget}
    cache_key = _cache_key(input_manifest, options)
    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "compiler_version": COMPILER_VERSION,
        "packet_id": "sha256:" + "0" * 64,
        "packet_digest": "0" * 64,
        "cache_key": cache_key,
        "cache_path": f"build/context-cache/{cache_key}.json",
        "status": (
            "NEEDS_CONTEXT_REVIEW"
            if invalid_ids or missing_ids or target_status_mismatch
            else "READY"
        ),
        "budget": {
            "mode": budget,
            "limit_tokens": TOKEN_BUDGETS[budget],
            "estimation": "ceil(canonical UTF-8 bytes / 4)",
            "utf8_bytes": 0,
            "estimated_tokens": 0,
            "truncated": False,
        },
        "input_manifest": input_manifest,
        "task": task_record,
        "role": role_record,
        "target_fact": _safe_project_fact(
            facts[target_id], target=True, location="target_fact", exclusions=exclusions
        ),
        "verified_dependencies": [
            _safe_project_fact(
                facts[fact_id],
                target=False,
                location=f"fact.{fact_id}",
                exclusions=exclusions,
            )
            for fact_id in verified_ids
        ],
        "artifacts": artifact_records,
        "sources": source_records,
        "policy": policy,
        "exclusions": exclusions,
    }
    force_review = bool(invalid_ids or missing_ids or target_status_mismatch)
    _set_budget_metrics(packet, force_review=force_review)
    packet["packet_digest"] = _packet_digest(packet)
    packet["packet_id"] = f"sha256:{packet['packet_digest']}"
    _set_budget_metrics(packet, force_review=force_review)
    packet["packet_digest"] = _packet_digest(packet)
    packet["packet_id"] = f"sha256:{packet['packet_digest']}"
    return packet


def _walk_forbidden(value: Any, location: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key)
            if key.lower() in _FORBIDDEN_KEYS:
                errors.append(f"{location}.{key}: forbidden chat/chain-of-thought field")
            if _SECRET_KEY_RE.search(key) and item not in (None, "", "UNKNOWN", "[REDACTED]"):
                errors.append(f"{location}.{key}: unredacted secret field")
            errors.extend(_walk_forbidden(item, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_walk_forbidden(item, f"{location}[{index}]"))
    elif isinstance(value, str) and _SECRET_VALUE_RE.search(value):
        errors.append(f"{location}: secret-like value")
    return errors


def check_context_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Check schema, content addressing, dependency policy, secrecy and budget."""

    errors = validate_instance(packet, load_schema("context_packet"))
    warnings: list[str] = []
    manifest = packet.get("input_manifest", [])
    budget = packet.get("budget", {})
    options = {
        "target_fact_id": packet.get("target_fact", {}).get("fact_id"),
        "budget": budget.get("mode"),
    }
    if isinstance(manifest, list) and packet.get("cache_key") != _cache_key(manifest, options):
        errors.append("$.cache_key: does not match the complete input manifest")
    expected_digest = _packet_digest(packet)
    if packet.get("packet_digest") != expected_digest:
        errors.append("$.packet_digest: content digest mismatch")
    if packet.get("packet_id") != f"sha256:{packet.get('packet_digest')}":
        errors.append("$.packet_id: does not match packet_digest")
    for dependency in packet.get("verified_dependencies", []):
        if dependency.get("status") != "VERIFIED":
            errors.append(
                f"$.verified_dependencies[{dependency.get('fact_id', '?')}]: status is not VERIFIED"
            )
        content = {key: value for key, value in dependency.items() if key != "digest"}
        if dependency.get("digest") != _digest(content):
            errors.append(
                f"$.verified_dependencies[{dependency.get('fact_id', '?')}]: digest mismatch"
            )
        if "proof" in dependency:
            errors.append(
                f"$.verified_dependencies[{dependency.get('fact_id', '?')}]: dependency proof is excluded"
            )
    target = packet.get("target_fact", {})
    if isinstance(target, Mapping):
        target_content = {key: value for key, value in target.items() if key != "digest"}
        if target.get("digest") != _digest(target_content):
            errors.append("$.target_fact.digest: mismatch")
    errors.extend(_walk_forbidden(packet))
    byte_count = len(_canonical_bytes(packet))
    token_count = math.ceil(byte_count / 4)
    if budget.get("utf8_bytes") != byte_count:
        errors.append("$.budget.utf8_bytes: estimate does not match canonical packet")
    if budget.get("estimated_tokens") != token_count:
        errors.append("$.budget.estimated_tokens: estimate does not match UTF-8 bytes / 4")
    limit = budget.get("limit_tokens")
    expected_status = "READY" if isinstance(limit, int) and token_count <= limit else "NEEDS_CONTEXT_REVIEW"
    dependency_exclusions = [
        item
        for item in packet.get("exclusions", [])
        if isinstance(item, Mapping)
        and (
            "not VERIFIED" in str(item.get("reason"))
            or "dependency record is missing" in str(item.get("reason"))
            or "status and verification_status disagree" in str(item.get("reason"))
        )
    ]
    if dependency_exclusions:
        expected_status = "NEEDS_CONTEXT_REVIEW"
        warnings.append("dependency closure is incomplete or contains non-VERIFIED facts")
    if packet.get("status") != expected_status:
        errors.append(f"$.status: expected {expected_status}")
    if token_count > TOKEN_BUDGETS["max"]:
        warnings.append("packet exceeds the global 32k soft maximum")
    status = "READY" if not errors and expected_status == "READY" else "NEEDS_CONTEXT_REVIEW"
    return {
        "status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "estimated_tokens": token_count,
        "limit_tokens": limit,
        "cache_key": packet.get("cache_key"),
        "packet_digest": packet.get("packet_digest"),
    }


def explain_context_packet(packet: Mapping[str, Any]) -> str:
    """Return a compact, deterministic explanation suitable for logs or CLI use."""

    report = check_context_packet(packet)
    target = packet.get("target_fact", {})
    dependencies = [
        item.get("fact_id", "?") for item in packet.get("verified_dependencies", [])
    ]
    lines = [
        f"Context packet: {report['status']}",
        f"Target fact: {target.get('fact_id', 'UNKNOWN')} ({target.get('status', 'UNKNOWN')})",
        f"Budget: {report['estimated_tokens']}/{report['limit_tokens']} estimated tokens",
        f"Verified dependency closure: {', '.join(dependencies) if dependencies else '(empty)'}",
        f"Artifacts: {len(packet.get('artifacts', []))}; sources: {len(packet.get('sources', []))}",
        f"Exclusions: {len(packet.get('exclusions', []))}",
        f"Cache key: {report['cache_key']}",
        f"Packet digest: {report['packet_digest']}",
    ]
    if report["errors"]:
        lines.append("Errors: " + " | ".join(report["errors"]))
    if report["warnings"]:
        lines.append("Warnings: " + " | ".join(report["warnings"]))
    return "\n".join(lines)


# Short pure-function API names for callers that import this module as a compiler.
build = build_context_packet
check = check_context_packet
explain = explain_context_packet


__all__ = [
    "TOKEN_BUDGETS",
    "CHUNKABLE_LONG_CONTENT_KINDS",
    "UNSPLITTABLE_LONG_CONTENT_KINDS",
    "build",
    "build_context_packet",
    "check",
    "check_context_packet",
    "estimate_tokens",
    "chunk_long_content",
    "explain",
    "explain_context_packet",
]
