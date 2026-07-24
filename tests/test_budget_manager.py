from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.budget_manager import BudgetManager
from tests.common import write_json


class BudgetManagerTests(unittest.TestCase):
    def test_frontier_limit_blocks_without_weakening_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "budget.json"
            write_json(path, {"mode": "BALANCED", "maximum_frontier_calls": 0})
            result = BudgetManager(path).authorize(estimated_cost=None, capability_tier="FRONTIER")
            self.assertEqual("BLOCKED_BY_BUDGET", result["status"])

    def test_paid_probe_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = BudgetManager(Path(temp) / "budget.json").authorize(
                estimated_cost=0.0, capability_tier="STANDARD", paid_probe=True
            )
            self.assertEqual("BLOCKED_BY_BUDGET", result["status"])

    def test_escalation_count_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "budget.json"
            write_json(path, {"mode": "BALANCED", "reasoning_escalations": 2, "maximum_reasoning_escalations": 2})
            self.assertFalse(BudgetManager(path).allow_escalation("reasoning"))


if __name__ == "__main__":
    unittest.main()

