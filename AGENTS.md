# ProofWeave Core v2 instructions

Read `docs/v2_refactor.md` before changing the runtime.

- Certification must preserve statement, assumptions, quantifiers, and dependencies.
- `CERTIFIED` requires a deterministic certificate and 100% deductive coverage.
- Claim and proof dependencies must be acyclic.
- The runtime must not call models or import `tools/migrate_v1.py`.
- Keep exactly four CLI commands, at most ten production modules and three schemas.
- Do not reintroduce agents, workflows, providers, routers, reviewer loops, or legacy shims.

Validate with `py -3.14 -m unittest discover -s tests -v` and
`py -3.14 -m proofweave check`. Both commands must leave tracked files unchanged.
