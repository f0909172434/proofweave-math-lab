# Model routing guide

Routing chooses the lowest sufficient *verified executable* configuration. It
does not rank truth by model reputation and cannot replace proof verification.

## Availability is not one bit

- `VERIFIED_AVAILABLE`: current host/account evidence permits execution.
- `CONFIGURED_UNVERIFIED`: configured but not yet proven executable; automatic
  use needs explicit permission.
- `PUBLICLY_LISTED`: catalog only; never automatically executed.
- `UNAVAILABLE`, `UNKNOWN`, `DEPRECATED`: excluded.

An installed CLI proves only that the executable exists. An API-key variable
proves only that a name is present. Credential values are never logged.

## Capability and effort

UTILITY covers metadata and deterministic formatting; STANDARD covers initial
literature screening, LaTeX and ordinary code; ADVANCED covers strategy, local
proof, nontrivial numerics/asymptotics and counterexamples; FRONTIER covers
novel/core theorems, long chains, theorem verification and adversarial review.

Abstract effort is NONE, LOW, MEDIUM, HIGH, VERY_HIGH or MAXIMUM. An adapter maps
to supported native values; otherwise it records PROMPT_OR_LOOP_BASED or
HOST_UNSUPPORTED. It never invents invisible reasoning-token counts.

## Hard filters and score

First exclude candidates that lack verified availability, required tools,
context, privacy permission, provider permission or nondeprecated status.
High-risk theorem work cannot use UTILITY/STANDARD. Then score capability,
independent benchmark data, tools, context, reliability and independence minus
cost, latency, deprecation, availability and correlated-error risk.

The task classifier uses domain, proof depth, novelty, error cost, dependency
count, ambiguity, tools, context, privacy, latency and cost—not prompt length
alone. Same task plus inventory version yields the same route ID.

## Independence, escalation and downgrade

A verifier preferably differs from the author in provider, model family,
snapshot, prompt lineage, unverified memory, tools or method. Identical agents
are correlated; voting is not proof. Escalate only on defined evidence:
REJECT/UNCERTAIN, two no-progress attempts, agent conflict, suspected
counterexample, unjustified analytic exchange, grid sensitivity, source
conflict or main-conclusion impact. Order: raise effort, change model within
tier, raise tier, change provider, bounded evaluator-optimizer, human decision.
Downgrade once work is mechanical or a lower tier provides measured parity.

## Current project mode

The initialization snapshot is MODE A (native subagents with per-agent model
and effort controls). Codex/Claude CLIs are installed but subprocess routing is
disabled. API/gateway routing is disabled and unconfigured. Future sessions
must refresh `state/model_inventory.json` rather than treating this snapshot as
timeless.

```powershell
python -m mathlab models detect
python -m mathlab models doctor
python -m mathlab route classify task.md
python -m mathlab route recommend task.md
python -m mathlab route explain ROUTING_ID
python -m mathlab budget status
```
