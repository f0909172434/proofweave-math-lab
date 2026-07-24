from __future__ import annotations

import subprocess
from typing import Any

from .base import ProviderAdapter
from ..errors import ConfigurationRequired


class ClaudeCodeAdapter(ProviderAdapter):
    provider_id = "claude_code"
    status = "EXPERIMENTAL_DISABLED"

    def detect(self) -> dict[str, Any]:
        command = self.command("claude")
        return {"provider": self.provider_id, "installed": bool(command), "path": command, "status": self.status}

    def build_plan(self, task_file: str, model_id: str, reasoning: str) -> dict[str, Any]:
        command = self.command("claude")
        if not command:
            raise ConfigurationRequired("Claude Code is not installed")
        return {
            "provider": self.provider_id,
            "command": [
                command,
                "--print",
                "--model",
                model_id,
                "--effort",
                reasoning,
                "--output-format",
                "json",
                f"Read and execute the bounded task file: {task_file}",
            ],
            "dry_run": True,
            "may_consume_quota": True,
        }

    def execute(self, plan: dict[str, Any], *, explicitly_authorized: bool = False) -> Any:
        if not explicitly_authorized:
            return super().execute(plan, explicitly_authorized=False)
        completed = subprocess.run(plan["command"], capture_output=True, text=True, timeout=1800, check=False)
        return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}

