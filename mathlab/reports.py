"""Truth-derived, read-only research-status report helpers.

The functions in this module only read the formal fact graph, issue ledger, and
project state.  They deliberately do not infer a new mathematical result or
write to the truth layer.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from .io import atomic_write_text, load_json, load_jsonl, stable_digest


STATUS_SOURCES = (
    "state/fact_graph.jsonl",
    "state/issue_ledger.jsonl",
    "state/project_state.json",
)
OPEN_BLOCKING_STATUSES = {"OPEN", "IN_PROGRESS"}
OPEN_BLOCKING_SEVERITIES = {"FATAL", "MAJOR"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_text(value: Any) -> str:
    return str(value) if value not in (None, "") else "UNKNOWN"


def build_status_report(root: Path | str) -> dict[str, Any]:
    """Return a deterministic status snapshot derived from canonical state."""

    root = Path(root)
    facts = load_jsonl(root / "state" / "fact_graph.jsonl")
    issues = load_jsonl(root / "state" / "issue_ledger.jsonl")
    project_state = load_json(root / "state" / "project_state.json", default={}) or {}
    source_files = [
        {"path": relative, "sha256": _sha256(root / relative)} for relative in STATUS_SOURCES
    ]
    fact_counts = Counter(_as_text(record.get("status")) for record in facts)
    issue_counts = Counter(_as_text(record.get("status")) for record in issues)
    blocking = sorted(
        record["issue_id"]
        for record in issues
        if record.get("status") in OPEN_BLOCKING_STATUSES
        and record.get("severity") in OPEN_BLOCKING_SEVERITIES
        and record.get("issue_id")
    )
    facts_by_status: dict[str, list[str]] = {}
    for status in sorted(fact_counts):
        facts_by_status[status] = sorted(
            record["fact_id"] for record in facts if record.get("status") == status and record.get("fact_id")
        )
    return {
        "source_files": source_files,
        "source_digest": stable_digest(source_files),
        "updated_at": project_state.get("updated_at", "UNKNOWN"),
        "counts": {"facts": dict(sorted(fact_counts.items())), "issues": dict(sorted(issue_counts.items()))},
        "facts_by_status": facts_by_status,
        "open_blocking_issue_ids": blocking,
        "project": {
            key: project_state.get(key, [])
            for key in (
                "current_objective",
                "next_recommended_action",
                "blocking_gaps",
                "proposed_results",
                "tasks_lacking_independent_verification",
            )
        },
        "project_localized": project_state.get("status_narrative", {}),
    }


def _items(values: list[Any], empty: str) -> str:
    return "\n".join(f"- {value}" for value in values) if values else f"- {empty}"


def render_status_markdown(report: dict[str, Any], locale: str) -> str:
    """Render the report in English or Traditional Chinese without changing its data."""

    english = locale == "en"
    title = "Research status (truth-derived)" if english else "研究狀態（由 truth layer 衍生）"
    labels = (
        {
            "updated": "Project-state timestamp",
            "digest": "Source digest (SHA-256)",
            "counts": "Counts",
            "facts": "Facts by status",
            "blockers": "Open release blockers (FATAL/MAJOR)",
            "objective": "Current objective",
            "next": "Next recommended action",
            "proposed": "Proposed results (not verified)",
            "verification": "Tasks lacking independent verification",
            "sources": "Canonical sources",
            "none": "None recorded",
            "note": "This report is a read-only summary. It does not promote claims or turn computational evidence into proof.",
        }
        if english
        else {
            "updated": "project state 時間戳記",
            "digest": "來源摘要（SHA-256）",
            "counts": "數量",
            "facts": "依狀態列出的事實",
            "blockers": "尚未解決的發行阻塞項（FATAL/MAJOR）",
            "objective": "目前目標",
            "next": "建議的下一步",
            "proposed": "PROPOSED 結果（尚未驗證）",
            "verification": "尚缺獨立驗證的工作",
            "sources": "canonical 來源",
            "none": "未記錄",
            "note": "本報告僅為唯讀摘要；它不會升格 claim，也不會把計算證據當作證明。",
        }
    )
    fact_counts = ", ".join(f"{key}: {value}" for key, value in report["counts"]["facts"].items()) or labels["none"]
    issue_counts = ", ".join(f"{key}: {value}" for key, value in report["counts"]["issues"].items()) or labels["none"]
    fact_sections = "\n\n".join(
        f"### {status}\n\n{_items(ids, labels['none'])}" for status, ids in report["facts_by_status"].items()
    ) or labels["none"]
    source_lines = "\n".join(
        f"- `{source['path']}`: `{source['sha256']}`" for source in report["source_files"]
    )
    project = report.get("project_localized", {}).get(locale, report["project"])
    return (
        f"# {title}\n\n"
        f"{labels['updated']}: `{report['updated_at']}`  \n"
        f"{labels['digest']}: `{report['source_digest']}`\n\n"
        f"> {labels['note']}\n\n"
        f"## {labels['counts']}\n\n- Facts: {fact_counts}\n- Issues: {issue_counts}\n\n"
        f"## {labels['facts']}\n\n{fact_sections}\n\n"
        f"## {labels['blockers']}\n\n{_items(report['open_blocking_issue_ids'], labels['none'])}\n\n"
        f"## {labels['objective']}\n\n{_as_text(project['current_objective'])}\n\n"
        f"## {labels['next']}\n\n{_as_text(project['next_recommended_action'])}\n\n"
        f"## {labels['proposed']}\n\n{_items(project['proposed_results'], labels['none'])}\n\n"
        f"## {labels['verification']}\n\n{_items(project['tasks_lacking_independent_verification'], labels['none'])}\n\n"
        f"## {labels['sources']}\n\n{source_lines}\n"
    )


def _tex_escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in _as_text(value))


def _tex_items(values: list[Any], empty: str) -> str:
    rendered = values or [empty]
    return "\\begin{itemize}\n" + "\n".join(f"\\item {_tex_escape(item)}" for item in rendered) + "\n\\end{itemize}"


def render_status_tex(report: dict[str, Any], locale: str, template: str) -> str:
    """Fill a TeX template with escaped, truth-derived report content."""

    english = locale == "en"
    none = "None recorded" if english else "未記錄"
    fact_counts = ", ".join(f"{key}: {value}" for key, value in report["counts"]["facts"].items()) or none
    issue_counts = ", ".join(f"{key}: {value}" for key, value in report["counts"]["issues"].items()) or none
    fact_lines = []
    for status, ids in report["facts_by_status"].items():
        fact_lines.append(rf"\subsection*{{{_tex_escape(status)}}}")
        fact_lines.append(_tex_items(ids, none))
    source_rows = report["source_files"]
    sources_tex = (
        "\\begin{itemize}\n"
        + "\n".join(
            "\\item \\texttt{" + _tex_escape(item["path"]) + "}: "
            "\\texttt{\\seqsplit{" + item["sha256"] + "}}"
            for item in source_rows
        )
        + "\n\\end{itemize}"
        if source_rows
        else _tex_items([], none)
    )
    project = report.get("project_localized", {}).get(locale, report["project"])
    replacements = {
        "{{UPDATED_AT}}": _tex_escape(report["updated_at"]),
        "{{SOURCE_DIGEST}}": _tex_escape(report["source_digest"]),
        "{{FACT_COUNTS}}": _tex_escape(fact_counts),
        "{{ISSUE_COUNTS}}": _tex_escape(issue_counts),
        "{{FACTS_BY_STATUS}}": "\n".join(fact_lines) or _tex_escape(none),
        "{{BLOCKING_ISSUES}}": _tex_items(report["open_blocking_issue_ids"], none),
        "{{CURRENT_OBJECTIVE}}": _tex_escape(project["current_objective"]),
        "{{NEXT_ACTION}}": _tex_escape(project["next_recommended_action"]),
        "{{PROPOSED_RESULTS}}": _tex_items(project["proposed_results"], none),
        "{{MISSING_VERIFICATION}}": _tex_items(project["tasks_lacking_independent_verification"], none),
        "{{SOURCES}}": sources_tex,
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def write_status_sources(root: Path | str, output_directory: Path | str | None = None) -> dict[str, Path]:
    """Write bilingual Markdown and TeX sources; PDFs are built by the build script.

    ``state/STATUS.md`` is generated from the same truth snapshot and therefore
    is never a hand-maintained fact count.  Project policy requires this
    canonical status artifact to be Traditional Chinese; the English rendering
    remains available under ``dist/status``.
    """

    root = Path(root)
    output = Path(output_directory) if output_directory is not None else root / "dist" / "status"
    report = build_status_report(root)
    result: dict[str, Path] = {}
    canonical_status = root / "state" / "STATUS.md"
    atomic_write_text(
        canonical_status,
        "<!-- GENERATED by mathlab.reports; do not edit counts manually. -->\n\n"
        + render_status_markdown(report, "zh-TW"),
    )
    result["canonical_markdown"] = canonical_status
    for locale in ("en", "zh-TW"):
        suffix = "en" if locale == "en" else "zh_TW"
        markdown_path = output / f"STATUS_{suffix}.md"
        tex_path = output / f"STATUS_{suffix}.tex"
        template_path = root / "paper" / "status_templates" / f"status_{suffix}.tex.in"
        atomic_write_text(markdown_path, render_status_markdown(report, locale))
        atomic_write_text(tex_path, render_status_tex(report, locale, template_path.read_text(encoding="utf-8")))
        result[f"markdown_{locale}"] = markdown_path
        result[f"tex_{locale}"] = tex_path
    return result
