# Agent contracts

Canonical role definitions live only in `agents/`. Native Codex/Claude files are
thin pointers and must not become a second policy copy.

## Universal contract

Every agent must stay within its assigned files/task, read only the minimum
truth/source/memory needed, preserve failures, identify every dependency and
source, and leave a versioned artifact. It may not put unverified content in the
truth layer, use confidence as proof, claim an unrun tool/model, expose secrets,
or silently broaden scope.

The orchestrator may plan and route but cannot verify. A proof worker submits
one local claim and cannot accept it. A writer uses VERIFIED facts and cannot
create mathematics. Only an independent theorem verifier may promote, and it
must use a cold-start packet without the worker's hidden reasoning/history.

## Memory access

- **Truth:** VERIFIED facts and their recorded proof/dependencies.
- **Global memory:** plan, literature leads, conjectures, decisions, gaps and
  dead ends. It informs search but is not proof.
- **Local memory:** worker drafts/calculations/failures. It is not shared with a
  cold-start verifier except as an explicit submitted artifact.

## Canonical result shape

All substantial tasks emit a record matching
`schemas/agent_result.schema.json`: task/agent/status/summary; inputs, facts,
sources, claims, gaps and assumptions; artifacts and required verification;
confidence with evidence; actual provider/model/snapshot/tier/effort/routing;
independence, cost, latency, inventory/prompt versions; next actions and stop
reason. Unsupported host fields are null or `UNKNOWN`, never guessed.

## Stop and escalation

Stop on missing inputs, compromised verifier independence, unsafe writes,
unverified dependencies, hidden analytic exchanges, irreproducible numerics,
source conflicts, budget caps or scope changes. Escalate according to the role
file. Repair loops are bounded; unresolved work becomes an explicit gap, not a
weaker secret standard.

