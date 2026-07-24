from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import load_json, save_json, utc_now
from .schemas import require_valid


DEFAULT_BUDGET = {
    "mode": "BALANCED",
    "currency": "USD",
    "per_task_budget": None,
    "per_workflow_budget": None,
    "daily_budget": None,
    "monthly_budget": None,
    "maximum_parallel_agents": 4,
    "maximum_frontier_calls": 8,
    "maximum_reasoning_escalations": 2,
    "maximum_model_escalations": 2,
    "maximum_provider_switches": 1,
    "maximum_repair_loops": 3,
    "maximum_paid_probes": 0,
    "provider_specific_limits": {},
    "spent_today": 0.0,
    "spent_month": 0.0,
    "frontier_calls": 0,
    "reasoning_escalations": 0,
    "model_escalations": 0,
    "provider_switches": 0,
    "paid_probes": 0,
}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class BudgetManager:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        loaded = load_json(self.path, default={}) or {}
        self.state = {**DEFAULT_BUDGET, **loaded}
        if self.state["mode"] not in {"ECONOMY", "BALANCED", "QUALITY_FIRST", "MANUAL"}:
            raise ValidationError(f"Invalid budget mode: {self.state['mode']}")
        require_valid(self.state, "budget_state", SCHEMA_ROOT)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def estimate(self, classification: dict[str, Any], model: dict[str, Any] | None = None) -> dict[str, Any]:
        input_cost = None if model is None else model.get("estimated_input_cost")
        output_cost = None if model is None else model.get("estimated_output_cost")
        estimated_cost = None
        if isinstance(input_cost, (int, float)) and isinstance(output_cost, (int, float)):
            context = max(1000, int(classification.get("context_size", 1000)))
            output = {"short": 1000, "medium": 4000, "long": 12000}.get(
                classification.get("expected_output_length"), 4000
            )
            estimated_cost = (context / 1_000_000) * input_cost + (output / 1_000_000) * output_cost
        return {
            "estimated_cost": estimated_cost,
            "currency": self.state["currency"],
            "status": "KNOWN" if estimated_cost is not None else "UNKNOWN",
        }

    def authorize(
        self,
        *,
        estimated_cost: float | None,
        capability_tier: str,
        paid_probe: bool = False,
    ) -> dict[str, str]:
        if paid_probe and self.state["paid_probes"] >= self.state["maximum_paid_probes"]:
            return {"status": "BLOCKED_BY_BUDGET", "reason": "paid probes are disabled or exhausted"}
        if capability_tier == "FRONTIER" and self.state["frontier_calls"] >= self.state["maximum_frontier_calls"]:
            return {"status": "BLOCKED_BY_BUDGET", "reason": "frontier call limit reached"}
        if estimated_cost is None:
            if self.state["mode"] == "MANUAL":
                return {"status": "NEEDS_HUMAN_DECISION", "reason": "cost is UNKNOWN in MANUAL mode"}
            return {"status": "AUTHORIZED", "reason": "cost UNKNOWN; bounded call limits still apply"}
        limits = [
            (self.state.get("per_task_budget"), estimated_cost, "per-task"),
            (self.state.get("daily_budget"), self.state["spent_today"] + estimated_cost, "daily"),
            (self.state.get("monthly_budget"), self.state["spent_month"] + estimated_cost, "monthly"),
        ]
        for limit, projected, name in limits:
            if isinstance(limit, (int, float)) and projected > limit:
                return {"status": "BLOCKED_BY_BUDGET", "reason": f"{name} budget exceeded"}
        return {"status": "AUTHORIZED", "reason": "within configured limits"}

    def register(self, *, actual_cost: float | None, capability_tier: str, paid_probe: bool = False) -> None:
        if actual_cost is not None:
            self.state["spent_today"] += actual_cost
            self.state["spent_month"] += actual_cost
        if capability_tier == "FRONTIER":
            self.state["frontier_calls"] += 1
        if paid_probe:
            self.state["paid_probes"] += 1
        self.state["updated_at"] = utc_now()
        save_json(self.path, self.state)

    def allow_escalation(self, kind: str) -> bool:
        mapping = {
            "reasoning": ("reasoning_escalations", "maximum_reasoning_escalations"),
            "model": ("model_escalations", "maximum_model_escalations"),
            "provider": ("provider_switches", "maximum_provider_switches"),
        }
        if kind not in mapping:
            raise ValidationError(f"Unknown escalation kind: {kind}")
        used, limit = mapping[kind]
        return self.state[used] < self.state[limit]
