from __future__ import annotations

import argparse
import json
from pathlib import Path

from mathlab.io import configure_utf8_console, find_project_root
from mathlab.validation import release_report, validate_structure


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    root = find_project_root(Path.cwd())
    if args.quick:
        checks = validate_structure(root)
        result = {
            "status": "PASS" if not any(check.status == "FAIL" for check in checks) else "FAIL",
            "checks": [check.as_dict() for check in checks],
        }
    else:
        result = release_report(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
