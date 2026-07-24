from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import load_jsonl, save_jsonl, utc_now
from .schemas import require_valid


ISSUE_STATUSES = {"OPEN", "IN_PROGRESS", "FIXED", "REJECTED", "DEFERRED"}
SEVERITIES = {"FATAL", "MAJOR", "MINOR", "STRENGTH"}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class IssueLedger:
    REQUIRED = {
        "issue_id",
        "severity",
        "status",
        "location",
        "affected_claims",
        "explanation",
        "failed_step",
        "required_fix",
        "verification_after_fix",
    }

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._records: dict[str, dict[str, Any]] = {}
        for record in load_jsonl(self.path):
            issue_id = record.get("issue_id")
            if not issue_id:
                raise IntegrityError("Issue is missing issue_id")
            if issue_id in self._records:
                raise IntegrityError(f"Duplicate issue_id: {issue_id}")
            self._records[issue_id] = record

    def _validate(self, record: dict[str, Any]) -> None:
        missing = sorted(self.REQUIRED - record.keys())
        if missing:
            raise ValidationError(f"Issue missing required fields: {', '.join(missing)}")
        require_valid(record, "review_issue", SCHEMA_ROOT)
        if record["severity"] not in SEVERITIES:
            raise ValidationError(f"Invalid severity: {record['severity']}")
        if record["status"] not in ISSUE_STATUSES:
            raise ValidationError(f"Invalid issue status: {record['status']}")
        if not isinstance(record["affected_claims"], list):
            raise ValidationError("affected_claims must be an array")
        if record["status"] == "FIXED" and not record.get("fix_artifacts"):
            raise ValidationError("FIXED issue requires fix_artifacts")

    def _persist(self) -> None:
        save_jsonl(self.path, (self._records[key] for key in sorted(self._records)))

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        value = deepcopy(record)
        value.setdefault("status", "OPEN")
        value.setdefault("counterexample", None)
        value.setdefault("created_at", utc_now())
        value.setdefault("updated_at", value["created_at"])
        value.setdefault("fix_artifacts", [])
        value.setdefault("modified_files", [])
        value.setdefault("rerun_experiments", [])
        value.setdefault("reverify_sections", [])
        issue_id = value.get("issue_id")
        if issue_id in self._records:
            raise IntegrityError(f"Duplicate issue_id: {issue_id}")
        self._validate(value)
        self._records[issue_id] = value
        self._persist()
        return deepcopy(value)

    def update(self, issue_id: str, status: str, **changes: Any) -> dict[str, Any]:
        if issue_id not in self._records:
            raise ValidationError(f"Unknown issue_id: {issue_id}")
        if status not in ISSUE_STATUSES:
            raise ValidationError(f"Invalid issue status: {status}")
        value = self._records[issue_id]
        value.update(deepcopy(changes))
        value["status"] = status
        value["updated_at"] = utc_now()
        self._validate(value)
        self._persist()
        return deepcopy(value)

    def all(self) -> list[dict[str, Any]]:
        return [deepcopy(self._records[key]) for key in sorted(self._records)]

    def check(self) -> list[str]:
        errors: list[str] = []
        for issue_id, record in self._records.items():
            try:
                self._validate(record)
            except ValidationError as exc:
                errors.append(f"{issue_id}: {exc}")
        return errors
