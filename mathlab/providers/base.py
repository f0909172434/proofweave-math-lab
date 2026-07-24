from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from typing import Any

from ..errors import ConfigurationRequired


class ProviderAdapter(ABC):
    provider_id = "base"
    status = "UNSUPPORTED"

    @abstractmethod
    def detect(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_plan(self, task_file: str, model_id: str, reasoning: str) -> dict[str, Any]:
        raise NotImplementedError

    def execute(self, plan: dict[str, Any], *, explicitly_authorized: bool = False) -> Any:
        if not explicitly_authorized:
            raise ConfigurationRequired(
                f"{self.provider_id} execution requires explicit authorization; dry-run plan was produced instead."
            )
        raise ConfigurationRequired(f"{self.provider_id} live execution is not implemented in this adapter")

    @staticmethod
    def command(name: str) -> str | None:
        return shutil.which(f"{name}.cmd") or shutil.which(name)

    @staticmethod
    def env_present(name: str) -> bool:
        return bool(os.environ.get(name))

