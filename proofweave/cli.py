from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .core import CoreError
from .pipeline import check_project, initialize, run_proof, status

COMMANDS = ("init", "run", "status", "check")


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="proofweave", description="ProofWeave Core v2")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize workspace/claims and artifacts")
    init.add_argument("--root", default=".")

    run = commands.add_parser("run", help="distill and certify one theorem Markdown file")
    run.add_argument("input")
    run.add_argument("--root")
    run.add_argument("--confirm-alignment", action="store_true")

    show = commands.add_parser("status", help="show claim state")
    show.add_argument("claim_id", nargs="?")
    show.add_argument("--root")

    check = commands.add_parser("check", help="run read-only integrity and budget checks")
    check.add_argument("--root")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(Path(args.root))
            code = 0
        elif args.command == "run":
            result = run_proof(
                args.input,
                root=args.root,
                confirm_alignment=args.confirm_alignment,
            )
            code = 0 if result["proof_status"] == "CERTIFIED" else 1 if result["proof_status"] == "FAILED" else 2
        elif args.command == "status":
            result = status(args.root, args.claim_id)
            code = 0
        else:
            result = check_project(args.root)
            code = 0 if result["result"] == "PASS" else 1
    except (CoreError, OSError, ValueError) as exc:
        _print({"result": "ERROR", "error": str(exc)})
        return 1
    _print(result)
    return code


if __name__ == "__main__":
    sys.exit(main())
