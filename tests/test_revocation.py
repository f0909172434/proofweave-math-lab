from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mathlab.fact_graph import FactGraph
from tests.common import accept_report, fact


class RevocationTests(unittest.TestCase):
    def test_revocation_marks_all_transitive_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            graph = FactGraph(Path(temp) / "facts.jsonl")
            graph.add(fact("a"))
            graph.promote("a", verifier="v-a", verifier_role="theorem_verifier", report=accept_report("a", "v-a"))
            value_b = fact("b", dependencies=["a"])
            value_b["manuscript_locations"] = ["paper/main.tex:42"]
            graph.add(value_b)
            graph.promote("b", verifier="v-b", verifier_role="theorem_verifier", report=accept_report("b", "v-b", dependencies=["a"]))
            value_c = fact("c", dependencies=["b"])
            value_c["experiment_dependencies"] = ["experiment-critical"]
            graph.add(value_c)
            graph.promote("c", verifier="v-c", verifier_role="theorem_verifier", report=accept_report("c", "v-c", dependencies=["a", "b"]))
            affected = graph.revoke("a", reason="counterexample", revoked_by="auditor")
            self.assertEqual(["a", "b", "c"], affected)
            self.assertEqual(["b", "c"], graph.get("a")["affected_descendants"])
            self.assertTrue(all(graph.get(key)["status"] == "REVOKED" for key in affected))
            report = graph.get("a")["revocation_report"]
            self.assertEqual(["a", "b", "c"], report["affected_facts"])
            self.assertEqual(["paper/main.tex:42"], report["manuscript_locations"]["b"])
            self.assertEqual(["experiment-critical"], report["experiment_dependencies"]["c"])


if __name__ == "__main__":
    unittest.main()
