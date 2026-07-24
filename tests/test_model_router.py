from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.budget_manager import BudgetManager
from mathlab.model_registry import ModelRegistry
from mathlab.model_router import recommend_model
from mathlab.task_classifier import classify_task
from tests.common import inventory, model, write_json


class ModelRouterTests(unittest.TestCase):
    def _budget(self, temp: str, value: dict | None = None) -> BudgetManager:
        path = Path(temp) / "budget.json"
        if value is not None:
            write_json(path, value)
        return BudgetManager(path)

    def test_missing_required_tool_excludes_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("no-tools", tools=False), model("tools", tools=True)))
            classification = classify_task({"text": "verify local algebra", "web_requirement": True})
            result = recommend_model(classification, registry, self._budget(temp))
            self.assertEqual("tools", result["selected_model"])

    def test_context_too_small_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("small", context=10), model("large", context=100000)))
            classification = classify_task({"text": "general research", "context_size": 50000})
            result = recommend_model(classification, registry, self._budget(temp))
            self.assertEqual("large", result["selected_model"])

    def test_high_risk_theorem_never_routes_to_utility(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("utility", tier="UTILITY"), model("frontier", tier="FRONTIER")))
            result = recommend_model(classify_task("For all x, counterexample to main theorem"), registry, self._budget(temp))
            self.assertEqual("frontier", result["selected_model"])

    def test_formatting_does_not_default_to_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("standard", tier="STANDARD"), model("frontier", tier="FRONTIER")))
            result = recommend_model(classify_task("Fix Markdown heading format"), registry, self._budget(temp))
            self.assertEqual("standard", result["selected_model"])

    def test_verifier_prefers_different_model_family(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(
                model("same", tier="FRONTIER", family="family-a"),
                model("different", tier="FRONTIER", family="family-b"),
            ))
            result = recommend_model(
                classify_task("referee review of theorem proof"),
                registry,
                self._budget(temp),
                previous_execution={"provider": "host", "model_family": "family-a"},
            )
            self.assertEqual("different", result["selected_model"])

    def test_forbidden_provider_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("forbidden", provider="bad"), model("allowed", provider="good")))
            result = recommend_model(
                classify_task("general research"), registry, self._budget(temp),
                user_policy={"forbidden_providers": ["bad"]}
            )
            self.assertEqual("allowed", result["selected_model"])

    def test_requested_unavailable_model_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("available")))
            result = recommend_model(
                classify_task("general research"), registry, self._budget(temp),
                user_policy={"requested_model": "missing"}
            )
            self.assertEqual("ADVISORY_ONLY", result["status"])
            self.assertIsNone(result["selected_model"])

    def test_private_task_requires_allowlisted_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("private", provider="local")))
            classification = classify_task(
                {"text": "general research", "privacy_constraints": ["contains unpublished theorem"]}
            )
            blocked = recommend_model(classification, registry, self._budget(temp))
            self.assertEqual("ADVISORY_ONLY", blocked["status"])
            self.assertTrue(any("privacy" in row["reason"] for row in blocked["rejected_candidates"]))
            allowed = recommend_model(
                classification,
                registry,
                self._budget(temp),
                user_policy={"private_data_provider_allowlist": ["local"]},
            )
            self.assertEqual("private", allowed["selected_model"])

    def test_cross_provider_verifier_route_requires_policy_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("other", provider="p2", family="family-b")))
            classification = classify_task("referee review of theorem proof")
            blocked = recommend_model(
                classification,
                registry,
                self._budget(temp),
                previous_execution={"provider": "p1", "model_family": "family-a"},
            )
            self.assertEqual("ADVISORY_ONLY", blocked["status"])
            allowed = recommend_model(
                classification,
                registry,
                self._budget(temp),
                user_policy={"allow_cross_provider_routing": True},
                previous_execution={"provider": "p1", "model_family": "family-a"},
            )
            self.assertEqual("other", allowed["selected_model"])

    def test_manual_approval_task_is_not_auto_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("m1")))
            classification = classify_task(
                {"text": "execute provider call", "task_type": "external_model_execution"}
            )
            result = recommend_model(
                classification,
                registry,
                self._budget(temp),
                user_policy={"tasks_requiring_manual_approval": ["external_model_execution"]},
            )
            self.assertEqual("NEEDS_HUMAN_DECISION", result["status"])
            self.assertIsNone(result["selected_model"])


if __name__ == "__main__":
    unittest.main()
