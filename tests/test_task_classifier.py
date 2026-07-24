from __future__ import annotations

import unittest

from mathlab.task_classifier import classify_task


class TaskClassifierTests(unittest.TestCase):
    def test_high_risk_theorem_is_frontier(self) -> None:
        result = classify_task("For all parameters, find a counterexample to the main theorem")
        self.assertEqual("FRONTIER", result["recommended_capability_tier"])
        self.assertGreaterEqual(result["risk_score"], 80)

    def test_formatting_is_low_risk_utility(self) -> None:
        result = classify_task("Fix a Markdown heading format")
        self.assertEqual("UTILITY", result["recommended_capability_tier"])
        self.assertEqual("LOW", result["recommended_reasoning_profile"])

    def test_prompt_length_is_not_only_complexity_signal(self) -> None:
        short = classify_task("Audit an asymptotic limit exchange")
        long = classify_task("format " + "x " * 1000)
        self.assertGreater(short["risk_score"], long["risk_score"])


if __name__ == "__main__":
    unittest.main()

