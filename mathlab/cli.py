from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .benchmark_runner import BenchmarkRunner
from .budget_manager import BudgetManager
from .capability_probe import detect_capabilities
from .errors import MathLabError
from .fact_graph import FactGraph
from .io import configure_utf8_console, find_project_root, load_json, save_json
from .issue_ledger import IssueLedger
from .model_registry import ModelRegistry
from .model_router import recommend_model
from .project_state import initialize_state, project_summary
from .routing_audit import RoutingAudit
from .source_registry import SourceRegistry
from .task_classifier import classify_task, load_task
from .validation import (
    build_release_manifest,
    release_report,
    validate_bibliography,
    validate_claim_map,
    validate_experiments,
)
from .providers import (
    AnthropicAdapter,
    ClaudeCodeAdapter,
    CodexAdapter,
    GatewayAdapter,
    OpenAIAdapter,
    OpenAICompatibleAdapter,
)


def _print(value: Any) -> None:
    if isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _root(args: argparse.Namespace) -> Path:
    return Path(args.root).resolve() if getattr(args, "root", None) else find_project_root()


def _record_from_file(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Input JSON must be an object")
    return value


def _route(root: Path, task_path: str, *, record: bool = True) -> dict[str, Any]:
    task = load_task(Path(task_path))
    classification = classify_task(task)
    registry = ModelRegistry.from_path(root / "state" / "model_inventory.json")
    budget = BudgetManager(root / "state" / "budget_state.json")
    policy = load_json(root / "config" / "runtime_policy.json", default={}) or {}
    decision = recommend_model(classification, registry, budget, user_policy=policy)
    decision["task_file"] = str(Path(task_path).resolve())
    decision["classification"] = classification
    if record:
        RoutingAudit(root / "state" / "routing_log.jsonl").append(decision)
    return decision


def cmd_init(args: argparse.Namespace) -> int:
    root = _root(args)
    created = initialize_state(root, overwrite=args.force)
    inventory = detect_capabilities(root, write=True)
    _print({"status": "initialized", "created": [str(path) for path in created], "mode": inventory["execution_mode"]})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _print(project_summary(_root(args)))
    return 0


def cmd_add_source(args: argparse.Namespace) -> int:
    root = _root(args)
    record = _record_from_file(args.file)
    _print(SourceRegistry(root / "state" / "source_registry.jsonl").add(record))
    return 0


def cmd_add_claim(args: argparse.Namespace) -> int:
    root = _root(args)
    _print(FactGraph(root / "state" / "fact_graph.jsonl").add(_record_from_file(args.file)))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = _root(args)
    graph = FactGraph(root / "state" / "fact_graph.jsonl")
    report = _record_from_file(args.report)
    if args.outcome == "ACCEPT":
        if report.get("outcome") != "ACCEPT":
            raise ValueError("CLI outcome and untouched verification report outcome do not match")
        _print(
            graph.promote(
                args.fact_id,
                verifier=args.verifier,
                verifier_role="theorem_verifier",
                report=report,
            )
        )
    else:
        if report.get("outcome") != args.outcome:
            raise ValueError("CLI outcome and untouched verification report outcome do not match")
        _print(
            graph.review_failure(
                args.fact_id, verifier=args.verifier, outcome=args.outcome, report=report
            )
        )
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    root = _root(args)
    graph = FactGraph(root / "state" / "fact_graph.jsonl")
    affected = graph.revoke(
        args.fact_id, reason=args.reason, revoked_by=args.actor
    )
    _print(
        {
            "status": "revoked",
            "affected": affected,
            "revocation_report": graph.get(args.fact_id).get("revocation_report"),
        }
    )
    return 0


def cmd_graph_check(args: argparse.Namespace) -> int:
    errors = FactGraph(_root(args) / "state" / "fact_graph.jsonl").check()
    _print({"status": "PASS" if not errors else "FAIL", "errors": errors})
    return 0 if not errors else 1


def cmd_experiment_check(args: argparse.Namespace) -> int:
    checks = validate_experiments(_root(args))
    _print([check.as_dict() for check in checks])
    return 1 if any(check.status == "FAIL" for check in checks) else 0


def cmd_paper_check(args: argparse.Namespace) -> int:
    root = _root(args)
    checks = [*validate_claim_map(root), *validate_bibliography(root)]
    _print([check.as_dict() for check in checks])
    return 1 if any(check.status == "FAIL" for check in checks) else 0


def cmd_review(args: argparse.Namespace) -> int:
    root = _root(args)
    checks = [*validate_claim_map(root), *validate_bibliography(root)]
    issues = [check.as_dict() for check in checks if check.status in {"FAIL", "WARN"}]
    _print(
        {
            "mode": args.mode,
            "review_scope": "DETERMINISTIC_PRECHECK_ONLY",
            "status": "NEEDS_REVIEW" if issues else "DETERMINISTIC_PRECHECK_PASS",
            "fatal_errors": [row for row in issues if row["status"] == "FAIL"],
            "major_revisions": [],
            "minor_revisions": [row for row in issues if row["status"] == "WARN"],
            "strengths": [],
            "recommendation": (
                "This command is not a referee report. Human/independent mathematical review is still required."
            ),
        }
    )
    return 1 if any(row["status"] == "FAIL" for row in issues) else 0


def cmd_release_check(args: argparse.Namespace) -> int:
    root = _root(args)
    report = release_report(root)
    save_json(root / "state" / "release_report.json", report)
    if report["status"] == "PASS":
        manifest = build_release_manifest(root)
        save_json(root / "state" / "release_manifest.json", manifest)
        report["snapshot"] = {
            "snapshot_id": manifest["snapshot_id"],
            "file_count": manifest["file_count"],
            "git_head": manifest["git_head"],
            "git_dirty": manifest["git_dirty"],
            "manifest": "state/release_manifest.json",
        }
        save_json(root / "state" / "release_report.json", report)
    _print(report)
    return 0 if report["status"] == "PASS" else 1


def cmd_models_detect(args: argparse.Namespace) -> int:
    _print(detect_capabilities(_root(args), write=True))
    return 0


def cmd_models_list(args: argparse.Namespace) -> int:
    registry = ModelRegistry.from_path(_root(args) / "state" / "model_inventory.json")
    _print(registry.all())
    return 0


def cmd_models_show(args: argparse.Namespace) -> int:
    registry = ModelRegistry.from_path(_root(args) / "state" / "model_inventory.json")
    _print(registry.get(args.model))
    return 0


def cmd_models_doctor(args: argparse.Namespace) -> int:
    root = _root(args)
    inventory = detect_capabilities(root, write=False)
    issues = []
    if not inventory["models"]:
        issues.append("No host-account model is verified; routing will be advisory-only.")
    if inventory["paid_probe_performed"]:
        issues.append("Unexpected paid probe flag.")
    _print({"status": "OK" if not issues else "LIMITED", "mode": inventory["execution_mode"], "issues": issues, "tools": inventory["tools"]})
    return 0


def cmd_models_benchmark(args: argparse.Namespace) -> int:
    runner = BenchmarkRunner(_root(args))
    if args.model:
        runner.run_model(args.model, allow_paid_probe=False)
    _print({"suite": runner.validate_suite(), "results": runner.summarize()})
    return 0


def cmd_route_classify(args: argparse.Namespace) -> int:
    _print(classify_task(load_task(Path(args.task_file))))
    return 0


def cmd_route_recommend(args: argparse.Namespace) -> int:
    _print(_route(_root(args), args.task_file, record=True))
    return 0


def cmd_route_explain(args: argparse.Namespace) -> int:
    _print(RoutingAudit(_root(args) / "state" / "routing_log.jsonl").find(args.routing_id))
    return 0


def cmd_route_history(args: argparse.Namespace) -> int:
    _print(RoutingAudit(_root(args) / "state" / "routing_log.jsonl").all())
    return 0


def cmd_route_run(args: argparse.Namespace) -> int:
    decision = _route(_root(args), args.task_file, record=True)
    decision["execution_status"] = (
        "HOST_NATIVE_HANDOFF_REQUIRED"
        if decision.get("selected_provider") == "codex_desktop_native"
        else "DRY_RUN_ONLY"
    )
    decision["execution_note"] = "No external or paid model call was made by this command."
    _print(decision)
    return 0 if decision["status"] == "RECOMMENDED" else 2


def cmd_budget_status(args: argparse.Namespace) -> int:
    _print(BudgetManager(_root(args) / "state" / "budget_state.json").snapshot())
    return 0


def cmd_budget_estimate(args: argparse.Namespace) -> int:
    root = _root(args)
    classification = classify_task(load_task(Path(args.task_file)))
    _print(BudgetManager(root / "state" / "budget_state.json").estimate(classification))
    return 0


def cmd_providers_status(args: argparse.Namespace) -> int:
    adapters = [
        CodexAdapter(),
        ClaudeCodeAdapter(),
        OpenAIAdapter(),
        AnthropicAdapter(),
        OpenAICompatibleAdapter(),
        GatewayAdapter(),
    ]
    _print([adapter.detect() for adapter in adapters])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathlab", description="ProofWeave auditable mathematics research workspace"
    )
    parser.add_argument("--root", help="project root (auto-detected by default)")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)
    commands.add_parser("status").set_defaults(func=cmd_status)

    source = commands.add_parser("add-source")
    source.add_argument("--file", required=True)
    source.set_defaults(func=cmd_add_source)
    claim = commands.add_parser("add-claim")
    claim.add_argument("--file", required=True)
    claim.set_defaults(func=cmd_add_claim)
    verify = commands.add_parser("verify")
    verify.add_argument("fact_id")
    verify.add_argument("--report", required=True)
    verify.add_argument("--verifier", required=True)
    verify.add_argument("--outcome", choices=["ACCEPT", "REJECT", "UNCERTAIN"], required=True)
    verify.set_defaults(func=cmd_verify)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("fact_id")
    revoke.add_argument("--reason", required=True)
    revoke.add_argument("--actor", required=True)
    revoke.set_defaults(func=cmd_revoke)
    commands.add_parser("graph-check").set_defaults(func=cmd_graph_check)
    commands.add_parser("experiment-check").set_defaults(func=cmd_experiment_check)
    commands.add_parser("paper-check").set_defaults(func=cmd_paper_check)
    review = commands.add_parser("review")
    review.add_argument("--mode", choices=["internal", "blind-referee"], default="internal")
    review.set_defaults(func=cmd_review)
    commands.add_parser("release-check").set_defaults(func=cmd_release_check)

    models = commands.add_parser("models")
    model_sub = models.add_subparsers(dest="models_command", required=True)
    model_sub.add_parser("detect").set_defaults(func=cmd_models_detect)
    model_sub.add_parser("refresh").set_defaults(func=cmd_models_detect)
    model_sub.add_parser("list").set_defaults(func=cmd_models_list)
    show = model_sub.add_parser("show")
    show.add_argument("model")
    show.set_defaults(func=cmd_models_show)
    model_sub.add_parser("doctor").set_defaults(func=cmd_models_doctor)
    benchmark = model_sub.add_parser("benchmark")
    benchmark.add_argument("--model")
    benchmark.set_defaults(func=cmd_models_benchmark)

    route = commands.add_parser("route")
    route_sub = route.add_subparsers(dest="route_command", required=True)
    for name, func in (("classify", cmd_route_classify), ("recommend", cmd_route_recommend), ("run", cmd_route_run)):
        sub = route_sub.add_parser(name)
        sub.add_argument("task_file")
        sub.set_defaults(func=func)
    explain = route_sub.add_parser("explain")
    explain.add_argument("routing_id")
    explain.set_defaults(func=cmd_route_explain)
    route_sub.add_parser("history").set_defaults(func=cmd_route_history)

    budget = commands.add_parser("budget")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_sub.add_parser("status").set_defaults(func=cmd_budget_status)
    estimate = budget_sub.add_parser("estimate")
    estimate.add_argument("task_file")
    estimate.set_defaults(func=cmd_budget_estimate)

    providers = commands.add_parser("providers")
    provider_sub = providers.add_subparsers(dest="provider_command", required=True)
    provider_sub.add_parser("status").set_defaults(func=cmd_providers_status)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (MathLabError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
