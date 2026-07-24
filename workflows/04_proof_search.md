# 04 Proof search

## Purpose

Decompose a target into local, independently checkable claims and develop complete proof packets.

## Entry gate

The target, quantifiers, domains, assumptions and all formal dependencies are explicit; dependencies used formally are VERIFIED.

## Inputs

One local claim per worker, dependency IDs, source IDs, assigned method, edge cases and repair-loop budget.

## Required stages

1. Decompose the target into a dependency DAG before proving downstream claims.
2. Give a worker only the needed facts and sources; require a full proof, assumptions, boundary cases and GAP markers.
3. Run a counterexample attempt for universal, endpoint, degenerate, local-to-global, or exchange-of-limit claims.
4. Submit a complete PROPOSED packet to a cold-start independent theorem verifier.
5. On REJECT, record the minimum fatal gap and allow at most three repairs; on UNCERTAIN, record missing information/tooling.
6. If still unresolved, preserve an OPEN GAP, change method, search for a counterexample, or request human direction.

## Output gate

Each route ends in a verifier report and a PROPOSED, VERIFIED, REJECTED, UNCERTAIN, or refutation artifact. Only ACCEPT triggers the programmatic promotion gate.

## Verification gate

The verifier checks statement, assumptions, every step, dependencies, cited theorem applicability, boundary/degenerate cases, hidden regularity and improper analytic exchanges.

## Stop conditions

Stop at a complete verified local result, valid refutation, documented obstruction, or repair/budget cap.

## Escalation

Escalate suspected false statements, proof/verifier conflicts, repeated gaps or a main-conclusion impact.

## Handoff record

Record claim/proof/version IDs, dependencies, sources, verifier identity/outcome, repair count, artifacts and next action.

