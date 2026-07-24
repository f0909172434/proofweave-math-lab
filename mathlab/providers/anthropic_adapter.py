from __future__ import annotations

from typing import Any

from .base import ProviderAdapter


class AnthropicAdapter(ProviderAdapter):
    provider_id = "anthropic_api"
    status = "CONFIGURED_UNVERIFIED_OR_DISABLED"

    def detect(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "credential_present": self.env_present("ANTHROPIC_API_KEY"),
            "status": "CONFIGURED_UNVERIFIED" if self.env_present("ANTHROPIC_API_KEY") else "DISABLED",
        }

    def build_plan(self, task_file: str, model_id: str, reasoning: str) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "endpoint": "Messages API (not invoked)",
            "task_file": task_file,
            "model_id": model_id,
            "reasoning": reasoning,
            "dry_run": True,
            "may_charge": True,
        }

