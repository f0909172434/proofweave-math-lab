from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import contains_secret, load_jsonl, redact_secrets, save_jsonl
from .schemas import require_valid


SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class RoutingAudit:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def append(self, decision: dict[str, Any]) -> dict[str, Any]:
        safe = redact_secrets(decision)
        if contains_secret(safe):
            raise IntegrityError("Routing decision still contains a possible secret after redaction")
        records = load_jsonl(self.path)
        routing_id = safe.get("routing_id")
        if not routing_id:
            raise ValidationError("Routing decision is missing routing_id")
        require_valid(safe, "routing_decision", SCHEMA_ROOT)
        if any(record.get("routing_id") == routing_id for record in records):
            return safe
        records.append(safe)
        save_jsonl(self.path, records)
        return safe

    def find(self, routing_id: str) -> dict[str, Any]:
        for record in load_jsonl(self.path):
            if record.get("routing_id") == routing_id:
                return record
        raise ValidationError(f"Unknown routing_id: {routing_id}")

    def all(self) -> list[dict[str, Any]]:
        return load_jsonl(self.path)
