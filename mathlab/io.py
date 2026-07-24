from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .errors import ValidationError


SECRET_KEY_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|cookie|authorization|bearer|credential)"
)
SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+)"
)


def configure_utf8_console() -> None:
    """Keep JSON diagnostics printable on Windows consoles with legacy encodings."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (OSError, ValueError):
                pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)


def load_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, value: Any) -> None:
    atomic_write_text(
        Path(path), json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValidationError(f"JSONL record at {path}:{line_number} is not an object")
        records.append(value)
    return records


def save_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    atomic_write_text(Path(path), "\n".join(lines) + ("\n" if lines else ""))


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / "AGENTS.md").exists():
            return candidate
    return current


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            result[key] = "[REDACTED]" if SECRET_KEY_RE.search(str(key)) else redact_secrets(item)
        return result
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            SECRET_KEY_RE.search(str(key)) and item not in (None, "", "UNKNOWN", "[REDACTED]")
            or contains_secret(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_secret(item) for item in value)
    return bool(isinstance(value, str) and SECRET_VALUE_RE.search(value))
