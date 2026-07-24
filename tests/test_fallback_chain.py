from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.budget_manager import BudgetManager
from mathlab.model_registry import ModelRegistry
from mathlab.model_router import apply_fallback, mark_routing_failed, recommend_model
from mathlab.routing_audit import RoutingAudit
from mathlab.task_classifier import classify_task
from tests.common import inventory, model


class FallbackChainTests(unittest.TestCase):
    def test_provider_failure_uses_verified_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("primary", provider="p1"), model("fallback", provider="p1")))
            decision = recommend_model(classify_task("general research"), registry, BudgetManager(Path(temp) / "budget.json"))
            failed = decision["selected_model"]
            fallback = apply_fallback(decision, registry, failed_model=failed, reason="provider unavailable")
            self.assertTrue(fallback["fallback_used"])
            self.assertNotEqual(failed, fallback["selected_model"])

    def test_no_fallback_marks_routing_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("only")))
            decision = recommend_model(classify_task("general research"), registry, BudgetManager(Path(temp) / "budget.json"))
            failed = apply_fallback(decision, registry, failed_model="only", reason="switch failed")
            self.assertEqual("ROUTING_FAILED", failed["status"])

    def test_explicit_switch_failure_marker(self) -> None:
        failed = mark_routing_failed({"routing_id": "r1", "status": "RECOMMENDED"}, "host rejected model switch")
        self.assertEqual("ROUTING_FAILED", failed["status"])
        self.assertFalse(failed["execution_succeeded"])

    def test_routing_log_redacts_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("m1")))
            decision = recommend_model(
                classify_task("general research"),
                registry,
                BudgetManager(Path(temp) / "budget.json"),
            )
            decision["api_key"] = "unit-test-secret-value"
            audit = RoutingAudit(Path(temp) / "routing.jsonl")
            saved = audit.append(decision)
            self.assertEqual("[REDACTED]", saved["api_key"])

    def test_same_input_and_inventory_have_same_routing_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("m1")))
            budget = BudgetManager(Path(temp) / "budget.json")
            classification = classify_task("general research")
            first = recommend_model(classification, registry, budget)
            second = recommend_model(classification, registry, budget)
            self.assertEqual(first["routing_id"], second["routing_id"])

    def test_deprecated_model_cannot_be_injected_as_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("primary"), model("old", deprecated=True)))
            decision = recommend_model(
                classify_task("general research"), registry, BudgetManager(Path(temp) / "budget.json")
            )
            decision["fallback_chain"] = ["old"]
            failed = apply_fallback(decision, registry, failed_model="primary", reason="failure")
            self.assertEqual("ROUTING_FAILED", failed["status"])

    def test_absent_cross_provider_flag_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("primary", provider="p1"), model("other", provider="p2")))
            decision = recommend_model(
                classify_task("general research"), registry, BudgetManager(Path(temp) / "budget.json")
            )
            decision.pop("cross_provider_routing_allowed", None)
            decision["selected_model"] = "primary"
            decision["selected_provider"] = "p1"
            decision["fallback_chain"] = ["other"]
            failed = apply_fallback(decision, registry, failed_model="primary", reason="failure")
            self.assertEqual("ROUTING_FAILED", failed["status"])


if __name__ == "__main__":
    unittest.main()
