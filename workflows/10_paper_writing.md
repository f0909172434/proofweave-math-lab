# 10 Paper writing

## Purpose

Write a compilable manuscript from a frozen VERIFIED fact-graph snapshot without inventing mathematics.

## Entry gate

A graph version is frozen; theorem dependency outline and `claim_map.yml` exist; all formal manuscript claims point to VERIFIED facts.

## Inputs

Verified fact packets, source registry, paper plan, notation, numerical evidence with limitations, figures/tables and target style.

## Required stages

1. Generate sections in dependency order and attach fact IDs to every theorem/lemma/proposition/corollary.
2. Keep conjectures, heuristics, empirical observations and numerical evidence visibly distinct.
3. Do not add a proof step, assumption or stronger conclusion absent from the fact packet; return an OPEN GAP instead.
4. Ensure abstract, introduction, discussion and conclusion do not exceed the body.
5. Compile LaTeX and check labels, references, symbols, bibliography and claim map.
6. Run paper math verifier, reference auditor and finally style editor; mathematical edits trigger re-verification.

## Output gate

Compilable LaTeX, complete claim map, traceable bibliography and no unsupported formal claim.

## Verification gate

Paper-level glue, definition order, cross-section assumptions and editing regressions are independently checked.
Every claim-map entry binds the current LaTeX statement digest and normalized
fact-statement digest, with a named, timezone-stamped `paper_math_verifier`
attestation. Any statement edit invalidates that binding and requires re-review.

## Stop conditions

Stop on any unsupported claim, missing proof/source, inconsistent notation or uncompiled document.

## Escalation

Escalate claims whose desired prose would strengthen the verified statement or whose source entailment is uncertain.

## Handoff record

Record graph snapshot, files, claim-map version, compile result, audits, open issues and sections requiring re-review.
