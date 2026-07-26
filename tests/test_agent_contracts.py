from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.generate_native_adapters import ROLES


ROOT = Path(__file__).resolve().parents[1]
SHARED_DOCS = (
    "docs/agent_contracts.md",
    "docs/mathematical_quality_standard.md",
    "docs/model_routing_guide.md",
)
ROLE_SECTIONS = ("Mission", "Scope", "Role-specific duties")
LEGACY_SHARED_SECTIONS = (
    "Inputs",
    "Preconditions",
    "Allowed tools",
    "Forbidden actions",
    "Required procedure",
    "Output contract",
    "Quality checklist",
    "Stop conditions",
    "Escalation conditions",
    "Model routing profile",
    "Reasoning profile",
    "Verification requirements",
    "Memory access policy",
)


class AgentContractTests(unittest.TestCase):
    def test_roles_compose_shared_contract_without_copying_it(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                text = (ROOT / "agents" / f"{role}.md").read_text(encoding="utf-8")
                self.assertLessEqual(len(text), 1_500)
                self.assertTrue(text.startswith(f"# {role}\n"))
                for path in SHARED_DOCS:
                    self.assertIn(f"`{path}`", text)
                for section in ROLE_SECTIONS:
                    self.assertEqual(1, len(re.findall(rf"^## {re.escape(section)}$", text, re.MULTILINE)))
                for section in LEGACY_SHARED_SECTIONS:
                    self.assertNotRegex(text, rf"(?m)^## {re.escape(section)}$")

    def test_shared_contract_keeps_mandatory_execution_gates(self) -> None:
        text = (ROOT / "docs" / "agent_contracts.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for section in (
            "Composition and authority",
            "Preconditions and execution discipline",
            "Universal contract",
            "Memory access",
            "Canonical result shape",
            "Verification and quality",
            "Routing and budget",
            "Stop and escalation",
        ):
            self.assertIn(f"## {section}", text)
        for requirement in (
            "Only an independent theorem verifier may promote",
            "never self-verification",
            "Budget exhaustion cannot weaken truth or verification gates",
            "record the actual provider/model/version",
            "present numerical evidence as proof",
            "overwrite evidence",
            "Access is read-only unless the task grants a bounded write scope",
            "stop immediately if proceeding would require claiming proof from experiments",
        ):
            self.assertIn(requirement, normalized)

    def test_native_adapters_use_the_compact_pointer(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                for path in (
                    ROOT / ".codex" / "agents" / f"{role}.toml",
                    ROOT / ".claude" / "agents" / f"{role}.md",
                ):
                    text = path.read_text(encoding="utf-8")
                    self.assertIn(f"agents/{role}.md", text)
                    self.assertIn("mandatory shared-contract references", text)
                    self.assertNotIn("Also read docs/agent_contracts.md", text)


if __name__ == "__main__":
    unittest.main()
