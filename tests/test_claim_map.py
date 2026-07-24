from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mathlab.fact_graph import FactGraph
from mathlab.validation import validate_bibliography, validate_claim_map
from tests.common import accept_report, fact


class ClaimMapTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        root = Path(temp)
        (root / "paper").mkdir(parents=True)
        (root / "state").mkdir(parents=True)
        (root / "state" / "fact_graph.jsonl").write_text("", encoding="utf-8")
        (root / "state" / "source_registry.jsonl").write_text("", encoding="utf-8")
        return root

    def test_theorem_without_claim_map_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            (root / "paper" / "main.tex").write_text("\\begin{theorem}\\label{thm:x}X\\end{theorem}", encoding="utf-8")
            checks = validate_claim_map(root)
            self.assertTrue(any(check.status == "FAIL" for check in checks))

    def test_latex_whitespace_and_comments_cannot_hide_formal_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            (root / "paper" / "main.tex").write_text(
                """\\begin% a valid TeX comment
 {theorem}\\label {thm:space}X\\end {theorem}
\\begin
 {lemma}\\label{lem:space}L\\end {lemma}
\\begin {proposition}\\label{prop:space}P\\end {proposition}
\\begin {corollary}\\label{cor:space}C\\end {corollary}
""",
                encoding="utf-8",
            )
            (root / "paper" / "claim_map.yml").write_text("claims: []\n", encoding="utf-8")
            checks = validate_claim_map(root)
            uncovered = [c for c in checks if c.check_id == "claim-map-coverage"]
            self.assertEqual(4, len(uncovered))

    def test_locally_declared_theorem_alias_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            (root / "paper" / "main.tex").write_text(
                "\\newtheorem{mainresult}{Theorem}\n"
                "\\begin{mainresult}\\label{thm:alias}X\\end{mainresult}\n",
                encoding="utf-8",
            )
            (root / "paper" / "claim_map.yml").write_text("claims: []\n", encoding="utf-8")
            checks = validate_claim_map(root)
            self.assertTrue(any(c.check_id == "claim-map-coverage" and "thm:alias" in c.message for c in checks))

    def test_claim_map_to_non_verified_fact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            FactGraph(root / "state" / "fact_graph.jsonl").add(fact("f1"))
            (root / "paper" / "main.tex").write_text("\\begin{theorem}\\label{thm:x}X\\end{theorem}", encoding="utf-8")
            (root / "paper" / "claim_map.yml").write_text("claims:\n  - latex_label: thm:x\n    fact_id: f1\n", encoding="utf-8")
            checks = validate_claim_map(root)
            self.assertTrue(any(check.status == "FAIL" and "non-VERIFIED" in check.message for check in checks))

    def test_unregistered_bibliography_citation_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            (root / "paper" / "main.tex").write_text("See \\cite{known}.", encoding="utf-8")
            (root / "paper" / "references.bib").write_text("@article{known, title={X}}", encoding="utf-8")
            checks = validate_bibliography(root)
            self.assertTrue(any(check.status == "WARN" and "source-registry" in check.message for check in checks))

    def test_spaced_citation_command_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            (root / "paper" / "main.tex").write_text("See \\cite [p. 1] {known}.", encoding="utf-8")
            (root / "paper" / "references.bib").write_text("@article{known, title={X}}", encoding="utf-8")
            checks = validate_bibliography(root)
            self.assertTrue(any(check.check_id == "citation-registered" for check in checks))

    def test_verified_numerical_evidence_cannot_back_latex_theorem(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            malicious = FactGraph._defaulted(fact("f1"))
            malicious["kind"] = "numerical_evidence"
            malicious["status"] = malicious["verification_status"] = "VERIFIED"
            (root / "state" / "fact_graph.jsonl").write_text(
                json.dumps(malicious) + "\n", encoding="utf-8"
            )
            (root / "paper" / "main.tex").write_text(
                "\\begin{theorem}\\label{thm:x}X\\end{theorem}", encoding="utf-8"
            )
            (root / "paper" / "claim_map.yml").write_text(
                "claims:\n  - latex_label: thm:x\n    fact_id: f1\n", encoding="utf-8"
            )
            checks = validate_claim_map(root)
            self.assertTrue(any(check.check_id == "claim-map-kind" and check.status == "FAIL" for check in checks))

    def test_claim_map_digest_binding_detects_manuscript_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            graph = FactGraph(root / "state" / "fact_graph.jsonl")
            theorem = fact("f1")
            theorem["kind"] = "theorem"
            graph.add(theorem)
            graph.promote(
                "f1",
                verifier="theorem-reviewer",
                verifier_role="theorem_verifier",
                report=accept_report("f1", "theorem-reviewer"),
            )
            latex_hash = __import__("hashlib").sha256(b"X").hexdigest()
            fact_hash = __import__("hashlib").sha256(b"statement-f1").hexdigest()
            (root / "paper" / "main.tex").write_text(
                "\\begin{theorem}\\label{thm:x}X\\end{theorem}", encoding="utf-8"
            )
            (root / "paper" / "claim_map.yml").write_text(
                "\n".join(
                    [
                        "claims:",
                        "  - latex_label: thm:x",
                        "    fact_id: f1",
                        f"    latex_statement_sha256: {latex_hash}",
                        f"    fact_statement_sha256: {fact_hash}",
                        "    statement_match_verifier_role: paper_math_verifier",
                        "    statement_match_verified_by: paper-reviewer",
                        "    statement_match_verified_at: 2026-07-24T00:00:00Z",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            initial = validate_claim_map(root)
            self.assertFalse(any(check.status == "FAIL" for check in initial))
            (root / "paper" / "main.tex").write_text(
                "\\begin{theorem}\\label{thm:x}Y\\end{theorem}", encoding="utf-8"
            )
            changed = validate_claim_map(root)
            self.assertTrue(
                any(check.check_id == "claim-map-statement-binding" for check in changed)
            )


if __name__ == "__main__":
    unittest.main()
