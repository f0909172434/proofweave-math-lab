# Contributing to ProofWeave

Thank you for helping improve ProofWeave. The project is experimental, but its
truth-status and evidence-preservation rules are not optional.

## Before changing files

1. Read `AGENTS.md` and the canonical documents it names.
2. Keep changes bounded to one purpose and preserve unrelated local work.
3. Treat `state/fact_graph.jsonl` as the formal truth layer. Do not promote,
   rewrite, delete, or silently strengthen research claims in a code or
   documentation contribution.
4. Change canonical role contracts under `agents/`; generated Codex and Claude
   adapters are pointers, not independent policy sources.
5. Report vulnerabilities through [SECURITY.md](SECURITY.md), not a public
   issue or pull request.

## Local setup

ProofWeave requires Python 3.11 or newer and has no mandatory third-party
runtime dependency.

```console
python -m pip install --no-deps --editable .
python -m unittest discover -s tests -v
python -m mathlab graph-check
python -m scripts.validate_project --quick
python -m mathlab release-check
```

The final command refreshes tracked release-report files. Review those changes
and include them only when a release snapshot is intentionally in scope.

## Pull requests

- Explain the problem, scope, security/privacy impact, and validation performed.
- Add or update tests for behavior changes.
- Preserve CLI flags, file formats, and truth-status semantics unless a
  separately reviewed compatibility change explicitly authorizes otherwise.
- Keep all GitHub Actions dependencies pinned to a full 40-character commit SHA
  and retain a human-readable version comment on the same line.
- Do not add secrets, private research, generated credentials, absolute personal
  paths, or claims that a passing test proves a theorem.
- Update user-facing documentation when behavior or supported boundaries change.

Use `python -m scripts.check_repository_baseline` to validate public-document
links, required community files, stable CI contracts, and workflow action pins.

## Research-status language

Keep `DRAFT`, `PROPOSED`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `UNCERTAIN`,
`REVOKED`, `SUPERSEDED`, `COMPUTATIONAL`, and `OPEN` distinct. A model answer,
vote, search result, algebraic check, or finite computation cannot promote a
claim. Only an independent `theorem_verifier` may accept a submitted proof
packet, and deterministic graph checks must still pass.

By contributing, you agree that your contribution is licensed under the
repository's [MIT License](LICENSE).
