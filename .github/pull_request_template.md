## Purpose and scope

Describe the problem, the bounded change, and what is intentionally out of
scope.

## Truth, security, and compatibility impact

- Truth-layer files or statuses touched: none / explain
- External data, credentials, network, or cost impact: none / explain
- CLI, schema, or file-format compatibility impact: none / explain
- Generated artifacts intentionally included: none / explain

## Validation

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python -m mathlab graph-check`
- [ ] `python -m scripts.validate_project --quick`
- [ ] `python -m scripts.check_repository_baseline`
- [ ] `python -m mathlab release-check` (or reason it is not applicable)

## Contributor checklist

- [ ] I read `AGENTS.md` and the canonical contracts relevant to this change.
- [ ] I did not promote a claim from model agreement, confidence, search, or computation.
- [ ] I preserved rejected work, open gaps, and unrelated local changes.
- [ ] I added no credentials, private research, personal paths, or sensitive logs.
- [ ] Every workflow action is pinned to a full commit SHA with a version comment.
- [ ] Documentation and tests match the implemented behavior without claiming unrun checks.
