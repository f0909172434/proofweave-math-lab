from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TASK_PROFILES: list[tuple[str, tuple[str, ...], int, int, str, str]] = [
    ("formatting", ("markdown heading", "format", "typo", "標題", "排版"), 12, 8, "UTILITY", "LOW"),
    ("doi_lookup", ("doi", "bibliographic", "文獻", "citation"), 28, 25, "STANDARD", "LOW"),
    ("local_algebra", ("algebra", "identity", "代數", "等式"), 48, 60, "ADVANCED", "HIGH"),
    ("asymptotics_audit", ("asymptotic", "little-o", "big-o", "漸近", "limit exchange"), 72, 86, "FRONTIER", "VERY_HIGH"),
    ("counterexample_search", ("counterexample", "disprove", "反例", "for all", "theorem"), 78, 92, "FRONTIER", "HIGH"),
    ("referee_review", ("referee", "manuscript", "全文", "審稿", "review paper"), 88, 94, "FRONTIER", "VERY_HIGH"),
]


def load_task(path: Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("Task JSON must be an object")
        value.setdefault("text", value.get("description", ""))
        return value
    return {"text": text, "title": path.stem}


def classify_task(task: dict[str, Any] | str) -> dict[str, Any]:
    value = {"text": task} if isinstance(task, str) else dict(task)
    text = " ".join(str(value.get(key, "")) for key in ("title", "task_type", "text", "description"))
    lowered = text.lower()
    selected = ("general_research", (), 55, 60, "ADVANCED", "HIGH")
    for profile in TASK_PROFILES:
        if any(keyword in lowered for keyword in profile[1]):
            if profile[2] + profile[3] > selected[2] + selected[3] or selected[0] == "general_research":
                selected = profile
    task_type, _, complexity, risk, tier, reasoning = selected
    universal = bool(re.search(r"\b(for all|every|global|theorem|prove)\b|對所有|全域|定理|證明", lowered))
    if universal and task_type not in {"formatting", "doi_lookup"}:
        risk = min(100, risk + 7)
    context_size = int(value.get("context_size", len(text)))
    dependency_count = int(value.get("dependency_count", 0))
    complexity = min(100, complexity + min(10, dependency_count * 2) + (8 if context_size > 100_000 else 0))
    required_tools: list[str] = []
    if task_type == "doi_lookup" or value.get("web_requirement"):
        required_tools.append("web_search")
    if task_type in {"local_algebra", "asymptotics_audit", "counterexample_search"}:
        required_tools.append("code_execution")
    if value.get("symbolic_requirement"):
        required_tools.append("symbolic")
    if value.get("numerical_requirement"):
        required_tools.append("code_execution")
    independence = "REQUIRED" if risk >= 80 else "PREFERRED" if risk >= 55 else "NOT_REQUIRED"
    return {
        "task_type": value.get("task_type", task_type),
        "mathematical_domain": value.get("mathematical_domain", "UNKNOWN"),
        "proof_depth": value.get("proof_depth", "high" if risk >= 80 else "medium"),
        "novelty": value.get("novelty", "UNKNOWN"),
        "error_cost": value.get("error_cost", "high" if risk >= 75 else "medium"),
        "verification_importance": "critical" if risk >= 85 else "normal",
        "context_size": context_size,
        "tool_requirements": sorted(set(required_tools)),
        "web_requirement": "web_search" in required_tools,
        "coding_requirement": "code_execution" in required_tools,
        "symbolic_requirement": bool(value.get("symbolic_requirement", False)),
        "numerical_requirement": bool(value.get("numerical_requirement", False)),
        "multimodal_requirement": bool(value.get("multimodal_requirement", False)),
        "expected_output_length": value.get("expected_output_length", "medium"),
        "dependency_count": dependency_count,
        "ambiguity": value.get("ambiguity", "UNKNOWN"),
        "adversarial_risk": "high" if task_type in {"counterexample_search", "referee_review"} else "normal",
        "latency_priority": value.get("latency_priority", "normal"),
        "cost_priority": value.get("cost_priority", "normal"),
        "privacy_constraints": value.get("privacy_constraints", []),
        "complexity_score": complexity,
        "risk_score": risk,
        "recommended_capability_tier": tier,
        "recommended_reasoning_profile": reasoning,
        "required_tools": sorted(set(required_tools)),
        "independence_requirement": independence,
        "fallback_policy": "bounded_escalation_then_human" if risk >= 75 else "one_fallback_then_advisory",
        "justification": (
            f"Classified as {task_type}; score uses semantic risk, dependencies, context, and tools, not prompt length alone."
        ),
    }

