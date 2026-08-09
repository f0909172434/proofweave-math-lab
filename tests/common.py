from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from proofweave.certifiers.lean import environment_fingerprint
from proofweave.pipeline import initialize


class FakeRunner:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def __call__(self, root: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
        if specs:
            self.calls += 1
        results = {
            spec["id"]: "FAILED" if self.fail or "False" in str(spec.get("target")) else "PASSED"
            for spec in specs
        }
        return {
            "outcome": "FAILED" if "FAILED" in results.values() else "PASSED" if specs else "UNSUPPORTED",
            "toolchain_version": "Lean (test 4.32.2)",
            "environment": environment_fingerprint(root),
            "results": results,
            "diagnostics": [],
            "invocations": 1 if specs else 0,
            "source": "-- deterministic fake certificate\n" if specs else "",
        }


class ProjectCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        initialize(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def theorem(
        self,
        claim_id: str = "claim",
        *,
        statement: str = "For every integer x, (x + 1)^2 = x^2 + 2x + 1.",
        assumptions: list[str] | None = None,
        quantifiers: list[str] | None = None,
        dependencies: list[str] | None = None,
        proof: str = "Expand the square and collect terms.",
        target: str | None = "∀ x : ℤ, (x + 1)^2 = x^2 + 2*x + 1",
        tactic: str = "ring",
    ) -> Path:
        assumptions = ["x is an integer"] if assumptions is None else assumptions
        quantifiers = ["for every integer x"] if quantifiers is None else quantifiers
        dependencies = [] if dependencies is None else dependencies
        certificate = ""
        if target is not None:
            certificate = (
                "\n## Certificate\n\n```proofweave-lean\n"
                f"target = {json.dumps(target, ensure_ascii=False)}\n"
                f"tactic = {json.dumps(tactic)}\n```\n"
            )
        text = (
            "+++\n"
            f"claim_id = {json.dumps(claim_id)}\n"
            f"title = {json.dumps(claim_id.title())}\n"
            f"assumptions = {json.dumps(assumptions, ensure_ascii=False)}\n"
            f"quantifiers = {json.dumps(quantifiers, ensure_ascii=False)}\n"
            f"dependencies = {json.dumps(dependencies)}\n"
            "+++\n\n"
            f"## Statement\n\n{statement}\n\n"
            f"## Proof\n\n{proof}\n"
            f"{certificate}"
        )
        path = self.root / f"{claim_id}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        return path
