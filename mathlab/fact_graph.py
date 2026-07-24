from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .errors import IntegrityError, ValidationError
from .io import load_jsonl, save_jsonl, utc_now
from .schemas import require_valid


FACT_STATUSES = {
    "DRAFT",
    "PROPOSED",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED",
    "UNCERTAIN",
    "REVOKED",
    "SUPERSEDED",
}
FACT_KINDS = {
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "conjecture",
    "heuristic",
    "numerical_evidence",
    "empirical_observation",
    "refuted_claim",
    "open_gap",
    "unknown",
}
FORMAL_KINDS = {"theorem", "lemma", "proposition", "corollary"}
PROMOTABLE_KINDS = FORMAL_KINDS | {"refuted_claim"}
SCHEMA_ROOT = Path(__file__).resolve().parents[1]


class FactGraph:
    """Persistent fact DAG with verifier-only promotion and revocation cascade."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._facts: dict[str, dict[str, Any]] = {}
        for record in load_jsonl(self.path):
            fact_id = record.get("fact_id", record.get("id"))
            if not fact_id:
                raise IntegrityError("Fact record is missing fact_id")
            if fact_id in self._facts:
                raise IntegrityError(f"Duplicate fact_id: {fact_id}")
            record["fact_id"] = fact_id
            record.pop("id", None)
            self._facts[fact_id] = record

    @classmethod
    def at_project(cls, root: Path) -> "FactGraph":
        return cls(root / "state" / "fact_graph.jsonl")

    def all(self) -> list[dict[str, Any]]:
        return [deepcopy(self._facts[key]) for key in sorted(self._facts)]

    def get(self, fact_id: str) -> dict[str, Any]:
        if fact_id not in self._facts:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        return deepcopy(self._facts[fact_id])

    def _persist(self) -> None:
        save_jsonl(self.path, (self._facts[key] for key in sorted(self._facts)))

    @staticmethod
    def _defaulted(record: dict[str, Any]) -> dict[str, Any]:
        value = deepcopy(record)
        if "id" in value and "fact_id" not in value:
            value["fact_id"] = value.pop("id")
        value.setdefault("title", value.get("statement", "")[:80])
        value.setdefault("normalized_statement", value.get("statement", "").strip())
        value.setdefault("kind", "unknown")
        value.setdefault("assumptions", [])
        value.setdefault("quantifiers", [])
        value.setdefault("mathematical_domain", "UNKNOWN")
        value.setdefault("proof", "")
        value.setdefault("dependencies", [])
        value.setdefault("source_dependencies", [])
        value.setdefault("created_by", "UNKNOWN")
        value.setdefault("checked_by", None)
        value.setdefault("verification_status", value.get("status", "DRAFT"))
        value.setdefault("verification_report", None)
        value.setdefault("confidence", {"level": "low", "reason": "NOT VERIFIED"})
        value.setdefault("tags", [])
        value.setdefault("created_at", utc_now())
        value.setdefault("verified_at", None)
        value.setdefault("supersedes", [])
        value.setdefault("revoked_reason", None)
        value.setdefault("affected_descendants", [])
        value.setdefault("manuscript_locations", [])
        value.setdefault("experiment_dependencies", [])
        value.setdefault("formalization_status", "NOT_ATTEMPTED")
        value.setdefault("status", value.get("verification_status", "DRAFT"))
        return value

    def _validate_record(self, record: dict[str, Any], *, adding: bool = False) -> None:
        required = {
            "fact_id",
            "title",
            "statement",
            "normalized_statement",
            "kind",
            "assumptions",
            "quantifiers",
            "mathematical_domain",
            "proof",
            "dependencies",
            "source_dependencies",
            "created_by",
            "verification_status",
        }
        missing = sorted(key for key in required if key not in record)
        if missing:
            raise ValidationError(f"Fact is missing required fields: {', '.join(missing)}")
        require_valid(record, "fact", SCHEMA_ROOT)
        fact_id = record["fact_id"]
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise ValidationError("fact_id must be a non-empty string")
        if adding and fact_id in self._facts:
            raise IntegrityError(f"Duplicate fact_id: {fact_id}")
        if record.get("status") not in FACT_STATUSES:
            raise ValidationError(f"Invalid fact status: {record.get('status')}")
        if record.get("verification_status") != record.get("status"):
            raise IntegrityError("status and verification_status must agree")
        if record.get("kind") not in FACT_KINDS:
            raise ValidationError(f"Invalid fact kind: {record.get('kind')}")
        if not isinstance(record.get("statement"), str) or not record["statement"].strip():
            raise ValidationError("statement must be non-empty")
        for field in (
            "assumptions",
            "quantifiers",
            "dependencies",
            "source_dependencies",
            "tags",
            "supersedes",
            "affected_descendants",
            "manuscript_locations",
            "experiment_dependencies",
        ):
            if not isinstance(record.get(field), list):
                raise ValidationError(f"{field} must be an array")
        if record["kind"] in FORMAL_KINDS and not record["assumptions"]:
            raise ValidationError("Formal claims require explicit assumptions (use an explicit 'none')")
        if fact_id in record["dependencies"]:
            raise IntegrityError("A fact cannot depend on itself")
        for dependency in record["dependencies"]:
            if dependency not in self._facts:
                raise IntegrityError(f"Unknown dependency {dependency!r}")
            if record["status"] in {"PROPOSED", "UNDER_REVIEW", "VERIFIED"}:
                status = self._facts[dependency].get("status")
                if status != "VERIFIED":
                    raise IntegrityError(
                        f"Formal dependency {dependency!r} is {status}, not VERIFIED"
                    )
                if record["kind"] in FORMAL_KINDS and self._facts[dependency].get("kind") not in FORMAL_KINDS:
                    raise IntegrityError(
                        f"Formal claim cannot depend on non-proof evidence kind {self._facts[dependency].get('kind')!r} ({dependency})"
                    )
        if record["status"] in {"PROPOSED", "UNDER_REVIEW", "VERIFIED"}:
            self._validate_source_dependencies(record)
        if record["status"] == "VERIFIED":
            if record["kind"] not in PROMOTABLE_KINDS:
                raise IntegrityError(
                    f"Evidence kind {record['kind']!r} cannot receive truth-layer VERIFIED status"
                )
            if not record.get("checked_by") or record.get("checked_by") == record.get("created_by"):
                raise IntegrityError("VERIFIED facts require an independent checker")
            report = record.get("verification_report") or {}
            self._validate_accept_report(record, report, verifier=record.get("checked_by"))
            if not record.get("verified_at"):
                raise IntegrityError("VERIFIED facts require verified_at")

    def _validate_source_dependencies(self, record: dict[str, Any]) -> None:
        source_ids = set(record.get("source_dependencies", []))
        if not source_ids:
            return
        registry_path = self.path.parent / "source_registry.jsonl"
        records = load_jsonl(registry_path)
        statuses = {
            value.get("source_id", value.get("id")): value.get("status") for value in records
        }
        for source_id in sorted(source_ids):
            if source_id not in statuses:
                raise IntegrityError(f"Unknown source dependency {source_id!r}")
            if statuses[source_id] != "VERIFIED":
                raise IntegrityError(
                    f"Source dependency {source_id!r} is {statuses[source_id]}, not VERIFIED"
                )

    def _validate_accept_report(
        self, record: dict[str, Any], report: dict[str, Any], *, verifier: str | None
    ) -> None:
        fact_id = record["fact_id"]
        if report.get("outcome") != "ACCEPT":
            raise IntegrityError("VERIFIED facts require an ACCEPT verification report")
        if report.get("fact_id") != fact_id:
            raise IntegrityError("Verification report fact_id does not match the promoted fact")
        if report.get("verifier") != verifier:
            raise IntegrityError("Verification report verifier does not match checked_by")
        if report.get("verifier_role") != "theorem_verifier":
            raise IntegrityError("Verification report must identify theorem_verifier role")
        if report.get("cold_start") is not True:
            raise IntegrityError("Verification report must attest cold_start")
        checklist = report.get("checklist")
        if not isinstance(checklist, list) or not checklist:
            raise ValidationError("ACCEPT report requires a non-empty checklist")
        invalid = [
            item for item in checklist if not isinstance(item, dict) or item.get("result") != "PASS"
        ]
        if invalid:
            raise IntegrityError("ACCEPT report checklist must contain only PASS results")
        if report.get("fatal_gap"):
            raise IntegrityError("ACCEPT report cannot contain a fatal_gap")
        self._validate_report_coverage(record, report)

    def _validate_report_coverage(self, record: dict[str, Any], report: dict[str, Any]) -> None:
        fact_id = record["fact_id"]
        expected_dependencies = (
            set(self.dependency_closure(fact_id))
            if fact_id in self._facts
            else set(record.get("dependencies", []))
        )
        checked_dependencies = set(report.get("dependencies_checked", []))
        if not expected_dependencies.issubset(checked_dependencies):
            missing = sorted(expected_dependencies - checked_dependencies)
            raise IntegrityError(f"Verification report did not check dependency closure: {missing}")
        expected_sources = set(record.get("source_dependencies", []))
        for dependency in expected_dependencies:
            expected_sources.update(self._facts[dependency].get("source_dependencies", []))
        checked_sources = set(report.get("sources_checked", []))
        if not expected_sources.issubset(checked_sources):
            missing = sorted(expected_sources - checked_sources)
            raise IntegrityError(f"Verification report did not check source dependencies: {missing}")

    def _graph_with(self, record: dict[str, Any] | None = None) -> dict[str, list[str]]:
        graph = {key: list(value.get("dependencies", [])) for key, value in self._facts.items()}
        if record is not None:
            graph[record["fact_id"]] = list(record.get("dependencies", []))
        return graph

    @staticmethod
    def _cycle(graph: dict[str, list[str]]) -> list[str] | None:
        state: dict[str, int] = {}
        trail: list[str] = []

        def visit(node: str) -> list[str] | None:
            state[node] = 1
            trail.append(node)
            for dependency in graph.get(node, []):
                if state.get(dependency) == 1:
                    start = trail.index(dependency)
                    return trail[start:] + [dependency]
                if state.get(dependency, 0) == 0:
                    found = visit(dependency)
                    if found:
                        return found
            trail.pop()
            state[node] = 2
            return None

        for node in graph:
            if state.get(node, 0) == 0:
                found = visit(node)
                if found:
                    return found
        return None

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        value = self._defaulted(record)
        if value["status"] == "VERIFIED":
            raise IntegrityError("Use promote(); facts cannot enter the graph pre-VERIFIED")
        self._validate_record(value, adding=True)
        cycle = self._cycle(self._graph_with(value))
        if cycle:
            raise IntegrityError(f"Dependency cycle: {' -> '.join(cycle)}")
        self._facts[value["fact_id"]] = value
        self._persist()
        return deepcopy(value)

    def set_under_review(self, fact_id: str) -> dict[str, Any]:
        fact = self._facts.get(fact_id)
        if fact is None:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        if fact["status"] != "PROPOSED":
            raise IntegrityError("Only PROPOSED facts can enter UNDER_REVIEW")
        fact["status"] = fact["verification_status"] = "UNDER_REVIEW"
        self._validate_record(fact)
        self._persist()
        return deepcopy(fact)

    def add_dependency(self, fact_id: str, dependency_id: str) -> dict[str, Any]:
        """Add one edge after checking existence, truth status and acyclicity."""

        if fact_id not in self._facts or dependency_id not in self._facts:
            missing = fact_id if fact_id not in self._facts else dependency_id
            raise ValidationError(f"Unknown fact_id: {missing}")
        fact = self._facts[fact_id]
        if dependency_id in fact.get("dependencies", []):
            return deepcopy(fact)
        if fact["status"] in {"PROPOSED", "UNDER_REVIEW", "VERIFIED"} and self._facts[
            dependency_id
        ]["status"] != "VERIFIED":
            raise IntegrityError(f"Formal dependency {dependency_id!r} is not VERIFIED")
        candidate = deepcopy(fact)
        candidate.setdefault("dependencies", []).append(dependency_id)
        cycle = self._cycle(self._graph_with(candidate))
        if cycle:
            raise IntegrityError(f"Dependency cycle: {' -> '.join(cycle)}")
        self._facts[fact_id] = candidate
        self._validate_record(candidate)
        self._persist()
        return deepcopy(candidate)

    def promote(
        self,
        fact_id: str,
        *,
        verifier: str,
        verifier_role: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        fact = self._facts.get(fact_id)
        if fact is None:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        if verifier_role != "theorem_verifier":
            raise IntegrityError("Only theorem_verifier may promote a fact")
        if fact["status"] not in {"PROPOSED", "UNDER_REVIEW"}:
            raise IntegrityError(f"Cannot promote a fact in status {fact['status']}")
        if not verifier or verifier == fact.get("created_by"):
            raise IntegrityError("The proof worker may not verify its own claim")
        if fact.get("kind") not in PROMOTABLE_KINDS:
            raise IntegrityError(
                f"Evidence kind {fact.get('kind')!r} cannot be promoted to truth-layer VERIFIED"
            )
        self._validate_source_dependencies(fact)
        require_valid(report, "verification", SCHEMA_ROOT)
        self._validate_accept_report(fact, report, verifier=verifier)
        for dependency in fact.get("dependencies", []):
            if self._facts[dependency].get("status") != "VERIFIED":
                raise IntegrityError(f"Dependency {dependency} is no longer VERIFIED")
        fact["status"] = fact["verification_status"] = "VERIFIED"
        fact["checked_by"] = verifier
        fact["verification_report"] = deepcopy(report)
        fact["verified_at"] = utc_now()
        self._validate_record(fact)
        self._persist()
        return deepcopy(fact)

    def review_failure(
        self, fact_id: str, *, verifier: str, outcome: str, report: dict[str, Any]
    ) -> dict[str, Any]:
        if outcome not in {"REJECT", "UNCERTAIN"}:
            raise ValidationError("Review outcome must be REJECT or UNCERTAIN")
        fact = self._facts.get(fact_id)
        if fact is None:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        if fact["status"] not in {"PROPOSED", "UNDER_REVIEW"}:
            raise IntegrityError(f"Cannot review a fact in status {fact['status']}")
        if verifier == fact.get("created_by"):
            raise IntegrityError("A worker cannot review its own claim")
        if report.get("outcome") != outcome:
            raise IntegrityError("Review outcome does not match the untouched verification report")
        submitted = deepcopy(report)
        require_valid(submitted, "verification", SCHEMA_ROOT)
        if submitted.get("fact_id") != fact_id or submitted.get("verifier") != verifier:
            raise IntegrityError("Review report identity does not match the reviewed fact/verifier")
        if submitted.get("verifier_role") != "theorem_verifier" or submitted.get("cold_start") is not True:
            raise IntegrityError("Review report must come from a cold-start theorem_verifier")
        self._validate_report_coverage(fact, submitted)
        fact["status"] = fact["verification_status"] = (
            "REJECTED" if outcome == "REJECT" else "UNCERTAIN"
        )
        fact["checked_by"] = verifier
        fact["verification_report"] = submitted
        self._persist()
        return deepcopy(fact)

    def descendants(self, fact_id: str) -> list[str]:
        if fact_id not in self._facts:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        reverse: dict[str, list[str]] = {key: [] for key in self._facts}
        for child, fact in self._facts.items():
            for parent in fact.get("dependencies", []):
                reverse.setdefault(parent, []).append(child)
        seen: set[str] = set()
        stack = list(reverse.get(fact_id, []))
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(reverse.get(node, []))
        return sorted(seen)

    def dependency_closure(self, fact_id: str) -> list[str]:
        if fact_id not in self._facts:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        seen: set[str] = set()
        stack = list(self._facts[fact_id].get("dependencies", []))
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self._facts[node].get("dependencies", []))
        return sorted(seen)

    def revoke(self, fact_id: str, *, reason: str, revoked_by: str) -> list[str]:
        if not reason.strip():
            raise ValidationError("Revocation requires a reason")
        if fact_id not in self._facts:
            raise ValidationError(f"Unknown fact_id: {fact_id}")
        affected = [fact_id, *self.descendants(fact_id)]
        descendants = affected[1:]
        timestamp = utc_now()
        report = {
            "revoked_fact_id": fact_id,
            "reason": reason,
            "revoked_by": revoked_by,
            "revoked_at": timestamp,
            "affected_facts": affected,
            "manuscript_locations": {
                current: list(self._facts[current].get("manuscript_locations", []))
                for current in affected
                if self._facts[current].get("manuscript_locations")
            },
            "experiment_dependencies": {
                current: list(self._facts[current].get("experiment_dependencies", []))
                for current in affected
                if self._facts[current].get("experiment_dependencies")
            },
            "source_dependencies": {
                current: list(self._facts[current].get("source_dependencies", []))
                for current in affected
                if self._facts[current].get("source_dependencies")
            },
        }
        for current in affected:
            fact = self._facts[current]
            fact["status"] = fact["verification_status"] = "REVOKED"
            fact["revoked_reason"] = (
                reason if current == fact_id else f"Upstream fact {fact_id} revoked: {reason}"
            )
            fact["revoked_by"] = revoked_by
            fact["revoked_at"] = timestamp
            fact["affected_descendants"] = self.descendants(current)
        self._facts[fact_id]["affected_descendants"] = descendants
        self._facts[fact_id]["revocation_report"] = report
        for current in affected:
            self._validate_record(self._facts[current])
        self._persist()
        return affected

    def check(self) -> list[str]:
        errors: list[str] = []
        for fact_id, record in self._facts.items():
            try:
                self._validate_record(record)
            except (ValidationError, IntegrityError) as exc:
                errors.append(f"{fact_id}: {exc}")
        cycle = self._cycle(self._graph_with())
        if cycle:
            errors.append(f"Dependency cycle: {' -> '.join(cycle)}")
        return errors

    def verified_ids(self) -> set[str]:
        return {key for key, value in self._facts.items() if value.get("status") == "VERIFIED"}
