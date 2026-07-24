# ProofWeave instructions for Claude Code

The durable policy is shared with Codex. Before acting, read:

- `docs/mathematical_quality_standard.md`
- `docs/agent_contracts.md`
- `docs/model_routing_guide.md`
- the selected canonical role in `agents/`

`CLAUDE.md` supplies context, not a proof or security gate. Deterministic checks
live in `mathlab/`, `scripts/`, tests and project hooks.

Never write unverified memory into `state/fact_graph.jsonl`. Only the independent
theorem verifier may promote a PROPOSED claim, and it must not verify its own
work. Numerical evidence, model agreement and high confidence are not proofs.
Preserve gaps, dead ends, rejected claims and revocations. Use parallel agents
only for independent non-overlapping tasks. Do not run external paid model calls,
publish, push, upload, or expose credentials without explicit authorization.

Run before handoff:

```powershell
python -m unittest discover -s tests -v
python -m mathlab release-check
```
