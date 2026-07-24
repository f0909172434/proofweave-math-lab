from __future__ import annotations

import json
from pathlib import Path

from mathlab.io import configure_utf8_console

from mathlab.budget_manager import BudgetManager
from mathlab.io import find_project_root, load_json, save_json
from mathlab.model_registry import ModelRegistry
from mathlab.model_router import recommend_model
from mathlab.task_classifier import classify_task, load_task


def main() -> int:
    configure_utf8_console()
    root = find_project_root(Path.cwd())
    demo = root / "examples" / "routing_demo"
    registry = ModelRegistry.from_path(root / "state" / "model_inventory.json")
    budget = BudgetManager(root / "state" / "budget_state.json")
    policy = load_json(root / "config" / "runtime_policy.json", default={}) or {}
    results = []
    for path in sorted((demo / "tasks").glob("*.md")):
        classification = classify_task(load_task(path))
        decision = recommend_model(classification, registry, budget, user_policy=policy)
        results.append(
            {
                "task": path.name,
                "task_type": classification["task_type"],
                "complexity": classification["complexity_score"],
                "risk": classification["risk_score"],
                "recommended_tier": classification["recommended_capability_tier"],
                "selected_model": decision["selected_model"],
                "selected_tier": decision["selected_capability_tier"],
                "reasoning_profile": decision["requested_reasoning_profile"],
                "effective_reasoning": decision["effective_reasoning_setting"],
                "routing_reason": decision["routing_reason"],
                "status": decision["status"],
            }
        )
    output = {
        "status": "PASS" if len(results) == 6 and all(row["status"] == "RECOMMENDED" for row in results) else "FAIL",
        "paid_calls": 0,
        "model_inventory_version": registry.version,
        "results": results,
    }
    save_json(demo / "results.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
