from __future__ import annotations

import unittest

from mathlab.reasoning_router import map_reasoning


class ReasoningRouterTests(unittest.TestCase):
    def test_unsupported_level_maps_to_nearest_native(self) -> None:
        result = map_reasoning("MAXIMUM", ["low", "medium", "high"])
        self.assertEqual("high", result["effective_reasoning_setting"])
        self.assertTrue(result["degraded"])

    def test_host_unsupported_is_not_falsely_native(self) -> None:
        result = map_reasoning("HIGH", ["high"], host_can_control=False)
        self.assertEqual("HOST_UNSUPPORTED", result["reasoning_control_method"])
        self.assertEqual("UNKNOWN", result["effective_reasoning_setting"])

    def test_prompt_loop_control_is_labeled(self) -> None:
        result = map_reasoning("HIGH", [], host_can_control=True)
        self.assertEqual("PROMPT_OR_LOOP_BASED", result["reasoning_control_method"])


if __name__ == "__main__":
    unittest.main()

