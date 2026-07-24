from __future__ import annotations

import json
from pathlib import Path

from mathlab.io import configure_utf8_console

from mathlab.fact_graph import FactGraph
from mathlab.io import find_project_root, save_json
from mathlab.validation import validate_claim_map
from scripts.compile_paper import compile_tex


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    configure_utf8_console()
    root = find_project_root(Path.cwd())
    toy = root / "examples" / "toy_odd_sum"
    state = toy / "state"
    state.mkdir(parents=True, exist_ok=True)
    graph_path = state / "fact_graph.jsonl"
    graph_path.write_text("", encoding="utf-8")
    graph = FactGraph(graph_path)
    graph.add(load(toy / "inputs" / "correct_claim.json"))
    graph.add(load(toy / "inputs" / "flawed_claim.json"))
    accept = load(toy / "verifications" / "accept.json")
    reject = load(toy / "verifications" / "reject.json")
    accepted = graph.promote(
        "toy-odd-sum",
        verifier=accept["verifier"],
        verifier_role=accept["verifier_role"],
        report=accept,
    )
    rejected = graph.review_failure(
        "toy-odd-sum-flawed",
        verifier=reject["verifier"],
        outcome="REJECT",
        report=reject,
    )
    claim_checks = validate_claim_map(
        toy,
        paper_dir=toy / "paper",
        graph_path=graph_path,
    )
    compile_result = compile_tex(toy / "paper" / "main.tex")
    report = {
        "status": "PASS"
        if accepted["status"] == "VERIFIED"
        and rejected["status"] == "REJECTED"
        and not any(check.status == "FAIL" for check in claim_checks)
        and compile_result["status"] in {"PASS", "UNSUPPORTED"}
        else "FAIL",
        "accepted_fact": accepted["fact_id"],
        "accepted_status": accepted["status"],
        "rejected_fact": rejected["fact_id"],
        "rejected_status": rejected["status"],
        "claim_map": [check.as_dict() for check in claim_checks],
        "latex": compile_result,
        "limitations": [
            "Verifier decisions are reviewed fixtures for exercising the workflow.",
            "VERIFIED is a project workflow status, not a claim of formal proof or peer review."
        ],
    }
    save_json(toy / "toy_run_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
