# Model detection limits

Detection evidence has different strength:

1. current host capability metadata plus a callable surface;
2. authenticated official account model-list API (when explicitly allowed);
3. successful minimal authorized probe;
4. installed CLI/help text;
5. configured endpoint/key-name presence;
6. public catalog;
7. model self-report or remembered name.

Only the first three can justify VERIFIED_AVAILABLE, and a probe may have cost.
An installed/authenticated CLI does not prove that every documented model is
entitled. Public model names do not establish account access. Model prose cannot
reliably prove its own identity, snapshot, context size or tool availability.

Rolling aliases, plans, admin policy, regional rollout and host versions drift.
Refresh after upgrades, account/policy changes, unexplained routing failures or
model deprecations. Preserve exact version/evidence time and keep unknown
context/cost/rate fields null or UNKNOWN.

Reasoning effort is observable only through an exposed official setting and the
effective configuration record. Prompt depth/iteration can be labeled
PROMPT_OR_LOOP_BASED but is not native effort. If the host cannot control it,
record HOST_UNSUPPORTED.

The current snapshot confirms native per-agent model/effort controls for this
Codex desktop task. It does not promise the same list in a future task or through
Codex CLI, Claude Code or an API.

