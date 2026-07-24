from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.benchmark_runner import BenchmarkRunner
from mathlab.budget_manager import BudgetManager
from mathlab.errors import ConfigurationRequired
from mathlab.model_registry import ModelRegistry
from mathlab.model_router import recommend_model
from mathlab.task_classifier import classify_task
from tests.common import inventory, model


class AdvisoryModeTests(unittest.TestCase):
    def test_all_providers_unavailable_enters_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = ModelRegistry(inventory(model("public", status="PUBLICLY_LISTED")))
            result = recommend_model(classify_task("general research"), registry, BudgetManager(Path(temp) / "budget.json"))
            self.assertEqual("ADVISORY_ONLY", result["status"])

    def test_live_benchmark_requires_explicit_paid_authorization_and_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runner = BenchmarkRunner(Path(temp))
            with self.assertRaises(ConfigurationRequired):
                runner.run_model("m1", allow_paid_probe=False)
            with self.assertRaises(ConfigurationRequired):
                runner.run_model("m1", allow_paid_probe=True)

    def test_insufficient_benchmark_data_yields_no_fake_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = BenchmarkRunner(root)
            runner.record(
                {
                    "run_id": "run-1",
                    "case_id": "case-1",
                    "dataset_version": "test-v1",
                    "visibility": "PUBLIC",
                    "category": "proof_gap_detection",
                    "provider": "test",
                    "model_id": "m1",
                    "model_snapshot": None,
                    "reasoning_setting": "high",
                    "prompt_version": "test-v1",
                    "correct": True,
                    "false_acceptance": False,
                    "false_rejection": False,
                    "estimated_cost": None,
                    "actual_cost": None,
                    "latency_ms": 1,
                }
            )
            summary = runner.summarize(minimum_cases=20)
            self.assertEqual("INSUFFICIENT_DATA", summary["ranking_status"])
            self.assertEqual([], summary["ranking"])


if __name__ == "__main__":
    unittest.main()
