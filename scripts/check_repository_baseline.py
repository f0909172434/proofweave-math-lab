from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

from mathlab.io import configure_utf8_console, find_project_root


ACTION_PIN = re.compile(
    r"\buses:\s*(?P<action>[^\s@]+)@(?P<sha>[0-9a-f]{40})"
    r"\s+#\s+(?P<version>v\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?)\s*$"
)
MARKDOWN_LINK = re.compile(
    r"(?<!!)\[[^\]]+\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]+['\"])?\)"
)
USER_SPECIFIC_CODEX_PYTHON = re.compile(
    r"[A-Za-z]:\\Users\\[^\\\r\n]+\\\.cache\\codex-runtimes\\[^\r\n`\"']*python\.exe",
    re.IGNORECASE,
)

REQUIRED_FILES = (
    "README.md",
    "README.en.md",
    "README.zh-TW.md",
    "README.zh-CN.md",
    "README.ja.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/user_guide.md",
    "docs/design/threat_model.md",
    "docs/security_baseline.md",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug-report.yml",
    ".github/ISSUE_TEMPLATE/feature-request.yml",
    ".github/ISSUE_TEMPLATE/research-correctness.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
)


def check_required_files(root: Path) -> list[str]:
    return [f"missing required file: {path}" for path in REQUIRED_FILES if not (root / path).is_file()]


def check_workflow_pins(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.y*ml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "uses:" not in line:
                continue
            value = line.split("uses:", 1)[1].strip()
            if value.startswith("./"):
                continue
            if not ACTION_PIN.search(line):
                errors.append(
                    f"{path.relative_to(root)}:{line_number}: action must use a full commit SHA and version comment"
                )
    return errors


def _markdown_files(root: Path) -> list[Path]:
    files = [*root.glob("README*.md"), root / "SECURITY.md", root / "CONTRIBUTING.md"]
    files.extend((root / "docs").rglob("*.md"))
    return sorted({path for path in files if path.is_file()})


def check_local_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _markdown_files(root):
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group("target").strip("<>")
            if not raw_target or raw_target.startswith("#"):
                continue
            parsed = urlsplit(raw_target)
            if parsed.scheme or raw_target.startswith("//"):
                continue
            relative = unquote(parsed.path)
            if not relative:
                continue
            destination = (path.parent / relative).resolve()
            if not destination.exists():
                line_number = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(root)}:{line_number}: missing local link target {relative!r}"
                )
    return errors


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        return [
            root / item.decode("utf-8", errors="surrogateescape")
            for item in result.stdout.split(b"\0")
            if item
        ]
    fallback = _markdown_files(root)
    fallback.extend((root / "experiments" / "reports").rglob("*.md"))
    return sorted(set(fallback))


def check_no_user_specific_runtime_paths(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _tracked_files(root):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        normalized_text = text.replace("\\\\", "\\")
        if USER_SPECIFIC_CODEX_PYTHON.search(normalized_text):
            errors.append(
                f"{path.relative_to(root)}: contains a user-specific Codex Python runtime path"
            )
    return errors


def check_public_contracts(root: Path) -> list[str]:
    errors: list[str] = []
    readme = (root / "README.md").read_text(encoding="utf-8")
    for required in (
        "experimental 0.1",
        "python -m scripts.run_toy_workflow",
        "toy-odd-sum: VERIFIED",
        "toy-odd-sum-flawed: REJECTED",
        "state/fact_graph.jsonl",
        "Wang Chih Kai",
    ):
        if required not in readme:
            errors.append(f"README.md: missing public contract text {required!r}")
    if re.search(r"[A-Za-z]:\\Users\\", readme, re.IGNORECASE):
        errors.append("README.md: contains a user-specific Windows path")

    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for required in (
        "  ci-gate:",
        "    name: ci-gate",
        "python -m unittest discover -s tests -v",
        "python -m mathlab graph-check",
        "python -m scripts.release_check",
    ):
        if required not in ci:
            errors.append(f".github/workflows/ci.yml: missing CI contract {required!r}")
    if "pull_request_target" in ci:
        errors.append(".github/workflows/ci.yml: pull_request_target is forbidden")

    codeql = (root / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    for required in ("languages: python", "security-events: write"):
        if required not in codeql:
            errors.append(f".github/workflows/codeql.yml: missing CodeQL contract {required!r}")

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    if 'authors = [{name = "Wang Chih Kai"}]' not in pyproject:
        errors.append("pyproject.toml: public author metadata is not Wang Chih Kai")
    if "Copyright (c) 2026 Wang Chih Kai" not in license_text:
        errors.append("LICENSE: public copyright metadata is not Wang Chih Kai")
    return errors


def check_repository(root: Path) -> list[str]:
    return [
        *check_required_files(root),
        *check_workflow_pins(root),
        *check_local_markdown_links(root),
        *check_no_user_specific_runtime_paths(root),
        *check_public_contracts(root),
    ]


def main() -> int:
    configure_utf8_console()
    root = find_project_root(Path.cwd())
    errors = check_repository(root)
    if errors:
        print("Repository baseline checks: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository baseline checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
