from __future__ import annotations

import json
from pathlib import Path

from mathlab.io import find_project_root
from mathlab.source_registry import SourceRegistry


root = find_project_root(Path.cwd())
errors = SourceRegistry(root / "state" / "source_registry.jsonl").check()
print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
raise SystemExit(0 if not errors else 1)

