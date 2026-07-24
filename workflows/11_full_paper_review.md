# 11 Full paper review

## Purpose

Review the complete manuscript in internal-audit or blind-referee mode, including the main proofs rather than only abstracts/statements.

## Entry gate

The manuscript, claim map, graph snapshot, bibliography, experiment artifacts and supplements are frozen and readable.

## Inputs

Complete paper and all dependency/source/numerical artifacts. Blind mode hides author/worker discussion and starts fresh.

## Required stages

1. Trace each main theorem through its proof and VERIFIED dependency closure.
2. Audit assumptions, asymptotics, citations, novelty positioning, numerics, reproducibility and abstract/body consistency.
3. Attempt counterexamples for fragile universal/global claims.
4. Classify every issue as FATAL, MAJOR, MINOR or STRENGTH.
5. For each issue record ID, location, affected claims, explanation, failed step, counterexample if any, required fix and post-fix verification.
6. Produce a recommendation while preserving uncertainty and strengths.

## Output gate

A structured referee report and issue-ledger entries; no issue is closed by prose alone.

## Verification gate

Fatal/major mathematical findings are independently reproduced or explicitly marked UNCERTAIN before release decisions.

## Stop conditions

Stop only after every main proof and required evidence class has been examined, or clearly state which material could not be reviewed.

## Escalation

Escalate a false main theorem, circular dependency, unverifiable citation or irreproducible central numerical result immediately.

## Handoff record

Record review mode, frozen versions, issue IDs/severities, unreadable artifacts, recommendation and required revision gates.

