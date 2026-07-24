from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from mathlab.io import configure_utf8_console, find_project_root


def compile_tex(main_tex: Path) -> dict[str, object]:
    engine = shutil.which("pdflatex")
    if not engine:
        return {"status": "UNSUPPORTED", "reason": "pdflatex not installed"}
    results = []
    for _ in range(2):
        completed = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", main_tex.name],
            cwd=main_tex.parent,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        results.append(completed.returncode)
        if completed.returncode:
            return {
                "status": "FAIL",
                "returncodes": results,
                "log_tail": (completed.stdout + completed.stderr)[-4000:],
            }
    return {"status": "PASS", "returncodes": results, "pdf": str(main_tex.with_suffix(".pdf"))}


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("tex", nargs="?")
    args = parser.parse_args()
    root = find_project_root(Path.cwd())
    path = Path(args.tex).resolve() if args.tex else root / "paper" / "main.tex"
    result = compile_tex(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"PASS", "UNSUPPORTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
