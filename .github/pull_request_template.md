## Purpose and scope

Describe the problem, bounded change, and what remains intentionally out of scope.

## Certificate, alignment, and compatibility impact

- Statement, assumptions, quantifiers, or dependencies touched: none / explain
- `alignment`, `proof_status`, or `lifecycle` impact: none / explain
- Cache-key, certifier, Lean, path, or artifact impact: none / explain
- CLI, schema, migration, or file-format impact: none / explain
- Generated evidence intentionally included: none / explain

## Validation

- [ ] `py -3.14 -m coverage run -m unittest discover -s tests -v`
- [ ] `py -3.14 -m coverage report --fail-under=90 --show-missing`
- [ ] `py -3.14 -m proofweave check`
- [ ] `py -3.14 -m tools.check_workflow_security`
- [ ] `py -3.14 -m tools.evaluate core --output artifacts/evaluation` (evidence changes only)
- [ ] `git diff --exit-code` after read-only checks

## Contributor checklist

- [ ] I read `AGENTS.md` and `docs/v2_refactor.md`.
- [ ] I preserved the 10-module, 3-schema, and 4-command Core budgets.
- [ ] I did not reintroduce v1 agents, workflows, providers, routers, reviewer loops, or compatibility shims.
- [ ] I did not promote a claim from finite computation, coverage, model output, or human alignment alone.
- [ ] I added no credentials, private research, personal paths, or sensitive logs.
- [ ] Every external workflow action is pinned to a full commit SHA with a version comment.
- [ ] Documentation and tests match implemented behavior without claiming unrun checks.
