from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .fact_graph import FactGraph
from .io import load_json, load_jsonl, stable_digest, utc_now
from .issue_ledger import IssueLedger
from .budget_manager import BudgetManager
from .model_registry import ModelRegistry
from .schemas import validate_all_schemas
from .schemas import require_valid
from .source_registry import SourceRegistry


BASE_FORMAL_ENVIRONMENTS = {
    "theorem": "theorem",
    "lemma": "lemma",
    "proposition": "proposition",
    "corollary": "corollary",
}
NEW_THEOREM_RE = re.compile(
    r"\\newtheorem\s*\*?\s*\{\s*([^}]+?)\s*\}\s*(?:\[[^]]*\]\s*)?\{\s*([^}]+?)\s*\}",
    re.I | re.S,
)
LABEL_RE = re.compile(r"\\label\s*\{\s*([^}]+?)\s*\}", re.I | re.S)
CITE_RE = re.compile(
    r"\\(?:cite[a-zA-Z*]*|parencite|textcite|autocite|footcite|smartcite|supercite|nocite)"
    r"\s*(?:\[[^]]*\]\s*){0,2}\{([^}]+)\}",
    re.I | re.S,
)
BIB_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.I)


@dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    message: str
    severity: str = "ERROR"
    artifact: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _scalar(text: str) -> Any:
    value = text.strip()
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip("'\"")


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the intentionally tiny YAML subset used by claim-map/config files."""

    result: dict[str, Any] = {}
    current_list: list[Any] | None = None
    current_item: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_list is None:
                raise ValueError("List item without a list key")
            current_item = {}
            current_list.append(current_item)
            remainder = stripped[2:].strip()
            if remainder:
                key, sep, value = remainder.partition(":")
                if not sep:
                    current_list[-1] = _scalar(remainder)
                    current_item = None
                else:
                    current_item[key.strip()] = _scalar(value)
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            raise ValueError(f"Unsupported YAML line: {raw}")
        if line.startswith((" ", "\t")) and current_item is not None:
            current_item[key.strip()] = _scalar(value)
            continue
        if not value.strip():
            parsed = []
            current_list = parsed
        else:
            parsed = _scalar(value)
            current_list = parsed if isinstance(parsed, list) else None
        current_item = None
        result[key.strip()] = parsed
    return result


def load_yaml_like(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    value = parse_simple_yaml(text)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _strip_tex_comments(text: str) -> str:
    """Remove ordinary TeX comments before conservative command scanning."""

    lines: list[str] = []
    for raw in text.splitlines(keepends=True):
        index = 0
        while index < len(raw):
            if raw[index] == "%":
                backslashes = 0
                cursor = index - 1
                while cursor >= 0 and raw[cursor] == "\\":
                    backslashes += 1
                    cursor -= 1
                if backslashes % 2 == 0:
                    raw = raw[:index] + ("\n" if raw.endswith("\n") else "")
                    break
            index += 1
        lines.append(raw)
    return "".join(lines)


def _theorem_kind(display_name: str) -> str:
    lowered = re.sub(r"\\[A-Za-z@]+|[{}]", " ", display_name).strip().lower()
    if "lemma" in lowered or "引理" in lowered:
        return "lemma"
    if "proposition" in lowered or "命題" in lowered:
        return "proposition"
    if "corollary" in lowered or "推論" in lowered:
        return "corollary"
    return "theorem"


def _formal_labels(tex_paths: Iterable[Path]) -> tuple[list[tuple[str, str, str]], list[str]]:
    labels: list[tuple[str, str, str]] = []
    errors: list[str] = []
    documents = [
        (path, _strip_tex_comments(path.read_text(encoding="utf-8"))) for path in tex_paths
    ]
    environment_kinds = dict(BASE_FORMAL_ENVIRONMENTS)
    for _, text in documents:
        for definition in NEW_THEOREM_RE.finditer(text):
            environment_kinds[definition.group(1).strip().lower()] = _theorem_kind(
                definition.group(2)
            )
    names = sorted(environment_kinds, key=len, reverse=True)
    begin_re = re.compile(
        r"\\begin\s*\{\s*(" + "|".join(re.escape(name) for name in names) + r")\s*\}",
        re.I | re.S,
    )
    for path, text in documents:
        matches = list(begin_re.finditer(text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            environment_name = match.group(1).strip()
            close_re = re.compile(
                r"\\end\s*\{\s*" + re.escape(environment_name) + r"\s*\}",
                re.I | re.S,
            )
            close = close_re.search(text, match.end(), end)
            snippet_end = close.start() if close else end
            label = LABEL_RE.search(text, match.end(), snippet_end)
            if not label:
                errors.append(f"{path}: {environment_name} #{index + 1} has no \\label")
            else:
                body = LABEL_RE.sub("", text[match.end() : snippet_end])
                canonical_body = re.sub(r"\s+", " ", body).strip()
                labels.append(
                    (
                        label.group(1).strip(),
                        environment_kinds[environment_name.lower()],
                        hashlib.sha256(canonical_body.encode("utf-8")).hexdigest(),
                    )
                )
    return labels, errors


def validate_claim_map(root: Path, *, paper_dir: Path | None = None, graph_path: Path | None = None) -> list[Check]:
    paper = paper_dir or root / "paper"
    map_path = paper / "claim_map.yml"
    if not map_path.exists():
        return [Check("claim-map-present", "FAIL", "claim_map.yml is missing", artifact=str(map_path))]
    try:
        mapping = load_yaml_like(map_path)
    except (OSError, ValueError) as exc:
        return [Check("claim-map-parse", "FAIL", str(exc), artifact=str(map_path))]
    claims = mapping.get("claims", [])
    if not isinstance(claims, list):
        return [Check("claim-map-shape", "FAIL", "claims must be an array", artifact=str(map_path))]
    graph = FactGraph(graph_path or root / "state" / "fact_graph.jsonl")
    verified = graph.verified_ids()
    tex_paths = sorted(paper.rglob("*.tex"))
    labels, label_errors = _formal_labels(tex_paths)
    checks = [Check("formal-labels", "FAIL", error, artifact=error.split(":", 1)[0]) for error in label_errors]
    seen_labels: set[str] = set()
    for label, _, _ in labels:
        if label in seen_labels:
            checks.append(Check("formal-label-duplicate", "FAIL", f"duplicate formal LaTeX label {label}"))
        seen_labels.add(label)
    by_label: dict[str, dict[str, Any]] = {}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            checks.append(Check("claim-map-entry", "FAIL", f"claim #{index + 1} is not an object"))
            continue
        label = claim.get("latex_label")
        fact_id = claim.get("fact_id")
        if not label or not fact_id:
            checks.append(Check("claim-map-entry", "FAIL", f"claim #{index + 1} needs latex_label and fact_id"))
            continue
        if label in by_label:
            checks.append(Check("claim-map-duplicate", "FAIL", f"duplicate mapping for {label}"))
        by_label[label] = claim
        if fact_id not in verified:
            checks.append(Check("claim-map-verified", "FAIL", f"{label} points to non-VERIFIED fact {fact_id}"))
    for label, environment_kind, latex_statement_sha256 in labels:
        if label not in by_label:
            checks.append(
                Check(
                    "claim-map-coverage",
                    "FAIL",
                    (
                        f"formal claim {label} has no claim-map entry; "
                        f"latex_statement_sha256={latex_statement_sha256}"
                    ),
                )
            )
            continue
        fact_id = by_label[label].get("fact_id")
        if fact_id in verified:
            fact = graph.get(fact_id)
            if fact.get("kind") != environment_kind:
                checks.append(
                    Check(
                        "claim-map-kind",
                        "FAIL",
                        f"{label} is a LaTeX {environment_kind} but maps to fact kind {fact.get('kind')}",
                    )
                )
                continue
            claim = by_label[label]
            fact_statement_sha256 = hashlib.sha256(
                str(fact.get("normalized_statement", "")).strip().encode("utf-8")
            ).hexdigest()
            binding_errors: list[str] = []
            if claim.get("latex_statement_sha256") != latex_statement_sha256:
                binding_errors.append(
                    f"LaTeX statement digest is absent or stale; expected {latex_statement_sha256}"
                )
            if claim.get("fact_statement_sha256") != fact_statement_sha256:
                binding_errors.append(
                    f"fact statement digest is absent or stale; expected {fact_statement_sha256}"
                )
            if claim.get("statement_match_verifier_role") != "paper_math_verifier":
                binding_errors.append("statement match lacks paper_math_verifier role")
            match_verifier = claim.get("statement_match_verified_by")
            if (
                not isinstance(match_verifier, str)
                or not match_verifier.strip()
                or match_verifier == fact.get("created_by")
            ):
                binding_errors.append(
                    "statement match verifier is missing or not independent of the fact author"
                )
            match_time = claim.get("statement_match_verified_at")
            valid_match_time = False
            if isinstance(match_time, str) and match_time.strip():
                try:
                    valid_match_time = (
                        datetime.fromisoformat(match_time.replace("Z", "+00:00")).tzinfo
                        is not None
                    )
                except ValueError:
                    valid_match_time = False
            if not valid_match_time:
                binding_errors.append("statement match timestamp is missing or invalid")
            for message in binding_errors:
                checks.append(
                    Check(
                        "claim-map-statement-binding",
                        "FAIL",
                        f"{label}: {message}",
                    )
                )
    if not checks:
        checks.append(
            Check(
                "claim-map",
                "PASS",
                (
                    f"{len(labels)} formal claims map to matching VERIFIED formal facts "
                    "with current paper-math statement bindings"
                ),
            )
        )
    return checks


def validate_bibliography(root: Path, *, paper_dir: Path | None = None) -> list[Check]:
    paper = paper_dir or root / "paper"
    cited: set[str] = set()
    for path in paper.rglob("*.tex"):
        for group in CITE_RE.findall(path.read_text(encoding="utf-8")):
            cited.update(key.strip() for key in group.split(",") if key.strip())
    bib_entries: set[str] = set()
    for path in paper.rglob("*.bib"):
        bib_entries.update(BIB_RE.findall(path.read_text(encoding="utf-8")))
    sources = SourceRegistry(root / "state" / "source_registry.jsonl").all()
    registered = {record.get("bibtex_key") for record in sources if record.get("bibtex_key")}
    by_key: dict[str, list[dict[str, Any]]] = {}
    for record in sources:
        key = record.get("bibtex_key")
        if key:
            by_key.setdefault(key, []).append(record)
    checks: list[Check] = []
    for key in sorted(cited - bib_entries):
        checks.append(Check("citation-defined", "FAIL", f"Citation {key} is missing from bibliography"))
    for key in sorted(cited - registered):
        checks.append(
            Check(
                "citation-registered",
                "WARN",
                f"Bibliography citation {key} has no source-registry bibtex_key",
                severity="WARNING",
            )
        )
    for key in sorted(cited & registered):
        records = by_key[key]
        verified = [record for record in records if record.get("status") == "VERIFIED"]
        if not verified:
            checks.append(
                Check(
                    "citation-source-verified",
                    "FAIL",
                    f"Citation {key} has no VERIFIED source-registry record",
                )
            )
            continue
        if not any(str(record.get("exact_claim_supported", "")).strip() for record in verified):
            checks.append(
                Check(
                    "citation-entailment-record",
                    "FAIL",
                    f"Citation {key} lacks a non-empty exact_claim_supported audit statement",
                )
            )
    if not checks:
        checks.append(Check("bibliography", "PASS", f"{len(cited)} cited keys are defined and registered"))
    return checks


def validate_experiments(
    root: Path,
    *,
    experiments_dir: Path | None = None,
    execute_commands: bool = True,
) -> list[Check]:
    directory = experiments_dir or root / "experiments"
    checks: list[Check] = []
    config_paths = sorted((directory / "configs").glob("*.*")) if (directory / "configs").exists() else []
    for path in config_paths:
        if path.name.startswith("."):
            continue
        try:
            config = load_yaml_like(path)
        except (ValueError, OSError) as exc:
            checks.append(Check("experiment-config", "FAIL", str(exc), artifact=str(path)))
            continue
        try:
            require_valid(config, "experiment", Path(__file__).resolve().parents[1])
        except Exception as exc:
            checks.append(Check("experiment-schema", "FAIL", str(exc), artifact=str(path)))
        command = config.get("reproduction_command")
        declared_config = config.get("config_path")
        if not isinstance(declared_config, str) or not declared_config.strip():
            checks.append(Check("experiment-config-binding", "FAIL", "Experiment lacks config_path", artifact=str(path)))
        else:
            declared_config_path = (root / declared_config).resolve()
            if (
                not declared_config_path.is_relative_to(root.resolve())
                or declared_config_path != path.resolve()
            ):
                checks.append(
                    Check(
                        "experiment-config-binding",
                        "FAIL",
                        f"config_path does not identify this config: {declared_config}",
                        artifact=str(path),
                    )
                )
        if not isinstance(command, str) or not command.strip():
            checks.append(
                Check(
                    "experiment-reproduction",
                    "FAIL",
                    "Experiment config lacks reproduction_command",
                    artifact=str(path),
                )
            )
        for required in ("environment", "parameters", "limitations"):
            if required not in config:
                checks.append(
                    Check(
                        "experiment-metadata",
                        "FAIL",
                        f"Experiment config lacks {required}",
                        artifact=str(path),
                    )
                )
        for field in ("script_path", "report_path"):
            relative = config.get(field)
            if not isinstance(relative, str) or not relative.strip():
                checks.append(Check("experiment-path", "FAIL", f"Experiment config lacks {field}", artifact=str(path)))
                continue
            target = (root / relative).resolve()
            if not target.is_relative_to(root.resolve()):
                checks.append(Check("experiment-path", "FAIL", f"{field} escapes project root", artifact=str(path)))
            elif not target.is_file():
                checks.append(Check("experiment-path", "FAIL", f"{field} does not exist: {relative}", artifact=str(path)))
        for field in ("raw_data_paths", "output_paths"):
            values = config.get(field, [])
            if not isinstance(values, list):
                checks.append(Check("experiment-path", "FAIL", f"{field} must be an array", artifact=str(path)))
                continue
            for relative in values:
                target = (root / str(relative)).resolve()
                if not target.is_relative_to(root.resolve()) or not target.exists():
                    checks.append(Check("experiment-path", "FAIL", f"Missing or out-of-root artifact: {relative}", artifact=str(path)))
        argv: list[str] | None = None
        command_binding_valid = False
        if isinstance(command, str) and command.strip():
            try:
                argv = shlex.split(command, posix=os.name != "nt")
            except ValueError as exc:
                checks.append(Check("experiment-command", "FAIL", str(exc), artifact=str(path)))
            script_relative = config.get("script_path")
            config_relative = config.get("config_path")

            def token_matches(token: str, relative: Any) -> bool:
                if not isinstance(relative, str):
                    return False
                expected = (root / relative).resolve()
                candidate_text = token.split("=", 1)[-1].strip("'\"")
                candidate = Path(candidate_text)
                if not candidate.is_absolute():
                    candidate = root / candidate
                try:
                    return candidate.resolve() == expected
                except OSError:
                    return False

            python_names = {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
            executable_name = Path(argv[0].strip("'\"")).name.lower() if argv else ""
            is_current_python = False
            if argv:
                try:
                    is_current_python = Path(argv[0].strip("'\"")).resolve() == Path(sys.executable).resolve()
                except OSError:
                    is_current_python = False
            script_position = 1 if executable_name in python_names or is_current_python else 0
            script_is_invoked = bool(
                argv
                and len(argv) > script_position
                and token_matches(argv[script_position], script_relative)
            )
            config_is_argument = bool(
                argv
                and any(token_matches(token, config_relative) for token in argv[script_position + 1 :])
            )
            if not script_is_invoked:
                checks.append(
                    Check(
                        "experiment-command-binding",
                        "FAIL",
                        "reproduction_command does not invoke the declared script_path",
                        artifact=str(path),
                    )
                )
            if not config_is_argument:
                checks.append(
                    Check(
                        "experiment-command-binding",
                        "FAIL",
                        "reproduction_command does not reference the declared config_path",
                        artifact=str(path),
                    )
                )
            command_binding_valid = script_is_invoked and config_is_argument
        if execute_commands and argv and command_binding_valid:
            try:
                if argv and argv[0].lower() in {"python", "python3", "py"}:
                    argv[0] = sys.executable
                completed = subprocess.run(
                    argv,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )
                if completed.returncode != 0:
                    checks.append(
                        Check(
                            "experiment-execution",
                            "FAIL",
                            f"Reproduction command exited {completed.returncode}: {(completed.stdout + completed.stderr)[-1000:]}",
                            artifact=str(path),
                        )
                    )
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                checks.append(Check("experiment-execution", "FAIL", str(exc), artifact=str(path)))
    if not checks:
        checks.append(Check("experiments", "PASS", f"{len(config_paths)} experiment configs are reproducible"))
    return checks


def scan_secrets(root: Path) -> list[Check]:
    checks: list[Check] = []
    excluded_parts = {".git", "__pycache__", ".venv"}
    excluded_names = {".env.example", "model_overrides.example.yml"}
    patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"(?im)^\s*(?:OPENAI|ANTHROPIC|OPENROUTER)_API_KEY\s*=\s*[^\s#][^\r\n]*$"),
    ]
    for path in root.rglob("*"):
        if not path.is_file() or excluded_parts.intersection(path.parts) or path.name in excluded_names:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".zip", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(pattern.search(text) for pattern in patterns):
            checks.append(Check("secret-scan", "FAIL", "Possible credential material", artifact=str(path)))
    if not checks:
        checks.append(Check("secret-scan", "PASS", "No credential material detected"))
    return checks


def validate_structure(root: Path) -> list[Check]:
    required = [
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "pyproject.toml",
        "docs/design/source_basis.md",
        "docs/design/architecture.md",
        "docs/mathematical_quality_standard.md",
        "docs/agent_contracts.md",
        "docs/model_routing_guide.md",
        "state/fact_graph.jsonl",
        "state/source_registry.jsonl",
        "paper/main.tex",
        "paper/claim_map.yml",
    ]
    checks = [
        Check("structure", "FAIL", f"Required artifact is missing: {relative}", artifact=relative)
        for relative in required
        if not (root / relative).exists()
    ]
    expected_workflows = [
        "00_project_intake.md",
        "01_problem_formalization.md",
        "02_literature_review.md",
        "03_idea_swarm.md",
        "04_proof_search.md",
        "05_counterexample_search.md",
        "06_fact_verification.md",
        "07_computational_experiment.md",
        "08_formalization.md",
        "09_paper_planning.md",
        "10_paper_writing.md",
        "11_full_paper_review.md",
        "12_revision_cycle.md",
        "13_release_check.md",
        "14_session_handoff.md",
        "15_model_detection.md",
        "16_model_routing.md",
        "17_model_benchmarking.md",
    ]
    for name in expected_workflows:
        if not (root / "workflows" / name).exists():
            checks.append(Check("workflow-structure", "FAIL", f"Missing workflow {name}"))
    if len(list((root / "agents").glob("*.md"))) < 29:
        checks.append(Check("agent-structure", "FAIL", "Expected README plus 28 canonical role documents"))
    if not checks:
        checks.append(Check("structure", "PASS", "Required project structure is present"))
    return checks


def validate_open_issues(root: Path) -> list[Check]:
    ledger = IssueLedger(root / "state" / "issue_ledger.jsonl")
    blockers = [
        row
        for row in ledger.all()
        if row.get("status") in {"OPEN", "IN_PROGRESS"}
        and row.get("severity") in {"FATAL", "MAJOR"}
    ]
    if blockers:
        return [
            Check(
                "open-blocking-issue",
                "FAIL",
                f"{row['status']} {row['severity']} issue blocks release: {row['issue_id']}",
                artifact=row.get("location"),
            )
            for row in blockers
        ]
    return [Check("open-blocking-issue", "PASS", "No OPEN/IN_PROGRESS FATAL or MAJOR issues")]


def validate_runtime_policy(root: Path) -> list[Check]:
    policy = load_json(root / "config" / "runtime_policy.json", default={}) or {}
    live_flags = [
        key
        for key in (
            "allow_paid_probes",
            "allow_cli_subprocess_agents",
            "allow_api_routing",
            "allow_gateway_routing",
        )
        if policy.get(key) is True
    ]
    if not live_flags:
        return [Check("runtime-policy", "PASS", "Paid and external execution paths remain disabled")]
    review = policy.get("external_execution_review") or {}
    approved_by = review.get("approved_by")
    approved_at = review.get("approved_at")
    maximum_cost = review.get("maximum_cost")
    approved_actions = review.get("approved_actions")
    valid_timestamp = False
    if isinstance(approved_at, str) and approved_at.strip():
        try:
            parsed = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
            valid_timestamp = parsed.tzinfo is not None
        except ValueError:
            valid_timestamp = False
    valid_cost = (
        isinstance(maximum_cost, (int, float))
        and not isinstance(maximum_cost, bool)
        and maximum_cost >= 0
    )
    valid_actor = (
        isinstance(approved_by, str)
        and bool(approved_by.strip())
        and approved_by.strip().upper() != "UNKNOWN"
    )
    valid_actions = isinstance(approved_actions, list) and set(live_flags).issubset(
        set(approved_actions)
    )
    if not all(
        (
            review.get("approved") is True,
            valid_actor,
            valid_timestamp,
            valid_cost,
            valid_actions,
        )
    ):
        return [
            Check(
                "runtime-policy",
                "FAIL",
                (
                    f"Live execution flags {live_flags} lack a valid scoped approval: require a non-empty "
                    "approved_by, timezone-aware approved_at, nonnegative numeric maximum_cost, and "
                    "approved_actions covering every live flag"
                ),
                artifact="config/runtime_policy.json",
            )
        ]
    return [
        Check(
            "runtime-policy",
            "WARN",
            f"Reviewed live execution flags are enabled: {live_flags}",
            severity="WARNING",
            artifact="config/runtime_policy.json",
        )
    ]


def validate_persistent_schemas(root: Path) -> list[Check]:
    checks: list[Check] = []
    schema_root = Path(__file__).resolve().parents[1]
    try:
        ModelRegistry.from_path(root / "state" / "model_inventory.json")
    except Exception as exc:
        checks.append(Check("model-record-schema", "FAIL", str(exc)))
    try:
        BudgetManager(root / "state" / "budget_state.json")
    except Exception as exc:
        checks.append(Check("budget-record-schema", "FAIL", str(exc)))
    provider = load_json(root / "state" / "provider_status.json", default={}) or {}
    try:
        require_valid(provider, "provider_status", schema_root)
    except Exception as exc:
        checks.append(Check("provider-record-schema", "FAIL", str(exc)))
    project_state_path = root / "state" / "project_state.json"
    if not project_state_path.exists():
        checks.append(Check("project-state-schema", "FAIL", "state/project_state.json is missing"))
    else:
        try:
            require_valid(load_json(project_state_path), "project_state", schema_root)
        except Exception as exc:
            checks.append(Check("project-state-schema", "FAIL", str(exc)))
    for record in load_jsonl(root / "state" / "routing_log.jsonl"):
        try:
            require_valid(record, "routing_decision", schema_root)
        except Exception as exc:
            checks.append(Check("routing-record-schema", "FAIL", str(exc)))
    for record in load_jsonl(root / "state" / "model_benchmarks.jsonl"):
        try:
            require_valid(record, "benchmark_result", schema_root)
        except Exception as exc:
            checks.append(Check("benchmark-record-schema", "FAIL", str(exc)))
    if not checks:
        checks.append(Check("persistent-schemas", "PASS", "Persistent structured records satisfy their schemas"))
    return checks


def run_unit_test_gate(root: Path) -> Check:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("unit-tests", "FAIL", str(exc))
    output = (completed.stdout + completed.stderr).strip()
    return Check(
        "unit-tests",
        "PASS" if completed.returncode == 0 else "FAIL",
        output[-1500:] or f"unittest exit {completed.returncode}",
    )


def run_paper_compile_gate(root: Path) -> Check:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.compile_paper"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("paper-compile", "FAIL", str(exc))
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {"status": "FAIL", "reason": (completed.stdout + completed.stderr)[-1500:]}
    if completed.returncode != 0 or result.get("status") == "FAIL":
        return Check("paper-compile", "FAIL", json.dumps(result, ensure_ascii=False))
    if result.get("status") == "UNSUPPORTED":
        return Check(
            "paper-compile",
            "WARN",
            "HOST_LIMITED: LaTeX compiler is unavailable",
            severity="WARNING",
        )
    return Check("paper-compile", "PASS", json.dumps(result, ensure_ascii=False))


def build_release_manifest(root: Path) -> dict[str, Any]:
    excluded_parts = {".git", "__pycache__", ".venv"}
    excluded_names = {"release_manifest.json", "release_report.json"}
    excluded_suffixes = {".pyc", ".aux", ".log", ".out", ".fls", ".fdb_latexmk"}
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or excluded_parts.intersection(path.parts)
            or path.name in excluded_names
            or path.suffix.lower() in excluded_suffixes
        ):
            continue
        relative = path.relative_to(root).as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5, check=False
        )
        head = head_result.stdout.strip() if head_result.returncode == 0 else None
        status_result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=5, check=False
        )
        dirty = bool(status_result.stdout.strip()) if status_result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        head, dirty = None, None
    return {
        "snapshot_id": stable_digest(files),
        "created_at": utc_now(),
        "file_count": len(files),
        "files": files,
        "git_head": head,
        "git_dirty": dirty,
        "note": "Content-addressed manifest includes PDFs and excludes only disposable auxiliary build files plus this manifest/report.",
    }


def release_checks(root: Path, *, run_external_gates: bool = True) -> list[Check]:
    checks: list[Check] = []
    checks.extend(validate_structure(root))
    schema_errors = validate_all_schemas(root)
    checks.extend(Check("schemas", "FAIL", error) for error in schema_errors)
    if not schema_errors:
        checks.append(Check("schemas", "PASS", "All schema files parse and declare draft 2020-12"))
    try:
        graph_errors = FactGraph(root / "state" / "fact_graph.jsonl").check()
        checks.extend(Check("fact-graph", "FAIL", error) for error in graph_errors)
        if not graph_errors:
            checks.append(Check("fact-graph", "PASS", "Fact graph invariants hold"))
    except Exception as exc:  # convert malformed persistent state into a release failure
        checks.append(Check("fact-graph", "FAIL", str(exc)))
    try:
        source_errors = SourceRegistry(root / "state" / "source_registry.jsonl").check()
        checks.extend(Check("source-registry", "FAIL", error) for error in source_errors)
        if not source_errors:
            checks.append(Check("source-registry", "PASS", "Source registry records are valid"))
    except Exception as exc:
        checks.append(Check("source-registry", "FAIL", str(exc)))
    try:
        issue_errors = IssueLedger(root / "state" / "issue_ledger.jsonl").check()
        checks.extend(Check("issue-ledger", "FAIL", error) for error in issue_errors)
        if not issue_errors:
            checks.append(Check("issue-ledger", "PASS", "Issue ledger records are valid"))
    except Exception as exc:
        checks.append(Check("issue-ledger", "FAIL", str(exc)))
    checks.extend(validate_claim_map(root))
    bibliography_checks = validate_bibliography(root)
    checks.extend(bibliography_checks)
    for check in bibliography_checks:
        if check.status == "WARN" and check.check_id == "citation-registered":
            checks.append(
                Check(
                    "citation-audit-release",
                    "FAIL",
                    f"Release requires a VERIFIED source-entailment record: {check.message}",
                )
            )
    checks.extend(validate_experiments(root, execute_commands=run_external_gates))
    checks.extend(scan_secrets(root))
    checks.extend(validate_open_issues(root))
    checks.extend(validate_runtime_policy(root))
    checks.extend(validate_persistent_schemas(root))
    if run_external_gates:
        checks.append(run_unit_test_gate(root))
        checks.append(run_paper_compile_gate(root))
    try:
        manifest = build_release_manifest(root)
        if not manifest["files"]:
            checks.append(Check("release-snapshot", "FAIL", "Content-addressed release manifest would be empty"))
        else:
            git_note = (
                f"git head {manifest['git_head']}"
                if manifest["git_head"]
                else "unborn/uncommitted Git repository"
            )
            checks.append(
                Check(
                    "release-snapshot",
                    "PASS",
                    f"Candidate snapshot {manifest['snapshot_id']} covers {manifest['file_count']} files ({git_note})",
                )
            )
        if manifest["git_head"] is None or manifest["git_dirty"] is not False:
            checks.append(
                Check(
                    "release-vcs",
                    "WARN",
                    "No clean Git commit identifies this snapshot; the content-addressed manifest is the release baseline.",
                    severity="WARNING",
                )
            )
    except (OSError, subprocess.SubprocessError) as exc:
        checks.append(Check("release-snapshot", "FAIL", str(exc)))
    inventory = load_json(root / "state" / "model_inventory.json", default={}) or {}
    if not inventory.get("execution_mode"):
        checks.append(Check("model-inventory", "FAIL", "Model inventory has no execution_mode"))
    elif inventory.get("paid_probe_performed"):
        checks.append(Check("model-inventory", "FAIL", "Initialization inventory unexpectedly used a paid probe"))
    else:
        checks.append(Check("model-inventory", "PASS", f"Execution mode: {inventory['execution_mode']}"))
    return checks


def release_report(root: Path, *, run_external_gates: bool = True) -> dict[str, Any]:
    checks = release_checks(root, run_external_gates=run_external_gates)
    failures = [check for check in checks if check.status == "FAIL"]
    warnings = [check for check in checks if check.status == "WARN"]
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": len(failures),
        "warnings": len(warnings),
        "limitations": [
            "AI verification and deterministic gates can miss mathematical errors; VERIFIED is a workflow status, not formal proof or peer review.",
            "A human expert must review core theorems and statement faithfulness; numerical agreement is evidence, not proof.",
        ],
        "checks": [check.as_dict() for check in checks],
    }
