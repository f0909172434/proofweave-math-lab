from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .fact_graph import FactGraph
from .io import atomic_write_text, save_json, utc_now
from .issue_ledger import IssueLedger


STATE_MARKDOWN = (
    "problem.md",
    "assumptions.md",
    "notation.md",
    "research_plan.md",
    "open_gaps.md",
    "dead_ends.md",
    "decisions.md",
    "CHANGELOG.md",
    "STATUS.md",
)


def initialize_state(root: Path, *, overwrite: bool = False) -> list[Path]:
    root = Path(root)
    state = root / "state"
    templates = state / "templates"
    state.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for name in STATE_MARKDOWN:
        target = state / name
        if target.exists() and not overwrite:
            continue
        source = templates / name
        if source.exists():
            shutil.copyfile(source, target)
        else:
            atomic_write_text(target, f"# {name.removesuffix('.md').replace('_', ' ').title()}\n\n")
        created.append(target)
    for name in (
        "fact_graph.jsonl",
        "conjectures.jsonl",
        "source_registry.jsonl",
        "issue_ledger.jsonl",
        "model_benchmarks.jsonl",
        "routing_log.jsonl",
    ):
        target = state / name
        if not target.exists():
            atomic_write_text(target, "")
            created.append(target)
    project_state_path = state / "project_state.json"
    if overwrite or not project_state_path.exists():
        save_json(
            project_state_path,
            {
                "current_objective": "Formalize the first real research problem before attempting a proof.",
                "verified_results": [],
                "proposed_results": [],
                "refuted_claims": [],
                "active_workers": [],
                "blocking_gaps": ["No production research problem has been entered."],
                "failed_approaches": [],
                "latest_experiments": [],
                "next_recommended_action": "Run workflows 00 and 01.",
                "additional_model_usage_justified": "No",
                "current_execution_mode": "UNDETECTED",
                "verified_available_models": [],
                "configured_unverified_models": [],
                "disabled_models": [],
                "budget_mode": "BALANCED",
                "recent_routing_decisions": [],
                "escalations": [],
                "downgrades": [],
                "tasks_lacking_independent_verification": [],
                "updated_at": utc_now(),
            },
        )
        created.append(project_state_path)
    return created


def project_summary(root: Path) -> dict[str, Any]:
    graph = FactGraph.at_project(root)
    issues = IssueLedger(root / "state" / "issue_ledger.jsonl")
    fact_counts = Counter(record["status"] for record in graph.all())
    issue_counts = Counter(record["status"] for record in issues.all())
    return {
        "generated_at": utc_now(),
        "facts": dict(sorted(fact_counts.items())),
        "issues": dict(sorted(issue_counts.items())),
        "verified_fact_ids": sorted(graph.verified_ids()),
        "blocking_gaps": [
            record["issue_id"]
            for record in issues.all()
            if record["status"] in {"OPEN", "IN_PROGRESS"}
            and record["severity"] in {"FATAL", "MAJOR"}
        ],
    }
