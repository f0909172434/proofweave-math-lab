"""Fail-closed static checks for GitHub Actions workflow policy."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = Path(".github/workflows")
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


def _syntax_policy_errors(lines: list[str], relative: str) -> list[str]:
    errors: list[str] = []
    in_events = False
    for index, raw_line in enumerate(lines):
        semantic = _without_comment(raw_line)
        if not semantic.strip():
            continue
        indentation = _indent(semantic)
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


def check_workflows(root: Path = ROOT) -> tuple[str, ...]:
    directory = root / WORKFLOW_DIRECTORY
    errors: list[str] = []
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
        errors.extend(_syntax_policy_errors(lines, relative))
        errors.extend(_check_permissions(lines, relative))
        for index, line in enumerate(lines):
            if "uses:" not in line:
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
            if not action or PIN.fullmatch(ref) is None:
                errors.append(f"{relative}:{index + 1}: action ref must be a 40-hex SHA")
            if VERSION_COMMENT.fullmatch(match.group("version")) is None:
                errors.append(f"{relative}:{index + 1}: action pin needs a version comment")

            if action.casefold() == "actions/checkout":
                if action != "actions/checkout":
                    errors.append(
                        f"{relative}:{index + 1}: checkout action name must use canonical case"
                    )
                uses_indent = len(match.group("indent"))
                errors.extend(
                    _checkout_persistence_errors(lines, index, uses_indent, relative)
                )
    return tuple(errors)


def main() -> int:
    errors = check_workflows()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("workflow security policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
