from __future__ import annotations

from copy import deepcopy
from typing import Any

from .budget_manager import BudgetManager
from .model_registry import ModelRegistry
from .reasoning_router import map_reasoning
from .io import stable_digest, utc_now


TIER_RANK = {"UTILITY": 0, "STANDARD": 1, "ADVANCED": 2, "FRONTIER": 3}


def _tool_supported(model: dict[str, Any], tool: str) -> bool:
    aliases = {"symbolic": "code_execution"}
    return bool(model.get(aliases.get(tool, tool), False))


def _score(
    model: dict[str, Any],
    classification: dict[str, Any],
    previous_execution: dict[str, Any] | None,
) -> tuple[float, dict[str, float]]:
    requested = TIER_RANK[classification["recommended_capability_tier"]]
    offered = TIER_RANK.get(model.get("capability_tier", "STANDARD"), 1)
    capability_match = 25.0 if offered >= requested else max(0.0, 25.0 - 15.0 * (requested - offered))
    benchmark_score = float(model.get("benchmark_score", 0.5)) * 20.0
    tool_match = 15.0
    context_fit = 10.0 if model.get("context_window") in (None, "UNKNOWN") else 12.0
    reliability = float(model.get("reliability_score", 0.7)) * 15.0
    independence = 0.0
    correlated = 0.0
    if previous_execution:
        if model.get("provider") != previous_execution.get("provider"):
            independence += 6.0
        if model.get("model_family") != previous_execution.get("model_family"):
            independence += 6.0
        else:
            correlated = 8.0
    cost_penalty = {"UTILITY": 0.0, "STANDARD": 1.0, "ADVANCED": 3.0, "FRONTIER": 6.0}.get(
        model.get("capability_tier"), 3.0
    )
    if classification.get("cost_priority") == "high":
        cost_penalty *= 2
    latency_penalty = 4.0 if model.get("latency_class") == "HIGH" else 0.0
    deprecation = 100.0 if model.get("deprecation_status") == "DEPRECATED" else 0.0
    components = {
        "capability_match": capability_match,
        "benchmark_score": benchmark_score,
        "tool_match": tool_match,
        "context_fit": context_fit,
        "reliability_score": reliability,
        "independence_bonus": independence,
        "estimated_cost_penalty": cost_penalty,
        "latency_penalty": latency_penalty,
        "deprecation_penalty": deprecation,
        "availability_risk": 0.0,
        "correlated_error_penalty": correlated,
    }
    total = sum(
        value if not key.endswith("penalty") and key != "availability_risk" else -value
        for key, value in components.items()
    )
    return total, components


def recommend_model(
    classification: dict[str, Any],
    registry: ModelRegistry,
    budget: BudgetManager,
    *,
    user_policy: dict[str, Any] | None = None,
    previous_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = user_policy or {}
    requested_model = policy.get("requested_model")
    candidates = registry.executable(
        allow_configured_unverified=bool(policy.get("allow_configured_unverified", False)),
        forbidden_providers=set(policy.get("forbidden_providers", [])),
        forbidden_models=set(policy.get("forbidden_models", [])),
    )
    if requested_model:
        candidates = [model for model in candidates if model.get("model_id") == requested_model]
    rejected: list[dict[str, str]] = []
    scored: list[tuple[float, dict[str, Any], dict[str, float]]] = []
    requested_tier = classification["recommended_capability_tier"]
    task_type = classification.get("task_type")
    manual_types = set(policy.get("tasks_requiring_manual_approval", []))
    allow_cross_provider = bool(policy.get("allow_cross_provider_routing", False))
    if task_type in manual_types:
        return {
            "routing_id": stable_digest({"classification": classification, "inventory": registry.version})[:20],
            "status": "NEEDS_HUMAN_DECISION",
            "selected_provider": None,
            "selected_model": None,
            "selected_capability_tier": requested_tier,
            "requested_reasoning_profile": classification["recommended_reasoning_profile"],
            "effective_reasoning_setting": "UNKNOWN",
            "reasoning_control_method": "HOST_UNSUPPORTED",
            "routing_reason": f"Task type {task_type!r} requires explicit human approval.",
            "rejected_candidates": [],
            "estimated_cost": None,
            "expected_latency": "UNKNOWN",
            "fallback_chain": [],
            "escalation_conditions": ["human records explicit approval"],
            "independence_status": "UNAVAILABLE",
            "cross_provider_routing_allowed": allow_cross_provider,
            "model_inventory_version": registry.version,
            "created_at": utc_now(),
        }
    privacy_constraints = classification.get("privacy_constraints", [])
    private_allowlist = set(policy.get("private_data_provider_allowlist", []))
    for model in candidates:
        provider = model.get("provider")
        if privacy_constraints and provider not in private_allowlist:
            rejected.append(
                {
                    "model_id": model["model_id"],
                    "reason": f"privacy constraints require an allowlisted provider; {provider!r} is not allowlisted",
                }
            )
            continue
        if (
            previous_execution
            and previous_execution.get("provider")
            and provider != previous_execution.get("provider")
            and not allow_cross_provider
        ):
            rejected.append(
                {
                    "model_id": model["model_id"],
                    "reason": "cross-provider routing is disabled by policy",
                }
            )
            continue
        missing_tools = [
            tool for tool in classification.get("required_tools", []) if not _tool_supported(model, tool)
        ]
        if missing_tools:
            rejected.append({"model_id": model["model_id"], "reason": f"missing tools: {missing_tools}"})
            continue
        context = model.get("context_window")
        if isinstance(context, int) and context < classification.get("context_size", 0):
            rejected.append({"model_id": model["model_id"], "reason": "context window too small"})
            continue
        offered = TIER_RANK.get(model.get("capability_tier", "STANDARD"), 1)
        if classification["risk_score"] >= 75 and offered < TIER_RANK["ADVANCED"]:
            rejected.append({"model_id": model["model_id"], "reason": "high-risk work cannot use UTILITY/STANDARD"})
            continue
        value, components = _score(model, classification, previous_execution)
        scored.append((value, model, components))
    if not scored:
        return {
            "routing_id": stable_digest({"classification": classification, "inventory": registry.version})[:20],
            "status": "ADVISORY_ONLY",
            "selected_provider": None,
            "selected_model": None,
            "selected_capability_tier": requested_tier,
            "requested_reasoning_profile": classification["recommended_reasoning_profile"],
            "effective_reasoning_setting": "UNKNOWN",
            "reasoning_control_method": "HOST_UNSUPPORTED",
            "routing_reason": "No verified executable model passed hard filters.",
            "rejected_candidates": rejected,
            "estimated_cost": None,
            "expected_latency": "UNKNOWN",
            "fallback_chain": [],
            "escalation_conditions": ["human enables a verified provider"],
            "independence_status": "UNAVAILABLE",
            "cross_provider_routing_allowed": allow_cross_provider,
            "model_inventory_version": registry.version,
            "created_at": utc_now(),
        }
    scored.sort(key=lambda item: (-item[0], item[1]["model_id"]))
    _, selected, components = scored[0]
    reasoning = map_reasoning(
        classification["recommended_reasoning_profile"],
        selected.get("supported_reasoning_levels", []),
        host_can_control=True,
    )
    estimate = budget.estimate(classification, selected)
    authorization = budget.authorize(
        estimated_cost=estimate["estimated_cost"],
        capability_tier=selected.get("capability_tier", requested_tier),
    )
    status = "RECOMMENDED" if authorization["status"] == "AUTHORIZED" else authorization["status"]
    fallback_models = [
        model
        for _, model, _ in scored[1:]
        if allow_cross_provider or model.get("provider") == selected.get("provider")
    ]
    fallback = [model["model_id"] for model in fallback_models[:2]]
    independence = "NOT_APPLICABLE"
    if previous_execution:
        independence = (
            "INDEPENDENT_FAMILY"
            if selected.get("model_family") != previous_execution.get("model_family")
            else "CORRELATED_MODEL_FAMILY"
        )
    routing_core = {
        "classification": classification,
        "selected": selected["model_id"],
        "inventory": registry.version,
        "previous": previous_execution,
    }
    return {
        "routing_id": stable_digest(routing_core)[:20],
        "status": status,
        "selected_provider": selected.get("provider"),
        "selected_model": selected["model_id"],
        "selected_capability_tier": selected.get("capability_tier", requested_tier),
        **reasoning,
        "routing_reason": (
            f"Highest deterministic score after availability, tool, context, risk and policy filters; {authorization['reason']}."
        ),
        "score_components": components,
        "rejected_candidates": rejected,
        "estimated_cost": estimate["estimated_cost"],
        "expected_latency": selected.get("latency_class", "UNKNOWN"),
        "fallback_chain": fallback,
        "escalation_conditions": [
            "verifier REJECT or UNCERTAIN",
            "two no-progress attempts",
            "agent conflict or suspected counterexample",
            "unjustified limit/derivative/integral exchange",
            "grid-sensitive numerical result",
        ],
        "independence_status": independence,
        "cross_provider_routing_allowed": allow_cross_provider,
        "model_inventory_version": registry.version,
        "created_at": utc_now(),
    }


def mark_routing_failed(decision: dict[str, Any], reason: str) -> dict[str, Any]:
    failed = deepcopy(decision)
    failed["status"] = "ROUTING_FAILED"
    failed["execution_error"] = reason
    failed["execution_succeeded"] = False
    failed["failed_at"] = utc_now()
    return failed


def apply_fallback(
    decision: dict[str, Any], registry: ModelRegistry, *, failed_model: str, reason: str
) -> dict[str, Any]:
    for model_id in decision.get("fallback_chain", []):
        if model_id == failed_model:
            continue
        try:
            model = registry.get(model_id)
        except Exception:
            continue
        if model.get("availability_status") != "VERIFIED_AVAILABLE":
            continue
        if model.get("deprecation_status") == "DEPRECATED":
            continue
        if (
            not bool(decision.get("cross_provider_routing_allowed", False))
            and model.get("provider") != decision.get("selected_provider")
        ):
            continue
        fallback = deepcopy(decision)
        fallback["selected_model"] = model_id
        fallback["selected_provider"] = model.get("provider")
        fallback["fallback_used"] = True
        fallback["fallback_from"] = failed_model
        fallback["fallback_reason"] = reason
        fallback["status"] = "RECOMMENDED"
        return fallback
    return mark_routing_failed(decision, f"No usable fallback after {failed_model}: {reason}")
