from __future__ import annotations

import unittest

from mathlab.errors import ValidationError
from mathlab.model_registry import ModelRegistry
from tests.common import inventory, model


class ModelRegistryTests(unittest.TestCase):
    def test_nonexistent_model_is_not_available(self) -> None:
        registry = ModelRegistry(inventory(model("known")))
        with self.assertRaises(ValidationError):
            registry.get("missing")

    def test_publicly_listed_is_not_automatically_executable(self) -> None:
        registry = ModelRegistry(inventory(model("public", status="PUBLICLY_LISTED")))
        self.assertEqual([], registry.executable())

    def test_configured_unverified_requires_explicit_permission(self) -> None:
        registry = ModelRegistry(inventory(model("maybe", status="CONFIGURED_UNVERIFIED")))
        self.assertEqual([], registry.executable())
        self.assertEqual(["maybe"], [row["model_id"] for row in registry.executable(allow_configured_unverified=True)])

    def test_deprecated_model_is_excluded(self) -> None:
        registry = ModelRegistry(inventory(model("old", deprecated=True), model("new")))
        self.assertEqual(["new"], [row["model_id"] for row in registry.executable()])


if __name__ == "__main__":
    unittest.main()

