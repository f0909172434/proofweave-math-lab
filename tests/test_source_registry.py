from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.errors import ValidationError
from mathlab.source_registry import SourceRegistry


class SourceRegistryTests(unittest.TestCase):
    def test_missing_required_fields_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = SourceRegistry(Path(temp) / "sources.jsonl")
            with self.assertRaises(ValidationError):
                registry.add({"source_id": "s1", "title": "Incomplete", "status": "FOUND"})

    def test_found_opened_verified_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry = SourceRegistry(Path(temp) / "sources.jsonl")
            registry.add({
                "source_id": "s1", "title": "Official source", "authors_or_organization": "Org",
                "publication_date": "2026", "url": "https://example.org/source", "accessed_at": "2026-07-24T00:00:00Z",
                "source_type": "OFFICIAL_DOCUMENTATION", "trust_level": "PRIMARY_HIGH",
                "project_use": "test", "exact_claim_supported": "", "status": "FOUND"
            })
            opened = registry.transition("s1", "OPENED", actor="reader")
            verified = registry.transition("s1", "VERIFIED", actor="auditor", exact_claim_supported="Exact support")
            self.assertEqual("OPENED", opened["status"])
            self.assertEqual("VERIFIED", verified["status"])


if __name__ == "__main__":
    unittest.main()

