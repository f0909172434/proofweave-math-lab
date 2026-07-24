# ProofWeave agent instructions

Read and obey these canonical documents before substantive work:

- `docs/mathematical_quality_standard.md`
- `docs/agent_contracts.md`
- `docs/model_routing_guide.md`

The role definition in `agents/<role>.md` is authoritative. Native agent files
are adapters only and must not duplicate or weaken it.

## Non-negotiable rules

- `state/fact_graph.jsonl` is the formal truth layer. Research notes, model
  output, numerical scans and consensus are not truth.
- Only an independent `theorem_verifier` may promote a PROPOSED claim to
  VERIFIED, and never a claim it authored. The verifier receives the submitted
  statement, proof, assumptions, VERIFIED dependencies and opened sources, not
  hidden worker reasoning.
- Return UNCERTAIN when proof is incomplete. Never convert confidence, voting,
  absence of counterexamples or numerical evidence into proof.
- Preserve failed routes, rejected claims and revocations. Revocation must audit
  every transitive descendant and affected manuscript/experiment location.
- A writer may use VERIFIED facts but may not invent mathematics or silently
  strengthen statements.
- Use parallel agents only for genuinely independent work with non-overlapping
  write scopes. Keep dependency-heavy work sequential.
- Do not expose secrets or run paid probes. External model/API execution,
  publishing, pushing, uploading and messaging require explicit authorization.

## Development and validation

Use the bundled Python 3.12+ or any Python 3.11+ runtime. The project has no
mandatory third-party runtime dependency.

```powershell
python -m unittest discover -s tests -v
python -m mathlab graph-check
python -m mathlab release-check
```

Change canonical sources, not generated/native adapter copies. Keep JSONL one
valid object per line and use UTF-8.
