# ProofWeave Core v2 destructive refactor

## Baseline

- Repository: `f0909172434/proofweave-math-lab`
- Baseline commit: `4d9e1bce919f329a54d0a5d38b60e77629489a13`
- Baseline unit tests: 104 passed
- Baseline `graph-check`: PASS
- Baseline `release-check`: PASS
- Baseline production: 31 Python modules, 5,642 lines, 15 schemas, 633-line CLI

The v1 implementation remains recoverable from Git history. Core v2 does not
retain, relocate, import, or emulate the v1 runtime.

## The only preserved invariants

1. Certification never changes the statement, assumptions, quantifiers, or
   dependencies presented to it.
2. Claim dependencies and proof-node dependencies are acyclic DAGs.
3. A certificate cache key binds the statement, assumptions, quantifiers,
   dependency certificate digests, certifier identity and version, certificate
   view, Lean version, and toolchain/lockfile fingerprint.
4. `proof_status=CERTIFIED` is derived only from a deterministic certificate
   result with 100% deductive coverage.

`alignment`, `proof_status`, and `lifecycle` are independent fields. Agent
identity, model confidence, voting, and role-based promotion have no authority
over certificate results.

## Deleted responsibilities

Core v2 removes agents, workflows, prompts, provider adapters, model and
reasoning routers, task classification, budgets, capability probes, routing
audit, collaboration, context packets, benchmarks, source/literature ledgers,
paper review, experiment governance, release governance, and all generated
agent adapters. There is no compatibility shim and no `legacy/` tree.

## Target architecture

The runtime is exactly the `proofweave` package with ten modules:

```text
proofweave/
  __init__.py
  __main__.py
  cli.py
  core.py
  pipeline.py
  distill.py
  certify.py
  render.py
  certifiers/
    __init__.py
    lean.py
```

Persistent contracts are limited to `claim.schema.json`,
`proof_ir.schema.json`, and `run.schema.json`. User state lives under
`workspace/claims/`; immutable, content-addressed run output lives under
`artifacts/`.

The four top-level commands are `init`, `run`, `status`, and `check`. The normal
workflow is one command: `proofweave run theorem.md`.

Core performs no model calls. Structured Markdown is parsed deterministically.
A whole-claim Lean specification takes the fast path; otherwise one semantic IR
is built, distilled, batch-certified where supported, and rendered as a paper
proof, concept map, and exact coverage report. Unsupported obligations produce
`PARTIAL` and never start a reviewer loop.

Lean 4.32.1 and Mathlib 4.32.1 are project-pinned. The backend generates a
fixed `import Mathlib` file and accepts only enumerated tactics. Missing or
unusable tooling produces `PARTIAL/HOST_LIMITED`.

## Migration mapping

`tools/migrate_v1.py` is a one-time tool and is never imported by the runtime.
It preserves formal claim text, assumptions, quantifiers, proof, and dependency
IDs after validating uniqueness and acyclicity. Non-formal evidence is skipped
and reported.

All v1 review statuses, including `VERIFIED`, map to
`proof_status=UNVERIFIED` and `alignment=UNCONFIRMED`; human review is not a
machine certificate. v1 `REVOKED` and `SUPERSEDED` map only to the corresponding
`lifecycle`; other migrated formal claims are `ACTIVE`.

## Hard complexity and runtime budgets

- production modules: at most 10
- schemas: exactly 3
- top-level commands: exactly 4
- `cli.py`: at most 200 lines
- each production file: fewer than 400 lines
- total production Python: at most 2,500 lines, target at most 2,300
- mandatory role/workflow files: 0
- unchanged rerun: 0 model calls, 0 semantic extractions, 0 Lean invocations
- changed long proof: at most 1 deterministic semantic extraction
- cold run with supported obligations: at most 1 Lean batch invocation
- reviewer loops: 0

Any exceeded budget is fixed by deleting or merging design, not by documenting
an exception.
