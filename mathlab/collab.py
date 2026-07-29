"""Auditable boundary artifacts for the AI Collaboration Console.

This module deliberately does not call a provider or the Console.  It prepares
bounded requests and records already-returned Console results.  That keeps the
research ledger useful when the integration is unavailable and prevents a
transport failure from being mistaken for a completed external job.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import SECRET_KEY_RE, SECRET_VALUE_RE, load_jsonl, stable_digest, utc_now
from .schemas import require_valid


SCHEMA_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = "state/collab_jobs.jsonl"
ALLOWED_REQUEST_STATUSES = {"PROPOSED", "OPEN", "COMPUTATIONAL"}
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_SENSITIVITIES = {"public", "private", "restricted"}
ALLOWED_PROFILES = {"fast", "standard", "deep", "max"}
PROFILE_INPUT_LIMITS = {"fast": 8_000, "standard": 16_000, "deep": 24_000, "max": 32_000}
PROFILE_EFFORTS = {"fast": "low", "standard": "medium", "deep": "high", "max": "xhigh"}
ROLE_CAPABILITIES = {
    "coding": ["coding", "structured_output"],
    "math": ["mathematical_reasoning"],
    "research": ["research", "source_grounding"],
    "scientific_writing": ["scientific_writing"],
    "teaching_material": ["teaching_material"],
    "data_analysis": ["data_analysis"],
    "summarization": ["summarization"],
    "translation": ["translation"],
    "review": ["review", "critical_analysis"],
    "general": ["general"],
}
RESULT_STATUSES = {
    "completed",
    "needs_review",
    "awaiting_manual",
    "needs_attention",
    "COLLAB_UNAVAILABLE",
}
FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "raw_chain_of_thought",
    "cot",
    "thoughts",
    "analysis",
    "reasoning_trace",
}
ACCOUNTING_TOKEN_KEYS = {"input_tokens", "cached_input_tokens", "output_tokens"}


def _redact_collaboration_secrets(value: Any) -> Any:
    """Redact credentials without mistaking numeric token accounting for a secret."""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in ACCOUNTING_TOKEN_KEYS and isinstance(item, int) and not isinstance(item, bool):
                redacted[key] = item
            elif SECRET_KEY_RE.search(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_collaboration_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_collaboration_secrets(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def _contains_collaboration_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ACCOUNTING_TOKEN_KEYS and isinstance(item, int) and not isinstance(item, bool):
                continue
            if SECRET_KEY_RE.search(str(key)) and item not in (None, "", "UNKNOWN", "[REDACTED]"):
                return True
            if _contains_collaboration_secret(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_collaboration_secret(item) for item in value)
    return bool(isinstance(value, str) and SECRET_VALUE_RE.search(value))


def _reject_raw_reasoning(value: Any, path: str = "$") -> None:
    """Reject hidden-reasoning fields at every nesting level."""

    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_REASONING_KEYS:
                raise ValidationError(f"Raw chain-of-thought field is forbidden at {path}.{key}")
            _reject_raw_reasoning(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_raw_reasoning(item, f"{path}[{index}]")


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append one UTF-8 JSON object without rewriting prior ledger evidence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


class CollaborationArtifacts:
    """Prepare, ingest and inspect collaboration records through a small API."""

    def __init__(self, root: Path | str, ledger_path: Path | str | None = None):
        self.root = Path(root)
        self.path = Path(ledger_path) if ledger_path is not None else self.root / DEFAULT_LEDGER

    def prepare(
        self,
        task_id: str,
        objective: str,
        *,
        role: str = "coding",
        research_status: str = "PROPOSED",
        context_packet_digest: str,
        risk: str = "medium",
        sensitivity: str = "private",
        profile: str | None = None,
        capability_tags: list[str] | None = None,
        max_output_tokens: int = 4_096,
        max_rounds: int = 1,
        estimated_cost_usd: float = 0.70,
        reviewer_required: bool | None = None,
        console_available: bool = True,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Console request, or an honest local fallback record.

        A workspace ID must never be inferred from a filesystem path.  Workspace
        operations are disabled in this artifact layer, so callers must not pass
        one here at all.
        """

        if workspace_id is not None:
            raise ValidationError("workspace_id is not accepted: do not infer or authorize workspace operations here")
        if research_status not in ALLOWED_REQUEST_STATUSES:
            raise ValidationError("prepare accepts only PROPOSED, OPEN, or COMPUTATIONAL research status")
        if role not in ROLE_CAPABILITIES:
            raise ValidationError(f"Unknown collaboration role: {role!r}")
        if risk not in ALLOWED_RISKS:
            raise ValidationError(f"Unknown risk: {risk!r}")
        if sensitivity not in ALLOWED_SENSITIVITIES:
            raise ValidationError(f"Unknown sensitivity: {sensitivity!r}")
        if not isinstance(context_packet_digest, str) or not context_packet_digest.startswith("sha256:"):
            raise ValidationError("context_packet_digest must be a sha256: content digest")
        try:
            digest_hex = context_packet_digest.split(":", 1)[1]
            if len(digest_hex) != 64:
                raise ValueError
            int(digest_hex, 16)
        except (IndexError, ValueError) as exc:
            raise ValidationError("context_packet_digest must contain exactly 64 hexadecimal digits") from exc
        if not isinstance(task_id, str) or not task_id.strip() or not isinstance(objective, str) or not objective.strip():
            raise ValidationError("task_id and objective must be non-empty strings")
        profile = profile or {"low": "fast", "medium": "standard", "high": "max"}[risk]
        if profile not in ALLOWED_PROFILES:
            raise ValidationError(f"Unknown effort profile: {profile!r}")
        if max_output_tokens < 1 or max_rounds < 1:
            raise ValidationError("max_output_tokens and max_rounds must be positive")
        if estimated_cost_usd < 0 or estimated_cost_usd > 0.70:
            raise ValidationError("estimated_cost_usd must be between 0 and the USD 0.70 cap")
        reviewer_required = risk == "high" if reviewer_required is None else reviewer_required
        if not console_available:
            return self.console_unavailable(task_id, objective, role=role)

        request = {
            "request_id": "collab-request-" + stable_digest(
                {"task_id": task_id, "objective": objective, "role": role, "research_status": research_status}
            )[:16],
            "created_at": utc_now(),
            "task_id": task_id,
            "objective": objective,
            "role": role,
            "research_status": research_status,
            "risk": risk,
            "sensitivity": sensitivity,
            "context_packet_digest": context_packet_digest,
            "capability_tags": capability_tags or ROLE_CAPABILITIES[role],
            "effort": {
                "profile": profile,
                "requested": PROFILE_EFFORTS[profile],
                "native_mapping": "xhigh" if profile == "max" else PROFILE_EFFORTS[profile],
            },
            "limits": {
                "max_input_tokens": PROFILE_INPUT_LIMITS[profile],
                "max_output_tokens": max_output_tokens,
                "max_rounds": max_rounds,
            },
            "spend": {
                "authorization": "existing_balance",
                "maximum_usd": 0.70,
                "maximum_cny": 5.0,
                "estimated_cost_usd": estimated_cost_usd,
                "retry_on_402": False,
            },
            "review": {
                "required": reviewer_required,
                "different_model_family_required": reviewer_required,
                "unknown_family_is_independent": False,
                "copilot_auto_is_independent": False,
            },
            "workspace_operations": {"enabled": False},
            "fallback": "proofweave_native",
        }
        require_valid(request, "collab_job_request", SCHEMA_ROOT)
        return request

    def console_unavailable(self, task_id: str, objective: str, *, role: str = "coding") -> dict[str, Any]:
        """Persist a transport failure without fabricating a Console job id."""

        record = {
            "event_id": "collab-unavailable-" + stable_digest(
                {"task_id": task_id, "objective": objective, "role": role, "at": utc_now()}
            )[:16],
            "recorded_at": utc_now(),
            "request_id": None,
            "job_id": None,
            "task_id": task_id,
            "status": "COLLAB_UNAVAILABLE",
            "research_status": None,
            "summary": "AI Collaboration Console is unavailable; use proofweave_native fallback.",
            "reasoning_summary": None,
            "primary": None,
            "requested_effort": {"profile": "fallback", "level": "native"},
            "effective_effort": {"profile": "fallback", "level": "native"},
            "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "duration_ms": 0},
            "reviewer": None,
            "review_state": "unavailable",
            "disagreements": [],
            "artifacts": [],
            "evidence_status": "NONE",
            "spend": {"actual_usd": None, "actual_cny": None, "http_status": None, "retry_count": 0},
            "fallback": "proofweave_native",
        }
        self._append_record(record)
        return deepcopy(record)

    def needs_attention(
        self,
        task_id: str,
        summary: str,
        *,
        requested_profile: str,
        context_packet_digest: str | None = None,
    ) -> dict[str, Any]:
        """Persist a policy stop without submitting a provider job."""

        artifacts = []
        if context_packet_digest:
            digest = context_packet_digest.removeprefix("sha256:")
            artifacts.append(
                {"kind": "context_packet", "locator": "build/context-cache", "sha256": digest}
            )
        record = {
            "event_id": "collab-attention-" + stable_digest(
                {"task_id": task_id, "summary": summary, "at": utc_now()}
            )[:16],
            "recorded_at": utc_now(),
            "request_id": None,
            "job_id": None,
            "task_id": task_id,
            "status": "needs_attention",
            "research_status": None,
            "summary": summary,
            "reasoning_summary": None,
            "primary": None,
            "requested_effort": {
                "profile": requested_profile,
                "level": PROFILE_EFFORTS.get(requested_profile, "unknown"),
            },
            "effective_effort": {"profile": "unavailable", "level": "unavailable"},
            "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "duration_ms": 0},
            "reviewer": None,
            "review_state": "unavailable",
            "disagreements": [],
            "artifacts": artifacts,
            "evidence_status": "NONE",
            "spend": {"actual_usd": None, "actual_cny": None, "http_status": None, "retry_count": 0},
            "fallback": "proofweave_native",
        }
        self._validate_result(record)
        require_valid(record, "collab_job_result", SCHEMA_ROOT)
        self._append_record(record)
        return deepcopy(record)

    def ingest(self, result: dict[str, Any]) -> dict[str, Any]:
        """Strictly validate a Console result and append it as immutable evidence."""

        value = _redact_collaboration_secrets(deepcopy(result))
        if _contains_collaboration_secret(value):
            raise IntegrityError("Collaboration result still contains possible credential material after redaction")
        _reject_raw_reasoning(value)
        value.setdefault("event_id", "collab-event-" + stable_digest(value)[:16])
        value.setdefault("recorded_at", utc_now())
        value = self._normalize_review_gate(value)
        if value.get("status") in {"awaiting_manual", "needs_attention", "COLLAB_UNAVAILABLE"} and value.get("research_status") not in {None, "UNKNOWN"}:
            raise ValidationError(f"{value['status']} must not carry a research conclusion")
        value = self._normalize_research_status(value)
        self._validate_result(value)
        require_valid(value, "collab_job_result", SCHEMA_ROOT)
        self._append_record(value)
        return deepcopy(value)

    def _validate_result(self, value: dict[str, Any]) -> None:
        if not isinstance(value, dict):
            raise ValidationError("Collaboration result must be an object")
        status = value.get("status")
        if status not in RESULT_STATUSES:
            raise ValidationError(f"Unknown collaboration status: {status!r}")
        if value.get("research_status") == "VERIFIED":
            raise ValidationError("Console output cannot create a VERIFIED research conclusion")
        if status == "completed" and value.get("research_status") not in {"PROPOSED", "COMPUTATIONAL"}:
            raise ValidationError("completed Console results may conclude only PROPOSED or COMPUTATIONAL")
        if status in {"awaiting_manual", "needs_attention", "COLLAB_UNAVAILABLE"} and value.get("research_status") not in {None, "UNKNOWN"}:
            raise ValidationError(f"{status} must not carry a research conclusion")
        if status == "COLLAB_UNAVAILABLE" and value.get("job_id") is not None:
            raise ValidationError("COLLAB_UNAVAILABLE must not fabricate a Console job_id")

        primary = value.get("primary")
        if status not in {"COLLAB_UNAVAILABLE", "needs_attention"}:
            if not isinstance(primary, dict):
                raise ValidationError("A Console result requires primary provider/model/family metadata")
            missing_primary = [key for key in ("provider", "model", "model_family") if not primary.get(key)]
            if missing_primary:
                raise ValidationError("Primary result metadata is missing: " + ", ".join(missing_primary))

        spend = value.get("spend")
        if not isinstance(spend, dict):
            raise ValidationError("Collaboration result requires a spend object")
        for key, ceiling in (("actual_usd", 0.70), ("actual_cny", 5.0)):
            amount = spend.get(key)
            if isinstance(amount, bool) or (amount is not None and not isinstance(amount, (int, float))):
                raise ValidationError(f"{key} must be a number or null")
            if amount is not None and amount > ceiling:
                raise ValidationError(f"{key} exceeds the per-job existing-balance cap")
        if spend.get("http_status") == 402 and spend.get("retry_count", 0) != 0:
            raise ValidationError("A 402 response must not be retried")
        if spend.get("retry_count", 0) not in {0, None}:
            raise ValidationError("Retries are forbidden for bounded collaboration jobs")

        usage = value.get("usage")
        if not isinstance(usage, dict):
            raise ValidationError("Collaboration result requires token and duration usage metadata")
        for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
            amount = usage.get(key)
            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise ValidationError(f"usage.{key} must be a non-negative integer")
        duration = usage.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise ValidationError("usage.duration_ms must be a non-negative integer")

        for key in ("requested_effort", "effective_effort"):
            effort = value.get(key)
            if not isinstance(effort, dict) or not effort.get("profile") or not effort.get("level"):
                raise ValidationError(f"{key} requires profile and level")

        reviewer = value.get("reviewer")
        if reviewer is not None:
            if not isinstance(reviewer, dict):
                raise ValidationError("reviewer must be an object or null")
            missing_reviewer = [key for key in ("provider", "model", "model_family", "independent") if key not in reviewer]
            if missing_reviewer:
                raise ValidationError("Reviewer metadata is missing: " + ", ".join(missing_reviewer))
            if reviewer.get("independent"):
                primary_family = primary.get("model_family")
                reviewer_family = reviewer.get("model_family")
                if not primary_family or not reviewer_family or str(reviewer_family).upper() == "UNKNOWN":
                    raise ValidationError("An independent reviewer needs a known model family")
                if str(primary_family).casefold() == str(reviewer_family).casefold():
                    raise ValidationError("An independent reviewer must use a different model family")
                if str(reviewer.get("model", "")).casefold() == "copilot-auto":
                    raise ValidationError("copilot-auto cannot count as an independent reviewer")

    @staticmethod
    def _normalize_review_gate(value: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(value)
        reviewer = normalized.get("reviewer")
        independent = isinstance(reviewer, dict) and reviewer.get("independent") is True
        if (
            normalized.get("status") == "completed"
            and normalized.get("risk") in {"high", "critical"}
            and not independent
        ):
            normalized["status"] = "needs_review"
            normalized["research_status"] = "OPEN"
            normalized["review_state"] = "pending"
            normalized["evidence_status"] = "OPEN"
            disagreements = normalized.setdefault("disagreements", [])
            note = "high-risk result lacks an independent different-family reviewer"
            if note not in disagreements:
                disagreements.append(note)
        return normalized

    @staticmethod
    def _normalize_research_status(value: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(value)
        if normalized["status"] == "needs_review":
            normalized["research_status"] = "OPEN"
        elif normalized["status"] in {"awaiting_manual", "needs_attention", "COLLAB_UNAVAILABLE"}:
            normalized["research_status"] = None
        return normalized

    def _append_record(self, record: dict[str, Any]) -> None:
        _reject_raw_reasoning(record)
        if any(existing.get("event_id") == record["event_id"] for existing in load_jsonl(self.path)):
            raise IntegrityError(f"Duplicate collaboration event_id: {record['event_id']}")
        _append_jsonl(self.path, record)

    def history(self) -> list[dict[str, Any]]:
        """Read immutable records only; this API never calls the Console."""

        return deepcopy(load_jsonl(self.path))

    def audit(self) -> dict[str, Any]:
        """Validate the local append-only ledger without a Console side effect."""

        errors: list[str] = []
        seen: set[str] = set()
        for index, record in enumerate(self.history(), 1):
            event_id = record.get("event_id")
            if not event_id or event_id in seen:
                errors.append(f"record {index}: missing or duplicate event_id")
                continue
            seen.add(event_id)
            try:
                _reject_raw_reasoning(record)
                self._validate_result(record)
                require_valid(record, "collab_job_result", SCHEMA_ROOT)
            except ValidationError as exc:
                errors.append(f"record {index}: {exc}")
        return {"status": "PASS" if not errors else "FAIL", "records": len(seen), "errors": errors}


# Small functional API for scripts and tests.  No CLI command is intentionally
# registered: prepare/ingest/audit/history are local API operations only.
def prepare(root: Path | str, task_id: str, objective: str, **kwargs: Any) -> dict[str, Any]:
    return CollaborationArtifacts(root).prepare(task_id, objective, **kwargs)


def ingest(root: Path | str, result: dict[str, Any]) -> dict[str, Any]:
    return CollaborationArtifacts(root).ingest(result)


def history(root: Path | str) -> list[dict[str, Any]]:
    return CollaborationArtifacts(root).history()


def audit(root: Path | str) -> dict[str, Any]:
    return CollaborationArtifacts(root).audit()


CollabArtifacts = CollaborationArtifacts
CollabLedger = CollaborationArtifacts
