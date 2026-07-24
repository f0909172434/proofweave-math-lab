from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import load_json
from .schemas import require_valid


AVAILABILITY = {
    "VERIFIED_AVAILABLE",
    "CONFIGURED_UNVERIFIED",
    "PUBLICLY_LISTED",
    "UNAVAILABLE",
    "UNKNOWN",
    "DEPRECATED",
}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class ModelRegistry:
    def __init__(self, inventory: dict[str, Any]):
        self.inventory = deepcopy(inventory)
        self.version = inventory.get("inventory_version", "UNKNOWN")
        self._models: dict[str, dict[str, Any]] = {}
        for model in inventory.get("models", []):
            model_id = model.get("model_id")
            if not model_id:
                raise ValidationError("Model inventory entry is missing model_id")
            if model_id in self._models:
                raise ValidationError(f"Duplicate model_id: {model_id}")
            if model.get("availability_status") not in AVAILABILITY:
                raise ValidationError(f"Invalid availability for {model_id}")
            require_valid(model, "model_capability", SCHEMA_ROOT)
            self._models[model_id] = deepcopy(model)

    @classmethod
    def from_path(cls, path: Path) -> "ModelRegistry":
        inventory = load_json(path, default={}) or {}
        return cls(inventory)

    def get(self, model_id: str) -> dict[str, Any]:
        if model_id not in self._models:
            raise ValidationError(f"Unknown model: {model_id}")
        return deepcopy(self._models[model_id])

    def all(self) -> list[dict[str, Any]]:
        return [deepcopy(self._models[key]) for key in sorted(self._models)]

    def executable(
        self,
        *,
        allow_configured_unverified: bool = False,
        forbidden_providers: set[str] | None = None,
        forbidden_models: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        allowed = {"VERIFIED_AVAILABLE"}
        if allow_configured_unverified:
            allowed.add("CONFIGURED_UNVERIFIED")
        providers = forbidden_providers or set()
        models = forbidden_models or set()
        return [
            deepcopy(model)
            for model in self._models.values()
            if model.get("availability_status") in allowed
            and model.get("deprecation_status") != "DEPRECATED"
            and model.get("provider") not in providers
            and model.get("model_id") not in models
        ]
