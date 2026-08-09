"""Fail-closed static checks for GitHub Actions workflow policy."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = Path(".github/workflows")
DEPENDABOT_PATH = Path(".github/dependabot.yml")
PIN = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^v\d+(?:\.\d+){0,2}(?:[-+][A-Za-z0-9_.-]+)?$")
USES = re.compile(r"^(?P<indent>\s*)uses:\s*(?P<spec>\S+)\s+#\s+(?P<version>\S+)\s*$")
KEY_VALUE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>\S(?:.*\S)?)?$")
JOB_WRITE_ALLOWLIST = {
    (".github/workflows/codeql.yml", "analyze"): {
        "contents": "read",
        "security-events": "write",
    },
    (".github/workflows/evidence.yml", "release"): {
        "contents": "write",
        "id-token": "write",
        "attestations": "write",
    },
}
EXPLICIT_EMPTY_JOB_PERMISSIONS = {
    (".github/workflows/ci.yml", "gate"),
}
SENSITIVE_KEYS = {
    "on",
    "permissions",
    "uses",
    "with",
    "persist-credentials",
    "pull_request_target",
}
DEPENDABOT_GITHUB_ACTIONS_BLOCK = """  - package-ecosystem: github-actions
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
    open-pull-requests-limit: 5"""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _without_comment(line: str) -> str:
    """Remove a YAML comment without treating quoted hashes as comments."""

    single = False
    double = False
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
            continue
        if character == "\\" and double:
            escaped = True
            continue
        if character == "'" and not double:
            single = not single
            continue
        if character == '"' and not single:
            double = not double
            continue
        if character == "#" and not single and not double:
            return line[:index].rstrip()
    return line.rstrip()


def _has_unclosed_quote(line: str) -> bool:
    single = False
    double = False
    escaped = False
    index = 0
    while index < len(line):
        character = line[index]
        if escaped:
            escaped = False
        elif character == "\\" and double:
            escaped = True
        elif character == "'" and not double:
            if single and index + 1 < len(line) and line[index + 1] == "'":
                index += 1
            else:
                single = not single
        elif character == '"' and not single:
            double = not double
        elif character == "#" and not single and not double:
            break
        index += 1
    return single or double


def _without_quoted_text(line: str) -> str:
    """Mask quoted YAML text so anchor checks ignore cron and shell strings."""

    semantic = _without_comment(line)
    output = list(semantic)
    single = False
    double = False
    escaped = False
    for index, character in enumerate(semantic):
        if escaped:
            output[index] = " "
            escaped = False
            continue
        if character == "\\" and double:
            output[index] = " "
            escaped = True
            continue
        if character == "'" and not double:
            single = not single
            output[index] = " "
            continue
        if character == '"' and not single:
            double = not double
            output[index] = " "
            continue
        if single or double:
            output[index] = " "
    return "".join(output)


def _opens_multiline_flow_collection(line: str) -> bool:
    """Reject flow collections whose lexical scope crosses a physical line."""

    stack: list[str] = []
    pairs = {"}": "{", "]": "["}
    for character in _without_quoted_text(line):
        if character in "{[":
            stack.append(character)
        elif character in "}]" and stack and stack[-1] == pairs[character]:
            stack.pop()
    return bool(stack)


def _is_block_scalar_header(line: str) -> bool:
    return re.search(r":\s*[|>][0-9+-]*\s*$", _without_comment(line)) is not None


def _block_scalar_content_indices(lines: list[str]) -> set[int]:
    content: set[int] = set()
    block_scalar_indent: int | None = None
    for index, raw_line in enumerate(lines):
        semantic = _without_comment(raw_line)
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if block_scalar_indent is not None:
            if indentation > block_scalar_indent:
                content.add(index)
                continue
            block_scalar_indent = None
        if _is_block_scalar_header(raw_line):
            block_scalar_indent = indentation
    return content


def _syntax_policy_errors(lines: list[str], relative: str) -> list[str]:
    errors: list[str] = []
    in_events = False
    block_scalar_content = _block_scalar_content_indices(lines)
    for index, raw_line in enumerate(lines):
        if index in block_scalar_content:
            continue
        if _has_unclosed_quote(raw_line):
            errors.append(
                f"{relative}:{index + 1}: multiline quoted YAML scalars are forbidden"
            )
        semantic = _without_comment(raw_line)
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if _opens_multiline_flow_collection(raw_line):
            errors.append(
                f"{relative}:{index + 1}: multiline YAML flow collections are forbidden"
            )
        stripped = semantic.strip()
        mapping_view = re.sub(r"^-\s*", "", stripped, count=1)

        quoted_key = re.search(r"(?:^|[{,])\s*[\"'][^\"']+[\"']\s*:", mapping_view)
        if quoted_key:
            errors.append(
                f"{relative}:{index + 1}: quoted YAML mapping keys are forbidden"
            )
        if mapping_view.startswith("?") or re.search(
            r"(?:^|[{,])\s*\?", mapping_view
        ):
            errors.append(
                f"{relative}:{index + 1}: complex YAML mapping keys are forbidden"
            )

        plain_key = re.match(r"^(?P<key>[A-Za-z0-9_-]+)\s*:", mapping_view)
        if plain_key:
            key = plain_key.group("key")
            if key.casefold() in SENSITIVE_KEYS and key not in SENSITIVE_KEYS:
                errors.append(
                    f"{relative}:{index + 1}: security-sensitive YAML keys must use canonical case"
                )
            if key.casefold() in SENSITIVE_KEYS and not mapping_view.startswith(f"{key}:"):
                errors.append(
                    f"{relative}:{index + 1}: security-sensitive YAML keys must not contain colon spacing"
                )

        if re.search(
            r"(?:^|[{,])\s*(?:permissions|uses|with|persist-credentials)\s*:",
            mapping_view,
            re.IGNORECASE,
        ) and not re.match(
            r"^(?:permissions|uses|with|persist-credentials)\s*:",
            mapping_view,
        ):
            errors.append(
                f"{relative}:{index + 1}: inline security-sensitive mappings are forbidden"
            )

        unquoted = _without_quoted_text(raw_line)
        unquoted_mapping_view = re.sub(r"^-\s*", "", unquoted.strip(), count=1)
        if re.search(r"(?:^\s*|[\[{:,-]\s*)!", unquoted_mapping_view):
            errors.append(f"{relative}:{index + 1}: YAML tags are forbidden")
        if re.search(r"^\s*<<\s*:", unquoted) or re.search(
            r"(?:^\s*|[\[{:,-]\s*)(?:&(?!&)|\*(?!\*))[^\s\[\]{},]+", unquoted
        ):
            errors.append(
                f"{relative}:{index + 1}: YAML anchors, aliases, and merge keys are forbidden"
            )

        if indentation == 0:
            on_match = re.match(r"^[\"']?on[\"']?\s*:(?P<value>.*)$", stripped)
            in_events = on_match is not None
            if on_match:
                event_value = on_match.group("value").strip()
                if "pull_request_target" in event_value:
                    errors.append(f"{relative}:{index + 1}: pull_request_target is forbidden")
                if event_value:
                    errors.append(
                        f"{relative}:{index + 1}: flow or scalar event declarations are forbidden"
                    )
            continue
        if in_events and "pull_request_target" in stripped:
            errors.append(f"{relative}:{index + 1}: pull_request_target is forbidden")
    return errors


def _permission_mapping(
    lines: list[str], start: int, parent_indent: int, relative: str
) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    header = _without_comment(lines[start]).strip()
    rest = header.partition(":")[2].strip()
    if rest:
        if rest == "{}":
            return {}, errors
        return {}, [f"{relative}:{start + 1}: permissions must be a block mapping or {{}}"]

    mapping: dict[str, str] = {}
    for index in range(start + 1, len(lines)):
        semantic = _without_comment(lines[index])
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if indentation <= parent_indent:
            break
        if indentation != parent_indent + 2:
            errors.append(
                f"{relative}:{index + 1}: permission entries must be direct children"
            )
            continue
        match = KEY_VALUE.fullmatch(semantic.strip())
        if match is None or match.group("value") is None:
            errors.append(f"{relative}:{index + 1}: invalid permission entry")
            continue
        key = match.group("key")
        value = match.group("value")
        if key in mapping:
            errors.append(f"{relative}:{index + 1}: duplicate permission {key}")
        mapping[key] = value
    return mapping, errors


def _check_permissions(lines: list[str], relative: str) -> list[str]:
    errors: list[str] = []
    top_level: list[tuple[int, dict[str, str]]] = []
    job_permissions: dict[str, tuple[int, dict[str, str]]] = {}
    in_jobs = False
    current_job: str | None = None

    for index, raw_line in enumerate(lines):
        line = _without_comment(raw_line)
        if not line.strip():
            continue
        indentation = _indent(line)
        stripped = line.strip()
        if indentation == 0:
            in_jobs = stripped == "jobs:"
            current_job = None
        elif in_jobs and indentation == 2:
            match = KEY_VALUE.fullmatch(stripped)
            current_job = match.group("key") if match and match.group("value") is None else None

        if not re.match(r"^permissions\s*:", stripped):
            continue
        mapping, mapping_errors = _permission_mapping(lines, index, indentation, relative)
        errors.extend(mapping_errors)
        if indentation == 0:
            top_level.append((index, mapping))
        elif in_jobs and indentation == 4 and current_job is not None:
            if current_job in job_permissions:
                errors.append(f"{relative}:{index + 1}: duplicate permissions block for job {current_job}")
            job_permissions[current_job] = (index, mapping)
        else:
            errors.append(f"{relative}:{index + 1}: permissions block is in an unsupported context")

    if len(top_level) != 1:
        errors.append(f"{relative}: expected exactly one top-level permissions block")
    elif top_level[0][1] != {"contents": "read"}:
        errors.append(f"{relative}: top-level permissions must be exactly contents: read")

    for job, (index, mapping) in job_permissions.items():
        context = (relative, job)
        expected = JOB_WRITE_ALLOWLIST.get(context)
        if expected is not None:
            if mapping != expected:
                errors.append(
                    f"{relative}:{index + 1}: job {job} permissions must match the write allowlist"
                )
            continue
        if context in EXPLICIT_EMPTY_JOB_PERMISSIONS:
            if mapping:
                errors.append(
                    f"{relative}:{index + 1}: job {job} permissions must be explicitly empty"
                )
            continue
        for key, value in mapping.items():
            if value != "read":
                errors.append(
                    f"{relative}:{index + 1}: job {job} has forbidden permission {key}: {value}"
                )

    for (expected_relative, job), _expected in JOB_WRITE_ALLOWLIST.items():
        if expected_relative == relative and job not in job_permissions:
            errors.append(f"{relative}: job {job} is missing its explicit permissions block")
    for expected_relative, job in EXPLICIT_EMPTY_JOB_PERMISSIONS:
        if expected_relative == relative and job not in job_permissions:
            errors.append(f"{relative}: job {job} must declare permissions: {{}}")
    return errors


def _checkout_persistence_errors(
    lines: list[str], uses_index: int, uses_indent: int, relative: str
) -> list[str]:
    step_indent = max(0, uses_indent - 2)
    with_indices: list[int] = []
    for index in range(uses_index + 1, len(lines)):
        semantic = _without_comment(lines[index])
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if indentation <= step_indent:
            break
        if indentation == uses_indent and semantic.strip() == "with:":
            with_indices.append(index)
    if len(with_indices) != 1:
        return [
            f"{relative}:{uses_index + 1}: checkout must have exactly one with mapping"
        ]

    values: list[str | None] = []
    for index in range(with_indices[0] + 1, len(lines)):
        semantic = _without_comment(lines[index])
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if indentation <= uses_indent:
            break
        if indentation != uses_indent + 2:
            continue
        match = KEY_VALUE.fullmatch(semantic.strip())
        if match and match.group("key") == "persist-credentials":
            values.append(match.group("value"))
    if len(values) != 1 or values[0] != "false":
        return [
            f"{relative}:{uses_index + 1}: checkout with must contain exactly one persist-credentials: false"
        ]
    return []


def _action_step_context_errors(
    lines: list[str], uses_index: int, uses_indent: int, relative: str
) -> list[str]:
    if uses_indent != 8:
        return [f"{relative}:{uses_index + 1}: uses must be a direct step action key"]
    step_index: int | None = None
    for index in range(uses_index - 1, -1, -1):
        semantic = _without_comment(lines[index])
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if indentation <= 6:
            if indentation == 6 and semantic.strip().startswith("- "):
                step_index = index
            break
    if step_index is None:
        return [f"{relative}:{uses_index + 1}: uses must belong to a sequence step"]
    for index in range(step_index - 1, -1, -1):
        semantic = _without_comment(lines[index])
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
        if indentation <= 4:
            if indentation == 4 and semantic.strip() == "steps:":
                return []
            break
    return [f"{relative}:{uses_index + 1}: uses must be nested under steps"]


def _codeql_pair_errors(
    actions: list[tuple[str, str, str, int]], relative: str
) -> list[str]:
    errors: list[str] = []
    expected = {"init", "analyze"}
    for component in expected:
        count = sum(item[0] == component for item in actions)
        if count != 1:
            errors.append(
                f"{relative}: CodeQL component {component} must appear exactly once"
            )
    extras = sorted({item[0] for item in actions} - expected)
    if extras:
        errors.append(f"{relative}: unexpected CodeQL action components: {extras}")
    pins = {(item[1], item[2]) for item in actions}
    if len(pins) > 1:
        errors.append(
            f"{relative}: all CodeQL actions must share one SHA and version comment"
        )
    return errors


def check_workflows(root: Path = ROOT) -> tuple[str, ...]:
    directory = root / WORKFLOW_DIRECTORY
    errors: list[str] = []
    all_codeql_actions: list[tuple[str, str, str, str, int]] = []
    paths = sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))
    if not paths:
        return ("no workflow files found",)

    for path in paths:
        relative = path.relative_to(root).as_posix()
        payload = path.read_bytes()
        if b"\r" in payload:
            errors.append(f"{relative}: workflow must use LF line endings")
        if b"\t" in payload:
            errors.append(f"{relative}: workflow must not contain tab characters")
        text = payload.decode("utf-8")
        lines = text.splitlines()
        block_scalar_content = _block_scalar_content_indices(lines)
        errors.extend(_syntax_policy_errors(lines, relative))
        errors.extend(_check_permissions(lines, relative))
        for index, line in enumerate(lines):
            if "uses:" not in line:
                continue
            if index in block_scalar_content:
                errors.append(
                    f"{relative}:{index + 1}: uses inside a block scalar are forbidden"
                )
                continue
            stripped = line.strip()
            if stripped.startswith("uses: ./"):
                errors.append(
                    f"{relative}:{index + 1}: local actions and reusable workflows are forbidden"
                )
                continue
            match = USES.match(line)
            if match is None:
                errors.append(
                    f"{relative}:{index + 1}: external action needs a full pin and version comment"
                )
                continue
            spec = match.group("spec")
            if "@" not in spec:
                errors.append(f"{relative}:{index + 1}: action is missing a ref")
                continue
            action, ref = spec.rsplit("@", 1)
            uses_indent = len(match.group("indent"))
            errors.extend(_action_step_context_errors(lines, index, uses_indent, relative))
            if action.casefold().startswith("github/codeql-action/"):
                canonical_action = action.casefold()
                if action != canonical_action:
                    errors.append(
                        f"{relative}:{index + 1}: CodeQL action name must use canonical case"
                    )
                all_codeql_actions.append(
                    (
                        relative,
                        canonical_action.removeprefix("github/codeql-action/"),
                        ref,
                        match.group("version"),
                        index + 1,
                    )
                )
            if not action or PIN.fullmatch(ref) is None:
                errors.append(f"{relative}:{index + 1}: action ref must be a 40-hex SHA")
            if VERSION_COMMENT.fullmatch(match.group("version")) is None:
                errors.append(f"{relative}:{index + 1}: action pin needs a version comment")

            if action.casefold() == "actions/checkout":
                if action != "actions/checkout":
                    errors.append(
                        f"{relative}:{index + 1}: checkout action name must use canonical case"
                    )
                errors.extend(
                    _checkout_persistence_errors(lines, index, uses_indent, relative)
                )
    codeql_relative = ".github/workflows/codeql.yml"
    if not any(path.relative_to(root).as_posix() == codeql_relative for path in paths):
        errors.append(f"{codeql_relative}: canonical CodeQL workflow is required")
    misplaced = sorted({item[0] for item in all_codeql_actions if item[0] != codeql_relative})
    if misplaced:
        errors.append(f"CodeQL actions are forbidden outside {codeql_relative}: {misplaced}")
    canonical_actions = [
        (component, ref, version, line)
        for relative, component, ref, version, line in all_codeql_actions
        if relative == codeql_relative
    ]
    errors.extend(_codeql_pair_errors(canonical_actions, codeql_relative))
    return tuple(errors)


def check_dependabot(root: Path = ROOT) -> tuple[str, ...]:
    path = root / DEPENDABOT_PATH
    relative = DEPENDABOT_PATH.as_posix()
    if not path.is_file():
        return (f"{relative}: missing Dependabot configuration",)
    payload = path.read_bytes()
    errors: list[str] = []
    if b"\r" in payload:
        errors.append(f"{relative}: configuration must use LF line endings")
    if b"\t" in payload:
        errors.append(f"{relative}: configuration must not contain tab characters")
    text = payload.decode("utf-8")
    lines = text.splitlines()
    errors.extend(_syntax_policy_errors(lines, relative))
    top_level = [
        (index, _without_comment(line).strip())
        for index, line in enumerate(lines)
        if _without_comment(line).strip() and _indent(_without_comment(line)) == 0
    ]
    if [item[1] for item in top_level] != ["version: 2", "updates:"]:
        errors.append(f"{relative}: top-level policy must be exactly version 2 and updates")
    updates_indices = [index for index, line in enumerate(lines) if line == "updates:"]
    if len(updates_indices) != 1:
        errors.append(f"{relative}: expected exactly one top-level updates section")
        return tuple(errors)
    updates_start = updates_indices[0]
    updates_end = len(lines)
    for index in range(updates_start + 1, len(lines)):
        semantic = _without_comment(lines[index])
        if semantic.strip() and _indent(semantic) == 0:
            updates_end = index
            break
    item_starts = [
        index
        for index in range(updates_start + 1, updates_end)
        if re.match(r"^  -(?:\s|$)", lines[index])
    ]
    items: list[tuple[str, int, int]] = []
    for position, start in enumerate(item_starts):
        end = item_starts[position + 1] if position + 1 < len(item_starts) else updates_end
        match = re.fullmatch(
            r"  - package-ecosystem: (?P<ecosystem>[A-Za-z0-9_-]+)", lines[start]
        )
        if match is None:
            errors.append(
                f"{relative}:{start + 1}: update items must begin with package-ecosystem"
            )
            continue
        items.append((match.group("ecosystem"), start, end))
    github_items = [item for item in items if item[0] == "github-actions"]
    if len(github_items) != 1:
        errors.append(f"{relative}: expected exactly one github-actions update block")
        return tuple(errors)
    _, start, end = github_items[0]
    block_lines = lines[start:end]
    block = "\n".join(block_lines)
    if block != DEPENDABOT_GITHUB_ACTIONS_BLOCK:
        errors.append(f"{relative}: github-actions update block must match canonical policy")
    if text.count('"github/codeql-action/*"') != 1:
        errors.append(f"{relative}: CodeQL Dependabot pattern must appear exactly once")
    return tuple(errors)


def main() -> int:
    errors = (*check_workflows(), *check_dependabot())
    if errors:
        for error in errors:
            print(error)
        return 1
    print("workflow security policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
