from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.check_workflow_security import check_dependabot, check_workflows


GOOD_SHA = "3" * 40
OTHER_SHA = "4" * 40


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


def codeql_workflow(actions: list[tuple[str, str, str]] | None = None) -> str:
    actions = actions or [
        ("init", GOOD_SHA, "v4.37.6"),
        ("analyze", GOOD_SHA, "v4.37.6"),
    ]
    steps = "\n".join(
        f"      - name: CodeQL {component}\n"
        f"        uses: github/codeql-action/{component}@{sha} # {version}"
        for component, sha, version in actions
    )
    return f"""name: CodeQL

on:
  pull_request:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
{steps}
"""


GOOD_DEPENDABOT = """version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
  - package-ecosystem: github-actions
    directory: "/"
    groups:
      codeql-action:
        patterns:
          - "github/codeql-action/*"
    schedule:
      interval: weekly
      day: monday
      time: "04:15"
      timezone: Asia/Taipei
    open-pull-requests-limit: 5
"""


class WorkflowSecurityTests(unittest.TestCase):
    def _check(self, payload: str) -> tuple[str, ...]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github" / "workflows"
            directory.mkdir(parents=True)
            (directory / "test.yml").write_text(payload, encoding="utf-8", newline="\n")
            (directory / "codeql.yml").write_text(
                codeql_workflow(), encoding="utf-8", newline="\n"
            )
            return check_workflows(root)

    def _check_codeql(self, payload: str) -> tuple[str, ...]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github" / "workflows"
            directory.mkdir(parents=True)
            (directory / "codeql.yml").write_text(
                payload, encoding="utf-8", newline="\n"
            )
            return check_workflows(root)

    def _check_workflow_files(self, payloads: dict[str, str]) -> tuple[str, ...]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github" / "workflows"
            directory.mkdir(parents=True)
            for name, payload in payloads.items():
                (directory / name).write_text(payload, encoding="utf-8", newline="\n")
            return check_workflows(root)

    def _check_dependabot(self, payload: str) -> tuple[str, ...]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            directory.mkdir(parents=True)
            (directory / "dependabot.yml").write_text(
                payload, encoding="utf-8", newline="\n"
            )
            return check_dependabot(root)

    def test_repository_workflows_pass(self) -> None:
        self.assertEqual(check_workflows(), ())
        self.assertEqual(check_dependabot(), ())

    def test_codeql_actions_must_move_atomically(self) -> None:
        self.assertEqual(self._check_codeql(codeql_workflow()), ())
        cases = {
            "sha-mismatch": (
                [("init", GOOD_SHA, "v4.37.6"), ("analyze", OTHER_SHA, "v4.37.6")],
                "share one SHA and version comment",
            ),
            "version-mismatch": (
                [("init", GOOD_SHA, "v4.37.6"), ("analyze", GOOD_SHA, "v4.37.5")],
                "share one SHA and version comment",
            ),
            "missing-init": (
                [("analyze", GOOD_SHA, "v4.37.6")],
                "component init must appear exactly once",
            ),
            "duplicate-analyze": (
                [
                    ("init", GOOD_SHA, "v4.37.6"),
                    ("analyze", GOOD_SHA, "v4.37.6"),
                    ("analyze", GOOD_SHA, "v4.37.6"),
                ],
                "component analyze must appear exactly once",
            ),
            "mixed-case-extra-component": (
                [
                    ("init", GOOD_SHA, "v4.37.6"),
                    ("analyze", GOOD_SHA, "v4.37.6"),
                    ("upload-sarif", OTHER_SHA, "v4.37.5"),
                ],
                "unexpected CodeQL action components",
            ),
        }
        for name, (actions, expected) in cases.items():
            with self.subTest(name=name):
                errors = self._check_codeql(codeql_workflow(actions))
                self.assertTrue(any(expected in error for error in errors), errors)
        mixed_case = codeql_workflow().replace(
            "github/codeql-action/init", "GitHub/CodeQL-Action/init"
        )
        errors = self._check_codeql(mixed_case)
        self.assertTrue(any("must use canonical case" in error for error in errors), errors)

    def test_codeql_actions_are_confined_to_canonical_workflow(self) -> None:
        extra = workflow().replace(
            f"actions/checkout@{GOOD_SHA} # v7.0.1",
            f"github/codeql-action/init@{OTHER_SHA} # v4.37.5",
        ).replace(
            "        with:\n          persist-credentials: false\n", ""
        )
        errors = self._check_workflow_files(
            {"codeql.yml": codeql_workflow(), "other.yml": extra}
        )
        self.assertTrue(any("forbidden outside" in error for error in errors), errors)

        errors = self._check_workflow_files({"CodeQL.yml": codeql_workflow()})
        self.assertTrue(any("canonical CodeQL workflow is required" in error for error in errors), errors)
        self.assertTrue(any("forbidden outside" in error for error in errors), errors)

        errors = self._check_workflow_files({"other.yml": workflow()})
        self.assertTrue(any("canonical CodeQL workflow is required" in error for error in errors), errors)

    def test_codeql_env_values_do_not_count_as_actions(self) -> None:
        payload = f"""name: CodeQL

on:
  pull_request:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    env:
      uses: github/codeql-action/init@{GOOD_SHA} # v4.37.6
    steps:
      - name: No-op
        run: echo no-codeql-ran
        env:
          uses: github/codeql-action/analyze@{GOOD_SHA} # v4.37.6
"""
        errors = self._check_codeql(payload)
        self.assertTrue(
            any("uses must be a direct step action key" in error for error in errors),
            errors,
        )

    def test_multiline_quoted_step_text_cannot_forge_codeql_actions(self) -> None:
        payload = f'''name: CodeQL

on:
  pull_request:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: "init decoy
        uses: github/codeql-action/init@{GOOD_SHA} # v4.37.6
        end"
        run: echo no-codeql-ran
      - name: "analyze decoy
        uses: github/codeql-action/analyze@{GOOD_SHA} # v4.37.6
        end"
        run: echo no-codeql-ran
'''
        errors = self._check_codeql(payload)
        self.assertTrue(
            any("multiline quoted YAML scalars are forbidden" in error for error in errors),
            errors,
        )

    def test_multiline_flow_env_cannot_forge_codeql_actions(self) -> None:
        payload = f"""name: CodeQL

on:
  pull_request:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Init decoy
        env: {{
        uses: github/codeql-action/init@{GOOD_SHA} # v4.37.6
        }}
        run: echo no-codeql-ran
      - name: Analyze decoy
        env: {{
        uses: github/codeql-action/analyze@{GOOD_SHA} # v4.37.6
        }}
        run: echo no-codeql-ran
"""
        errors = self._check_codeql(payload)
        self.assertTrue(
            any("multiline YAML flow collections are forbidden" in error for error in errors),
            errors,
        )

    def test_block_scalar_text_cannot_forge_codeql_actions(self) -> None:
        payload = f"""name: CodeQL

on:
  pull_request:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - run: |
        uses: github/codeql-action/init@{GOOD_SHA} # v4.37.6
      - run: >-
        uses: github/codeql-action/analyze@{GOOD_SHA} # v4.37.6
"""
        errors = self._check_codeql(payload)
        self.assertTrue(
            any("uses inside a block scalar are forbidden" in error for error in errors),
            errors,
        )

    def test_dependabot_keeps_codeql_actions_grouped(self) -> None:
        self.assertEqual(self._check_dependabot(GOOD_DEPENDABOT), ())
        cases = {
            "missing-group": GOOD_DEPENDABOT.replace(
                "    groups:\n      codeql-action:\n        patterns:\n"
                '          - "github/codeql-action/*"\n',
                "",
            ),
            "wrong-pattern": GOOD_DEPENDABOT.replace(
                "github/codeql-action/*", "github/codeql-action/init"
            ),
            "wrong-ecosystem": """version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    groups:
      codeql-action:
        patterns:
          - "github/codeql-action/*"
  - package-ecosystem: github-actions
    directory: "/"
""",
            "noncanonical-next-item": """version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
  - directory: "/"
    package-ecosystem: pip
    groups:
      codeql-action:
        patterns:
          - "github/codeql-action/*"
""",
            "duplicate-groups": GOOD_DEPENDABOT.replace(
                "    schedule:\n" if "    schedule:\n" in GOOD_DEPENDABOT else "",
                "",
            ).replace(
                "    groups:\n      codeql-action:\n        patterns:\n"
                '          - "github/codeql-action/*"\n',
                "    groups:\n      codeql-action:\n        patterns:\n"
                '          - "github/codeql-action/*"\n'
                "    groups: {}\n",
            ),
            "exclude-patterns": GOOD_DEPENDABOT.replace(
                '          - "github/codeql-action/*"\n',
                '          - "github/codeql-action/*"\n'
                "        exclude-patterns:\n"
                '          - "github/codeql-action/init"\n',
            ),
            "update-types": GOOD_DEPENDABOT.replace(
                '          - "github/codeql-action/*"\n',
                '          - "github/codeql-action/*"\n'
                "        update-types:\n          - patch\n",
            ),
            "security-only": GOOD_DEPENDABOT.replace(
                '          - "github/codeql-action/*"\n',
                '          - "github/codeql-action/*"\n'
                "        applies-to: security-updates\n",
            ),
            "duplicate-patterns": GOOD_DEPENDABOT.replace(
                '          - "github/codeql-action/*"\n',
                '          - "github/codeql-action/*"\n'
                "        patterns:\n"
                '          - "github/codeql-action/init"\n',
            ),
            "dash-only-extra-update": GOOD_DEPENDABOT.replace(
                "  - package-ecosystem: github-actions\n",
                "  -\n"
                "    package-ecosystem: github-actions\n"
                "    directory: \"/\"\n"
                "    target-branch: develop\n"
                "  - package-ecosystem: github-actions\n",
            ),
            "wrong-version": GOOD_DEPENDABOT.replace("version: 2", "version: 1"),
            "wrong-parent": GOOD_DEPENDABOT.replace("updates:", "not-updates:"),
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.assertTrue(self._check_dependabot(payload), name)

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
