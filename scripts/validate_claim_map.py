from __future__ import annotations

import json
from pathlib import Path

from mathlab.io import find_project_root
from mathlab.validation import validate_claim_map


root = find_project_root(Path.cwd())
checks = validate_claim_map(root)
print(json.dumps([check.as_dict() for check in checks], indent=2))
raise SystemExit(1 if any(check.status == "FAIL" for check in checks) else 0)

