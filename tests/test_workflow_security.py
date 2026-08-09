from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.check_workflow_security import check_workflows


GOOD_SHA = "3" * 40


def workflow(
    *,
    event: str = "pull_request",
    permissions: str = "contents: read",
    checkout: str = "persist-credentials: false",
) -> str:
    return f"""name: Test

on:
  {event}:

permissions:
  {permissions}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@{GOOD_SHA} # v7.0.1
        with:
          {checkout}
"""


class WorkflowSecurityTests(unittest.TestCase):
    def _check(self, payload: str) -> tuple[str, ...]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github" / "workflows"
            directory.mkdir(parents=True)
            (directory / "test.yml").write_text(payload, encoding="utf-8", newline="\n")
            return check_workflows(root)

    def test_repository_workflows_pass(self) -> None:
        self.assertEqual(check_workflows(), ())

    def test_policy_mutations_fail_closed(self) -> None:
        cases = {
            "unpinned": (
                workflow().replace(GOOD_SHA, "v7"),
                "action ref must be a 40-hex SHA",
            ),
            "missing-version-comment": (
                workflow().replace(" # v7.0.1", ""),
                "external action needs a full pin and version comment",
            ),
            "pull-request-target": (
                workflow(event="pull_request_target"),
                "pull_request_target is forbidden",
            ),
            "top-level-write": (
                workflow(permissions="contents: write"),
                "top-level permissions must be exactly contents: read",
            ),
            "write-all-inline-comment": (
                workflow().replace("contents: read", "write-all # bypass"),
                "top-level permissions must be exactly contents: read",
            ),
            "checkout-credentials": (
                workflow(checkout="fetch-depth: 0"),
                "exactly one persist-credentials: false",
            ),
        }
        for name, (payload, expected) in cases.items():
            with self.subTest(name=name):
                self.assertTrue(any(expected in error for error in self._check(payload)), name)

    def test_checkout_setting_under_env_does_not_count(self) -> None:
        payload = workflow().replace(
            "        with:\n          persist-credentials: false",
            "        env:\n          persist-credentials: false",
        )
        errors = self._check(payload)
        self.assertTrue(
            any("checkout must have exactly one with mapping" in error for error in errors)
        )

    def test_job_write_permissions_fail_closed(self) -> None:
        payloads = {
            "ordinary-write": workflow().replace(
                "    runs-on: ubuntu-latest",
                "    permissions:\n      issues: write\n    runs-on: ubuntu-latest",
            ),
            "write-all-comment": workflow().replace(
                "    runs-on: ubuntu-latest",
                "    permissions: write-all # bypass\n    runs-on: ubuntu-latest",
            ),
        }
        for name, payload in payloads.items():
            with self.subTest(name=name):
                errors = self._check(payload)
                self.assertTrue(
                    any(
                        "forbidden permission" in error
                        or "permissions must be a block mapping or {}" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_equivalent_yaml_security_bypasses_fail_closed(self) -> None:
        cases = {
            "quoted-event": (
                workflow().replace("  pull_request:", "  'pull_request_target':"),
                "pull_request_target is forbidden",
            ),
            "flow-event": (
                workflow().replace("on:\n  pull_request:\n", "on: [pull_request_target]\n"),
                "pull_request_target is forbidden",
            ),
            "checkout-case": (
                workflow(checkout="fetch-depth: 0").replace(
                    "actions/checkout", "Actions/Checkout"
                ),
                "checkout action name must use canonical case",
            ),
            "quoted-job-permissions": (
                workflow().replace(
                    "    runs-on: ubuntu-latest",
                    '    "permissions":\n      issues: write\n    runs-on: ubuntu-latest',
                ),
                "quoted YAML mapping keys are forbidden",
            ),
            "duplicate-persist": (
                workflow(
                    checkout="persist-credentials: false\n          persist-credentials: true"
                ),
                "exactly one persist-credentials: false",
            ),
            "duplicate-with": (
                workflow().replace(
                    "        with:\n          persist-credentials: false",
                    "        with:\n          persist-credentials: false\n"
                    "        with:\n          persist-credentials: true",
                ),
                "exactly one with mapping",
            ),
        }
        for name, (payload, expected) in cases.items():
            with self.subTest(name=name):
                errors = self._check(payload)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_escaped_or_complex_yaml_keys_fail_closed(self) -> None:
        cases = {
            "escaped-event-key": (
                workflow().replace(
                    "  pull_request:", '  "pull_request\\u005ftarget":'
                ),
                "quoted YAML mapping keys are forbidden",
            ),
            "escaped-flow-event": (
                workflow().replace(
                    "on:\n  pull_request:\n", 'on: ["pull_request\\u005ftarget"]\n'
                ),
                "flow or scalar event declarations are forbidden",
            ),
            "quoted-sequence-uses": (
                workflow().replace(
                    "        uses: actions/checkout",
                    '        - "uses": actions/checkout',
                ),
                "quoted YAML mapping keys are forbidden",
            ),
            "escaped-sequence-uses": (
                workflow().replace(
                    "        uses: actions/checkout",
                    '        - "us\\u0065s": actions/checkout',
                ),
                "quoted YAML mapping keys are forbidden",
            ),
            "complex-permissions-key": (
                workflow().replace("permissions:", "? permissions\n: {}", 1),
                "complex YAML mapping keys are forbidden",
            ),
            "flow-explicit-permissions-key": (
                workflow().replace(
                    "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                    "  test: {? permissions: {issues: write}, "
                    'runs-on: ubuntu-latest, steps: [{run: "echo ok"}]}\n'
                    "  inert:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                ),
                "complex YAML mapping keys are forbidden",
            ),
            "flow-explicit-quoted-permissions-key": (
                workflow().replace(
                    "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                    '  test: {? "permissions": {issues: write}, '
                    'runs-on: ubuntu-latest, steps: [{run: "echo ok"}]}\n'
                    "  inert:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                ),
                "complex YAML mapping keys are forbidden",
            ),
            "flow-explicit-anchored-permissions-key": (
                workflow().replace(
                    "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                    "  test: {? &0 permissions: {issues: write}, "
                    'runs-on: ubuntu-latest, steps: [{run: "echo ok"}]}\n'
                    "  inert:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                ),
                "complex YAML mapping keys are forbidden",
            ),
            "compact-flow-explicit-permissions-key": (
                workflow().replace(
                    "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                    "  test: {?permissions: {issues: write}, "
                    'runs-on: ubuntu-latest, steps: [{run: "echo ok"}]}\n'
                    "  inert:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                ),
                "complex YAML mapping keys are forbidden",
            ),
            "compact-flow-explicit-spaced-uses-key": (
                workflow().replace(
                    "    steps:\n      - name: Checkout\n"
                    f"        uses: actions/checkout@{GOOD_SHA} # v7.0.1\n"
                    "        with:\n          persist-credentials: false",
                    "    steps: [{?uses : actions/checkout@v7}]",
                ),
                "complex YAML mapping keys are forbidden",
            ),
            "tab-indentation": (
                workflow().replace("  test:", "\ttest:"),
                "workflow must not contain tab characters",
            ),
            "spaced-uses": (
                workflow().replace("uses: actions/checkout", "uses : actions/checkout"),
                "security-sensitive YAML keys must not contain colon spacing",
            ),
            "spaced-sequence-uses": (
                workflow().replace("uses: actions/checkout", "- uses : actions/checkout"),
                "security-sensitive YAML keys must not contain colon spacing",
            ),
            "spaced-duplicate-with": (
                workflow().replace(
                    "        with:\n          persist-credentials: false",
                    "        with:\n          persist-credentials: false\n"
                    "        with :\n          persist-credentials: true",
                ),
                "security-sensitive YAML keys must not contain colon spacing",
            ),
            "spaced-duplicate-persist": (
                workflow(
                    checkout="persist-credentials: false\n          persist-credentials : true"
                ),
                "security-sensitive YAML keys must not contain colon spacing",
            ),
            "tagged-permissions": (
                workflow().replace(
                    "permissions:\n  contents: read",
                    "!!str permissions:\n  contents: read\n  issues: write",
                ),
                "YAML tags are forbidden",
            ),
            "tagged-events": (
                workflow().replace("on:", "!!str on:", 1).replace(
                    "  pull_request:", "  pull_request_target:"
                ),
                "YAML tags are forbidden",
            ),
            "non-specific-tagged-permissions": (
                workflow().replace(
                    "    runs-on: ubuntu-latest",
                    "    ! permissions:\n      issues: write\n    runs-on: ubuntu-latest",
                ),
                "YAML tags are forbidden",
            ),
            "non-specific-tagged-events": (
                workflow().replace("on:", "! on:", 1).replace(
                    "  pull_request:", "  pull_request_target:"
                ),
                "YAML tags are forbidden",
            ),
            "non-specific-tagged-uses": (
                workflow().replace(
                    "uses: actions/checkout", "! uses : actions/checkout"
                ),
                "YAML tags are forbidden",
            ),
            "numeric-anchor": (
                workflow().replace("jobs:", "defaults: &0 {}\n\njobs:", 1),
                "YAML anchors, aliases, and merge keys are forbidden",
            ),
            "flow-map-anchor": (
                workflow().replace(
                    "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                    "  test: {&0 permissions: {issues: write}, "
                    'runs-on: ubuntu-latest, steps: [{run: "echo ok"}]}\n'
                    "  inert:\n    runs-on: ubuntu-latest\n    steps:\n"
                    "      - name: Checkout\n",
                ),
                "YAML anchors, aliases, and merge keys are forbidden",
            ),
            "flow-list-tag": (
                workflow().replace(
                    "    runs-on: ubuntu-latest",
                    "    env: [!!str safe]\n    runs-on: ubuntu-latest",
                ),
                "YAML tags are forbidden",
            ),
            "local-action": (
                workflow().replace(
                    f"actions/checkout@{GOOD_SHA} # v7.0.1",
                    "./.github/actions/unsafe",
                ),
                "local actions and reusable workflows are forbidden",
            ),
        }
        for name, (payload, expected) in cases.items():
            with self.subTest(name=name):
                errors = self._check(payload)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_yaml_merge_indirection_is_rejected(self) -> None:
        payload = workflow().replace(
            "jobs:\n",
            "defaults: &dangerous\n  permissions:\n    issues: write\n\njobs:\n",
        ).replace(
            "    runs-on: ubuntu-latest",
            "    <<: *dangerous\n    runs-on: ubuntu-latest",
        )
        errors = self._check(payload)
        self.assertTrue(
            any("YAML anchors, aliases, and merge keys are forbidden" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
