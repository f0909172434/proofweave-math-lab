from __future__ import annotations

from typing import Any

from .base import ProviderAdapter


class OpenAICompatibleAdapter(ProviderAdapter):
    provider_id = "openai_compatible"
    status = "EXPERIMENTAL_DISABLED"

    def detect(self) -> dict[str, Any]:
        configured = self.env_present("OPENAI_COMPATIBLE_BASE_URL")
        return {"provider": self.provider_id, "status": "CONFIGURED_UNVERIFIED" if configured else "DISABLED"}

    def build_plan(self, task_file: str, model_id: str, reasoning: str) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "task_file": task_file,
            "model_id": model_id,
            "reasoning": reasoning,
            "dry_run": True,
            "compatibility_unverified": True,
        }

