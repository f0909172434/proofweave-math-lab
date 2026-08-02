from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_repository_baseline import (
    check_local_markdown_links,
    check_no_user_specific_runtime_paths,
    check_public_contracts,
    check_required_files,
    check_workflow_pins,
)


ROOT = Path(__file__).resolve().parents[1]


class RepositoryBaselineTests(unittest.TestCase):
    def test_required_public_files_exist(self) -> None:
        self.assertEqual([], check_required_files(ROOT))

    def test_public_markdown_links_resolve(self) -> None:
        self.assertEqual([], check_local_markdown_links(ROOT))

    def test_workflow_actions_are_immutably_pinned(self) -> None:
        self.assertEqual([], check_workflow_pins(ROOT))

    def test_tracked_files_have_no_user_specific_codex_python_path(self) -> None:
        self.assertEqual([], check_no_user_specific_runtime_paths(ROOT))

    def test_public_security_and_ci_contracts(self) -> None:
        self.assertEqual([], check_public_contracts(ROOT))


if __name__ == "__main__":
    unittest.main()
