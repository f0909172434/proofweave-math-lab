from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import load_jsonl, save_jsonl, utc_now
from .schemas import require_valid


SOURCE_STATUSES = {"FOUND", "OPENED", "VERIFIED", "RETRACTED", "CONFLICT", "UNKNOWN"}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class SourceRegistry:
    REQUIRED = {
        "source_id",
        "title",
        "authors_or_organization",
        "publication_date",
        "url",
        "accessed_at",
        "source_type",
        "trust_level",
        "project_use",
        "exact_claim_supported",
        "status",
    }

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._records: dict[str, dict[str, Any]] = {}
        for record in load_jsonl(self.path):
            source_id = record.get("source_id", record.get("id"))
            if not source_id:
                raise IntegrityError("Source record is missing source_id")
            if source_id in self._records:
                raise IntegrityError(f"Duplicate source_id: {source_id}")
            record["source_id"] = source_id
            record.pop("id", None)
            self._records[source_id] = record

    def _validate(self, record: dict[str, Any]) -> None:
        missing = sorted(self.REQUIRED - record.keys())
        if missing:
            raise ValidationError(f"Source missing required fields: {', '.join(missing)}")
        require_valid(record, "source", SCHEMA_ROOT)
        if record["status"] not in SOURCE_STATUSES:
            raise ValidationError(f"Invalid source status: {record['status']}")
        if not str(record["url"]).startswith(("https://", "http://")):
            raise ValidationError("Source URL must be http(s)")
        if record["status"] in {"OPENED", "VERIFIED"} and not record.get("opened_at"):
            raise ValidationError(f"{record['status']} source requires opened_at")
        if record["status"] == "VERIFIED":
            if not str(record.get("exact_claim_supported", "")).strip():
                raise ValidationError("VERIFIED source requires exact_claim_supported")
            if not record.get("verified_by"):
                raise ValidationError("VERIFIED source requires verified_by")

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        value = deepcopy(record)
        if "id" in value and "source_id" not in value:
            value["source_id"] = value.pop("id")
        value.setdefault("accessed_at", utc_now())
        value.setdefault("publication_date", "UNKNOWN")
        value.setdefault("license", "UNKNOWN")
        value.setdefault("conflicts", [])
        value.setdefault("notes", "")
        value.setdefault("status", "FOUND")
        source_id = value.get("source_id")
        if source_id in self._records:
            raise IntegrityError(f"Duplicate source_id: {source_id}")
        self._validate(value)
        self._records[source_id] = value
        self._persist()
        return deepcopy(value)

    def transition(
        self, source_id: str, status: str, *, actor: str, exact_claim_supported: str | None = None
    ) -> dict[str, Any]:
        if source_id not in self._records:
            raise ValidationError(f"Unknown source_id: {source_id}")
        if status not in SOURCE_STATUSES:
            raise ValidationError(f"Invalid source status: {status}")
        record = self._records[source_id]
        record["status"] = status
        if status in {"OPENED", "VERIFIED"}:
            record.setdefault("opened_at", utc_now())
        if exact_claim_supported is not None:
            record["exact_claim_supported"] = exact_claim_supported
        if status == "VERIFIED":
            record["verified_by"] = actor
            record["verified_at"] = utc_now()
        self._validate(record)
        self._persist()
        return deepcopy(record)

    def _persist(self) -> None:
        save_jsonl(self.path, (self._records[key] for key in sorted(self._records)))

    def get(self, source_id: str) -> dict[str, Any]:
        if source_id not in self._records:
            raise ValidationError(f"Unknown source_id: {source_id}")
        return deepcopy(self._records[source_id])

    def all(self) -> list[dict[str, Any]]:
        return [deepcopy(self._records[key]) for key in sorted(self._records)]

    def check(self) -> list[str]:
        errors: list[str] = []
        for source_id, record in self._records.items():
            try:
                self._validate(record)
            except ValidationError as exc:
                errors.append(f"{source_id}: {exc}")
        return errors
