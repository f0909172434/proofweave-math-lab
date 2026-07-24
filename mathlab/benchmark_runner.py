from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .errors import ConfigurationRequired, ValidationError
from .io import load_json, load_jsonl, save_jsonl, utc_now
from .schemas import require_valid


CATEGORIES = {
    "assumption_consistency",
    "proof_gap_detection",
    "counterexample_validation",
    "asymptotic_audit",
    "algebra_sign_audit",
    "citation_entailment",
    "numerical_methodology",
    "latex_claim_mapping",
    "research_planning",
    "long_context_consistency",
}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkRunner:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.result_path = self.root / "state" / "model_benchmarks.jsonl"

    def validate_suite(self) -> dict[str, Any]:
        cases = []
        for path in sorted((self.root / "benchmarks" / "public").glob("*.json")):
            value = load_json(path)
            if not isinstance(value, dict):
                raise ValidationError(f"Benchmark case {path} must be an object")
            required = {"case_id", "dataset_version", "category", "prompt", "expected"}
            missing = required - value.keys()
            if missing:
                raise ValidationError(f"Benchmark case {path} missing {sorted(missing)}")
            if value["category"] not in CATEGORIES:
                raise ValidationError(f"Benchmark case {path} has invalid category")
            cases.append(value)
        covered = {case["category"] for case in cases}
        return {
            "status": "VALID" if covered == CATEGORIES else "INCOMPLETE",
            "case_count": len(cases),
            "categories": sorted(covered),
            "missing_categories": sorted(CATEGORIES - covered),
        }

    def run_model(self, model_id: str, *, allow_paid_probe: bool = False) -> None:
        if not allow_paid_probe:
            raise ConfigurationRequired(
                "Model benchmark execution is disabled by default; pass explicit paid-probe authorization through policy, not just a model name."
            )
        raise ConfigurationRequired(
            "No live benchmark executor is configured. Register a provider adapter and a human-reviewed answer key first."
        )

    def record(self, result: dict[str, Any]) -> None:
        value = dict(result)
        value.setdefault("recorded_at", utc_now())
        require_valid(value, "benchmark_result", SCHEMA_ROOT)
        records = load_jsonl(self.result_path)
        records.append(value)
        save_jsonl(self.result_path, records)

    def summarize(self, *, minimum_cases: int = 20) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in load_jsonl(self.result_path):
            groups[record.get("model_id", "UNKNOWN")].append(record)
        summaries = []
        for model_id, rows in sorted(groups.items()):
            evaluated = [row for row in rows if isinstance(row.get("correct"), bool)]
            false_accepts = sum(bool(row.get("false_acceptance")) for row in evaluated)
            false_rejects = sum(bool(row.get("false_rejection")) for row in evaluated)
            summaries.append(
                {
                    "model_id": model_id,
                    "n": len(evaluated),
                    "accuracy": (sum(row["correct"] for row in evaluated) / len(evaluated)) if evaluated else None,
                    "false_acceptance_rate": false_accepts / len(evaluated) if evaluated else None,
                    "false_rejection_rate": false_rejects / len(evaluated) if evaluated else None,
                    "ranking_eligible": len(evaluated) >= minimum_cases,
                }
            )
        eligible = [row for row in summaries if row["ranking_eligible"]]
        ranking = sorted(
            eligible,
            key=lambda row: (
                row["false_acceptance_rate"],
                -(row["accuracy"] or 0),
                row["model_id"],
            ),
        )
        return {
            "models": summaries,
            "ranking": [row["model_id"] for row in ranking] if len(ranking) >= 2 else [],
            "ranking_status": "AVAILABLE" if len(ranking) >= 2 else "INSUFFICIENT_DATA",
        }
