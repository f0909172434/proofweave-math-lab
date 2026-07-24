from __future__ import annotations

import json
from pathlib import Path

from mathlab.io import configure_utf8_console, find_project_root
from mathlab.validation import release_report


root = find_project_root(Path.cwd())
configure_utf8_console()
report = release_report(root)
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["status"] == "PASS" else 1)
