# 14 Session handoff

## Purpose

Make research state recoverable across context windows, models and future sessions without turning memory into truth.

## Entry gate

A bounded unit of work has ended or a material decision, failure, verification, experiment or routing change occurred.

## Inputs

Truth graph, worker reports, issue/source ledgers, decisions, dead ends, experiments, routing log and budget state.

## Required stages

1. Update `state/STATUS.md`, `CHANGELOG.md`, `open_gaps.md`, `dead_ends.md` and `decisions.md` without deleting prior failures.
2. List current objective; verified/proposed/refuted results; active workers; blocking gaps; failed approaches; experiments; next action.
3. List execution mode, verified/configured/disabled models, budget mode, recent routes, escalations, downgrades and missing independent verification.
4. Label every memory item by evidence class and link artifacts/IDs rather than pasting hidden reasoning.
5. Run quick structural validation and record unresolved HOST_LIMITED/UNKNOWN items.

## Output gate

A fresh reader can resume from files alone and cannot mistake global/local memory for VERIFIED truth.

## Verification gate

Cross-check status claims against ledgers and graph; do not copy a worker's confidence as verification status.

## Stop conditions

Stop only after the next action and every blocker have an owner or explicit human-decision marker.

## Escalation

Escalate inconsistent state files, missing artifacts, secret leakage or a truth/memory mismatch.

## Handoff record

The handoff files themselves are the record; include timestamp, actor, commands/tests and artifact versions.

