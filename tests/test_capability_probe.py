from __future__ import annotations

import unittest

from mathlab.capability_probe import determine_mode


class CapabilityProbeTests(unittest.TestCase):
    def test_native_model_and_effort_controls_select_mode_a(self) -> None:
        mode, _ = determine_mode(
            {"native_subagents": True, "per_agent_model": True, "per_agent_reasoning_effort": True},
            {},
            {},
        )
        self.assertEqual("MODE_A_NATIVE_MULTI_MODEL", mode)

    def test_installed_cli_alone_does_not_enable_paid_subprocess(self) -> None:
        mode, _ = determine_mode(
            {},
            {"codex_cli": {"installed": True}, "claude_code": {"installed": True}},
            {},
            allow_cli_subprocess_agents=False,
        )
        self.assertEqual("MODE_E_ADVISORY_ONLY", mode)

    def test_api_credential_name_alone_does_not_enable_api_routing(self) -> None:
        mode, _ = determine_mode({}, {}, {"OPENAI_API_KEY": True}, allow_api_routing=False)
        self.assertEqual("MODE_E_ADVISORY_ONLY", mode)


if __name__ == "__main__":
    unittest.main()

