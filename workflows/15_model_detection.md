# 15 Model detection

## Purpose

Passively determine installed hosts/tools and models this account/session can actually execute.

## Entry gate

Paid probes are disabled; no credential value will be read, printed or stored.

## Inputs

Current host capability metadata, official CLI help/version output, environment-variable presence booleans and user policy.

## Required stages

1. Detect Codex/Claude/Lean/LaTeX/runtimes and versions with bounded passive commands.
2. Distinguish VERIFIED_AVAILABLE, CONFIGURED_UNVERIFIED, PUBLICLY_LISTED, UNAVAILABLE, UNKNOWN and DEPRECATED.
3. Query provider account lists only when a credential is configured and the user explicitly allows the request.
4. Record model capabilities, effort support, evidence, adapter and check time; unknown fields remain null/UNKNOWN.
5. Choose MODE A–E from verified host behavior and explicitly enabled fallbacks.
6. Never make an inference request in default `models detect`.

## Output gate

`model_inventory.json` and `provider_status.json` are versioned, secret-free and say whether any paid probe occurred.

## Verification gate

Public documentation alone cannot establish account availability. Callable current-session behavior takes precedence when documented and observed states differ.

## Stop conditions

Stop at interactive login, paywall, unknown-cost request, secret prompt or unsafe CLI option.

## Escalation

Ask the user before any active/paid probe or enabling subprocess/API/gateway execution.

## Handoff record

Record versions, paths, statuses, evidence methods, execution mode, limitations and next refresh trigger.

