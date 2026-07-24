# 12 Revision cycle

## Purpose

Turn review issues into controlled changes, re-verifying every affected mathematical descendant and manuscript section.

## Entry gate

The referee report and baseline artifacts are frozen; every accepted issue has an owner and intended disposition.

## Inputs

Issue ledger, affected fact IDs, manuscript locations, experiment dependencies, source records and repair budget.

## Required stages

1. Move issues through OPEN, IN_PROGRESS, FIXED, REJECTED or DEFERRED with reasons.
2. Link each issue to original location, facts, modified files, added/revoked facts, rerun experiments and sections to re-review.
3. If a fact changes or is revoked, audit every descendant before using it again.
4. Re-run experiments and source audits when inputs/claims change.
5. Re-run full paper review after mathematical edits; style-only edits cannot close mathematical issues.
6. Produce revision summary and response-to-reviewers draft without overstating resolution.

## Output gate

Every FIXED issue has artifacts and successful required post-fix verification; unresolved issues remain visible.

## Verification gate

The original worker/writer cannot self-certify the repaired theorem. Independent verification is repeated on affected claims.

## Stop conditions

Stop at repair-loop/budget caps or when a fix would change the main claim beyond scope; request human direction.

## Escalation

Escalate revoked main results, incompatible reviewer requests, new counterexamples or a repair that introduces stronger assumptions.

## Handoff record

Record issue status transitions, diffs/artifacts, fact cascades, reruns, new reports, deferred work and release readiness.

