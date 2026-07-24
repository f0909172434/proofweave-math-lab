from __future__ import annotations

import json
from pathlib import Path

from mathlab.fact_graph import FactGraph
from mathlab.io import find_project_root


root = find_project_root(Path.cwd())
errors = FactGraph(root / "state" / "fact_graph.jsonl").check()
print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
raise SystemExit(0 if not errors else 1)

