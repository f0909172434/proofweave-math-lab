# Contributing to ProofWeave Core v2

ProofWeave is experimental research infrastructure. Its evidence boundaries and
fail-closed behavior are part of the public contract.

## Before changing files

1. Read `AGENTS.md` and `docs/v2_refactor.md`.
2. Keep the change bounded and preserve unrelated work.
3. Preserve claim statements, assumptions, quantifiers, and dependencies across
   every certification boundary.
4. Do not couple `alignment`, `proof_status`, and `lifecycle`.
5. Do not reintroduce Core v1 agents, model workflows, providers, routers,
   reviewer loops, legacy state, or compatibility shims.
6. Report vulnerabilities through `SECURITY.md`, not a public issue.

## Local setup and validation

Core has no Python production dependencies. Supported certification still uses
the pinned external Lean/Mathlib toolchain. Tests use only the pinned test
requirements.

```console
py -3.14 -m pip install --no-deps --editable .
py -3.14 -m pip install -r requirements-test.txt
py -3.14 -m coverage run -m unittest discover -s tests -v
py -3.14 -m coverage report --fail-under=90 --show-missing
py -3.14 -m proofweave check
py -3.14 -m tools.check_workflow_security
```

When evidence behavior changes, follow the pinned toolchain bootstrap in
`docs/evaluation_protocol.md`, require Lean explicitly, and also run:

```powershell
lake update mathlib
lake exe cache get
$env:PROOFWEAVE_REQUIRE_LEAN = "1"
py -3.14 -m tools.evaluate core --output artifacts/evaluation
git diff --exit-code
```

The final command must remain clean: tests, checks, and evaluation may not edit
tracked files.

## Hard Core budgets

- exactly four top-level commands;
- exactly three schemas;
- at most ten production modules;
- no Python production runtime dependency;
- no model calls or reviewer loops;
- at most one Lean batch for a supported cold run;
- zero Lean, semantic-extraction, and model invocations for an unchanged warm run.

Budget failures are fixed in implementation, not documented as exceptions.

## Evidence language

`CERTIFIED` requires a deterministic certificate and complete deductive
coverage of the exact formal target. `PARTIAL`, `HOST_LIMITED`, `UNCONFIRMED`,
`STALE`, `COMPUTATIONAL`, and `OPEN` remain distinct. Finite corpora, test
coverage, model output, and natural-language review are not global soundness
proofs.

By contributing, you agree that your contribution is licensed under the
repository's MIT License.
