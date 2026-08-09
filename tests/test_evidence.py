from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from proofweave import certify as certify_module
from proofweave.certifiers.lean import ALLOWED_TACTICS, run_batch
from proofweave.certify import certify
from proofweave.cli import main as cli_main
from proofweave.core import CoreError, hash_file, parse_input, verify_artifacts
from proofweave.pipeline import run_proof
from tests.common import FakeRunner, ProjectCase
from tools.evaluate import (
    CATEGORY_COUNTS,
    _spec,
    evaluate_core,
    evaluate_pack,
    load_corpus,
    write_bundle,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def evidence_backend(root: Path, specs: list[dict[str, object]]) -> dict[str, object]:
    results: dict[str, str] = {}
    for spec in specs:
        identifier = str(spec["id"])
        results[identifier] = "FAILED" if identifier.startswith(("PW-NEG-", "PW-ATK-")) else "PASSED"
    outcome = "FAILED" if "FAILED" in results.values() else "PASSED" if results else "UNSUPPORTED"
    source = "\n".join(f"-- {spec['id']}" for spec in specs) + ("\n" if specs else "")
    return {
        "outcome": outcome,
        "toolchain_version": "Lean (test 4.32.2)",
        "environment": {"fingerprint": "a" * 64},
        "results": results,
        "diagnostics": [],
        "invocations": 1 if specs else 0,
        "source": source,
    }


class CorpusEvidenceTests(unittest.TestCase):
    def test_fixed_corpus_has_42_unique_partitioned_case_ids(self) -> None:
        cases, digest = load_corpus()
        self.assertEqual(42, len(cases))
        self.assertEqual(64, len(digest))
        self.assertEqual(42, len({case["id"] for case in cases}))
        self.assertEqual(
            CATEGORY_COUNTS,
            {category: sum(case["category"] == category for case in cases) for category in CATEGORY_COUNTS},
        )
        positives = [case for case in cases if case["category"] == "positive"]
        self.assertEqual(ALLOWED_TACTICS, {case["tactic"] for case in positives})
        self.assertTrue(all(sum(case["tactic"] == tactic for case in positives) == 2 for tactic in ALLOWED_TACTICS))

    def test_formal_corpus_against_pinned_lean(self) -> None:
        cases, _ = load_corpus()
        formal = [case for case in cases if case["category"] in {"positive", "negative"}]
        result = run_batch(REPOSITORY, [_spec(case) for case in formal])
        if result["outcome"] == "HOST_LIMITED":
            if os.environ.get("PROOFWEAVE_REQUIRE_LEAN") == "1":
                self.fail(f"PROOFWEAVE_REQUIRE_LEAN=1 but pinned Lean/Mathlib is unavailable: {result}")
            self.skipTest("Pinned Lean/Mathlib is unavailable")
        self.assertEqual(1, result["invocations"])
        for case in formal:
            with self.subTest(case_id=case["id"]):
                self.assertEqual(case["expected"], result["results"][case["id"]])

    def test_core_evaluator_writes_complete_self_checking_bundle(self) -> None:
        report = evaluate_core(REPOSITORY, backend=evidence_backend)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(42, report["metrics"]["case_total"])
        self.assertEqual(14, report["metrics"]["positive_passed"])
        self.assertEqual(0, report["metrics"]["false_certifications"])
        self.assertEqual(0, report["metrics"]["attack_acceptances"])
        self.assertEqual(6, report["metrics"]["fail_closed_passed"])
        self.assertEqual({"model": 0, "semantic_extraction": 0, "certifier": 0}, report["metrics"]["cold_warm"]["warm_invocations"])
        with tempfile.TemporaryDirectory() as directory:
            output = write_bundle(report, Path(directory) / "evaluation")
            required = {"evaluation.json", "summary.md", "environment.txt", "SHA256SUMS"}
            self.assertTrue(required.issubset({path.name for path in output.iterdir()}))
            self.assertTrue((output / "certificates" / "formal-corpus.lean").is_file())
            for line in (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
                expected, relative = line.split("  ", 1)
                self.assertEqual(expected, hash_file(output / relative))
            saved = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["corpus_digest"], saved["normalized"]["corpus_digest"])
            self.assertEqual("PASS", saved["normalized"]["result"])


class PackEvidenceTests(unittest.TestCase):
    def test_pack_keeps_runtime_alignment_unconfirmed_and_validates_human_attestation(self) -> None:
        pack = REPOSITORY / "tests" / "packs" / "template" / "pack.toml"
        report = evaluate_pack(pack, REPOSITORY, backend=evidence_backend)
        self.assertEqual("PASS", report["result"])
        self.assertEqual("UNCONFIRMED", report["claims"][0]["runtime_alignment"])
        self.assertEqual("VALID", report["claims"][0]["human_alignment_attestation"])
        self.assertEqual("CERTIFIED", report["claims"][0]["observed_proof_status"])
        self.assertEqual(report["corpus_digest"], report["normalized"]["corpus_digest"])

    def test_verified_pack_fails_closed_when_attestation_is_stale(self) -> None:
        source = REPOSITORY / "tests" / "packs" / "template"
        with tempfile.TemporaryDirectory() as directory:
            pack_root = Path(directory) / "pack"
            shutil.copytree(source, pack_root)
            manifest = pack_root / "pack.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace('research_status = "OPEN"', 'research_status = "VERIFIED"'),
                encoding="utf-8",
            )
            claim = pack_root / "claims" / "theorem.md"
            claim.write_text(claim.read_text(encoding="utf-8").replace("Two plus three", "Adding two and three"), encoding="utf-8")
            report = evaluate_pack(manifest, REPOSITORY, backend=evidence_backend)
            self.assertEqual("FAIL", report["result"])
            self.assertEqual("INVALID", report["claims"][0]["human_alignment_attestation"])
            self.assertFalse(report["metrics"]["verified_gate_passed"])

    def test_verified_status_is_unsupported_without_all_external_review_evidence(self) -> None:
        source = REPOSITORY / "tests" / "packs" / "template"
        with tempfile.TemporaryDirectory() as directory:
            pack_root = Path(directory) / "pack"
            shutil.copytree(source, pack_root)
            manifest = pack_root / "pack.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace('research_status = "OPEN"', 'research_status = "VERIFIED"'),
                encoding="utf-8",
            )
            report = evaluate_pack(manifest, REPOSITORY, backend=evidence_backend)
            self.assertEqual("VALID", report["claims"][0]["human_alignment_attestation"])
            self.assertTrue(report["metrics"]["verified_prerequisites_observed"])
            self.assertFalse(report["metrics"]["verified_gate_passed"])
            self.assertIn("cold-start replay", report["metrics"]["verified_gate_reason"])
            self.assertEqual("FAIL", report["result"])

    def test_alignment_attestation_requires_identity_and_timezone(self) -> None:
        source = REPOSITORY / "tests" / "packs" / "template"
        replacements = (
            ('attestation_id = "PW-ALIGN-TEMPLATE-01"', 'attestation_id = ""'),
            ('reviewer = "REPLACE-WITH-HUMAN-REVIEWER"', 'reviewer = ""'),
            ('reviewed_at = "1970-01-01T00:00:00Z"', 'reviewed_at = "not-a-timestamp"'),
            ('reviewed_at = "1970-01-01T00:00:00Z"', 'reviewed_at = "1970-01-01T00:00:00"'),
        )
        for old, new in replacements:
            with self.subTest(replacement=new), tempfile.TemporaryDirectory() as directory:
                pack_root = Path(directory) / "pack"
                shutil.copytree(source, pack_root)
                attestation = pack_root / "alignment" / "pack-template-claim.toml"
                attestation.write_text(
                    attestation.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
                )
                report = evaluate_pack(pack_root / "pack.toml", REPOSITORY, backend=evidence_backend)
                self.assertEqual("INVALID", report["claims"][0]["human_alignment_attestation"])

    def test_pack_path_traversal_is_rejected(self) -> None:
        source = REPOSITORY / "tests" / "packs" / "template"
        with tempfile.TemporaryDirectory() as directory:
            pack_root = Path(directory) / "pack"
            shutil.copytree(source, pack_root)
            manifest = pack_root / "pack.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace('path = "claims/theorem.md"', 'path = "../../outside.md"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "escapes pack or is missing"):
                evaluate_pack(manifest, REPOSITORY, backend=evidence_backend)

    def test_pack_manifest_rejects_empty_or_wrong_typed_identity_fields(self) -> None:
        source = REPOSITORY / "tests" / "packs" / "template"
        replacements = (
            ('title = "Minimal hash-bound theorem evidence pack"', 'title = ""'),
            ('sources = ["Template demonstration; replace with primary and independent sources."]', 'sources = [""]'),
            ('id = "pack-template-claim"', 'id = []'),
            ('path = "claims/theorem.md"', 'path = ""'),
            ('alignment_attestation = "alignment/pack-template-claim.toml"', 'alignment_attestation = ""'),
        )
        for old, new in replacements:
            with self.subTest(replacement=new), tempfile.TemporaryDirectory() as directory:
                pack_root = Path(directory) / "pack"
                shutil.copytree(source, pack_root)
                manifest = pack_root / "pack.toml"
                manifest.write_text(
                    manifest.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
                )
                with self.assertRaises(ValueError):
                    evaluate_pack(manifest, REPOSITORY, backend=evidence_backend)


class ContractAndHashTests(ProjectCase):
    def test_three_generated_contract_instances_validate_against_schemas(self) -> None:
        result = run_proof(self.theorem(), root=self.root, runner=FakeRunner())
        claim_path = next((self.root / "workspace" / "claims").glob("*.json"))
        run_path = Path(result["artifact_directory"]) / "run.json"
        instances = {
            "claim.schema.json": json.loads(claim_path.read_text(encoding="utf-8")),
            "proof_ir.schema.json": parse_input(self.theorem(target=None))["proof_ir"],
            "run.schema.json": json.loads(run_path.read_text(encoding="utf-8")),
        }
        for schema_name, instance in instances.items():
            with self.subTest(schema=schema_name):
                schema = json.loads((REPOSITORY / "schemas" / schema_name).read_text(encoding="utf-8"))
                Draft202012Validator(schema).validate(instance)

    def test_certificate_key_binds_every_public_key_material_field(self) -> None:
        parsed = parse_input(self.theorem())

        def runner(version: str = "Lean A", fingerprint: str = "a" * 64):
            def call(root: Path, specs: list[dict[str, object]]) -> dict[str, object]:
                return {
                    "outcome": "PASSED", "toolchain_version": version,
                    "environment": {"fingerprint": fingerprint},
                    "results": {spec["id"]: "PASSED" for spec in specs}, "diagnostics": [],
                    "invocations": 1, "source": "-- key fixture\n",
                }
            return call

        def key(value: dict[str, object], dependencies: dict[str, str], backend=None) -> str:
            return certify(
                self.root, value, dependency_digests=dependencies, dependencies_ready=True,
                runner=backend or runner(),
            )["certificate"]["cache_key"]

        base_dependencies = {"dep": "d" * 64}
        base = key(parsed, base_dependencies)
        variants: list[str] = []
        for field, replacement in (
            ("statement", "Changed statement"),
            ("quantifiers", ["for some integer x"]),
            ("assumptions", ["x is positive"]),
        ):
            changed = copy.deepcopy(parsed)
            changed[field] = replacement
            variants.append(key(changed, base_dependencies))
        changed = copy.deepcopy(parsed)
        changed["top_certificate"]["target"] = "True"
        variants.append(key(changed, base_dependencies))
        changed = copy.deepcopy(parsed)
        changed["top_certificate"]["tactic"] = "norm_num"
        variants.append(key(changed, base_dependencies))
        changed = copy.deepcopy(parsed)
        changed["top_certificate"]["exact"] = "earlier-node"
        variants.append(key(changed, base_dependencies))
        slow = parse_input(self.theorem(
            proof="""### premise [semantic]
Use the premise.

### calculation [computational]
Depends: premise
Calculate.
```proofweave-lean
target = "True"
tactic = "norm_num"
```""",
            target=None,
        ))
        variants.append(key(slow, base_dependencies))
        changed = copy.deepcopy(slow)
        changed["proof_ir"]["nodes"][0]["text"] = "Changed semantic text."
        variants.append(key(changed, base_dependencies))
        changed = copy.deepcopy(slow)
        changed["proof_ir"]["nodes"][1]["depends_on"] = []
        variants.append(key(changed, base_dependencies))
        changed = copy.deepcopy(slow)
        changed["proof_ir"]["nodes"][1]["certificate"]["target"] = "1 = 1"
        variants.append(key(changed, base_dependencies))
        variants.append(key(parsed, {"dep": "e" * 64}))
        variants.append(key(parsed, base_dependencies, runner("Lean B")))
        variants.append(key(parsed, base_dependencies, runner(fingerprint="b" * 64)))
        with patch.object(certify_module, "CERTIFIER_NAME", "other"):
            variants.append(key(parsed, base_dependencies))
        with patch.object(certify_module, "CERTIFIER_VERSION", "other"):
            variants.append(key(parsed, base_dependencies))
        self.assertTrue(all(value != base for value in variants))
        self.assertEqual(len(variants), len(set(variants)))

    def test_claim_and_run_hashes_and_deterministic_replay_match(self) -> None:
        first = run_proof(self.theorem(), root=self.root, runner=FakeRunner())
        claim = json.loads(next((self.root / "workspace" / "claims").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(first["statement_hash"], claim["statement_hash"])
        self.assertEqual(first["run_id"], first["cache_key"])
        self.assertEqual(first["certificate"]["cache_key"], claim["certificate_digest"])
        with tempfile.TemporaryDirectory() as directory:
            other = Path(directory)
            from proofweave.pipeline import initialize
            initialize(other)
            source = other / "claim.md"
            source.write_bytes(self.theorem().read_bytes())
            second = run_proof(source, root=other, runner=FakeRunner())
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["certificate"]["cache_key"], second["certificate"]["cache_key"])

    def test_artifact_path_traversal_is_detected(self) -> None:
        outside = self.root.parent / "outside-evidence.txt"
        errors = verify_artifacts(self.root, {"artifacts": {str(outside): hashlib.sha256(b"").hexdigest()}})
        self.assertTrue(any("escapes project root" in error for error in errors))

    def test_cli_exit_codes_cover_certified_failed_partial_and_input_error(self) -> None:
        for proof_status, expected in (("CERTIFIED", 0), ("FAILED", 1), ("PARTIAL", 2)):
            with self.subTest(status=proof_status), patch(
                "proofweave.cli.run_proof", return_value={"proof_status": proof_status}
            ), redirect_stdout(io.StringIO()):
                self.assertEqual(expected, cli_main(["run", "claim.md"]))
        with patch("proofweave.cli.run_proof", side_effect=CoreError("bad input")), redirect_stdout(io.StringIO()):
            self.assertEqual(1, cli_main(["run", "claim.md"]))
