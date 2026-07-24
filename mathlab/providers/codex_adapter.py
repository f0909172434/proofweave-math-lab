from __future__ import annotations

import subprocess
from typing import Any

from .base import ProviderAdapter
from ..errors import ConfigurationRequired


class CodexAdapter(ProviderAdapter):
    provider_id = "codex_cli"
    status = "EXPERIMENTAL_DISABLED"

    def detect(self) -> dict[str, Any]:
        command = self.command("codex")
        return {"provider": self.provider_id, "installed": bool(command), "path": command, "status": self.status}

    def build_plan(self, task_file: str, model_id: str, reasoning: str) -> dict[str, Any]:
        command = self.command("codex")
        if not command:
            raise ConfigurationRequired("Codex CLI is not installed")
        return {
            "provider": self.provider_id,
            "command": [
                command,
                "exec",
                "--model",
                model_id,
                "-c",
                f'model_reasoning_effort="{reasoning}"',
                "--json",
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

