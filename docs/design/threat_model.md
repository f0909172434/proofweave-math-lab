# Threat model

## Assets and trust boundaries

Protected assets are mathematical truth status, source/experiment provenance,
manuscript integrity, private research data, credentials, budget/quota and
reproducible history. Untrusted inputs include model output, web/MCP content,
uploaded papers, external code/data, source metadata and worker memory. A
VERIFIED project fact remains fallible and revocable.

## Main threats

- plausible invalid proof or circular dependency enters the truth layer;
- worker self-verifies or orchestrator/writer bypasses the verifier;
- numerical scan, consensus or confidence is upgraded to theorem;
- citation exists but does not entail the sentence, or has license/version
  problems;
- hidden assumptions, endpoint failures or unjustified analytic exchanges;
- stale/wrong model identity, unsupported effort or fake model switch;
- correlated author/verifier errors;
- revocation fails to invalidate descendants/manuscript claims;
- prompt injection in web/PDF/MCP content changes tool behavior;
- unbounded agents/repair loops exhaust quota;
- secrets/private data enter state, logs, subprocess arguments or providers;
- unsafe external code, destructive commands, upload/push/publish without
  authority.

## Controls

Programmatic role/independence/dependency/cycle gates; cold-start verification;
opened-source records and citation audit; evidence-class schemas; reproducible
experiment manifests; cascade revocation; claim-map/release checks; model
availability states and deterministic routing; redacted logs; disabled paid
probes/providers; bounded parallelism/escalation; `.gitignore` and secret scan;
safe CLI flags; human approval for cost/external side effects.

Native role files are prompts rather than security boundaries. Deterministic
Python checks and OS/host permissions are the enforcement layer. MCP, hooks and
provider adapters require separate review and least privilege.

## Residual risk

An independent AI verifier may accept a false proof, humans may formalize the
wrong statement, source registries may contain errors and secret scanners can
miss formats. Core results therefore retain expert-review requirements; high
risk lemmas should additionally use different methods/models, adversarial
counterexample search and, when cost-effective, pinned formalization.

## Incident response

On suspected error: freeze release, revoke the fact, cascade descendants, open
a FATAL/MAJOR issue, preserve the failed artifacts, rerun source/experiment
checks, repair with a new fact version, independently reverify and repeat the
full paper review. On secret exposure: stop tools, remove/rotate the credential
outside this repository, sanitize logs/history and record the incident without
the secret value.
