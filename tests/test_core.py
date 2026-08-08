from __future__ import annotations

from proofweave.core import CoreError, parse_input
from tests.common import ProjectCase


class CoreParsingTests(ProjectCase):
    def test_structured_markdown_preserves_statement_fields(self) -> None:
        parsed = parse_input(self.theorem())
        self.assertEqual("claim", parsed["claim_id"])
        self.assertEqual(["x is an integer"], parsed["assumptions"])
        self.assertEqual(["for every integer x"], parsed["quantifiers"])
        self.assertEqual("ring", parsed["top_certificate"]["tactic"])

    def test_proof_dag_cycle_is_rejected(self) -> None:
        proof = """### a [semantic]
Depends: b
First.

### b [bridge]
Depends: a
Second."""
        with self.assertRaisesRegex(CoreError, "Proof dependency cycle"):
            parse_input(self.theorem(proof=proof, target=None))

    def test_alias_requires_a_target(self) -> None:
        with self.assertRaisesRegex(CoreError, "requires `Alias"):
            parse_input(self.theorem(proof="### alias [alias]\nA name.", target=None))

    def test_unknown_front_matter_is_rejected(self) -> None:
        path = self.theorem()
        path.write_text(path.read_text(encoding="utf-8").replace("title =", "owner = \"x\"\ntitle ="), encoding="utf-8")
        with self.assertRaisesRegex(CoreError, "Unknown front matter"):
            parse_input(path)
