# 06 Fact verification

## Purpose

Perform cold-start review of a single claim or dependency closure and maintain graph consistency.

## Entry gate

A complete PROPOSED proof packet exists. The verifier did not author the claim and receives no hidden worker reasoning or unverified worker memory.

## Inputs

Statement, normalized statement, assumptions, quantifiers, proof, VERIFIED dependencies, opened external sources and edge-case list.

## Required stages

1. Validate statement meaning and assumption consistency.
2. Check every dependency is present and VERIFIED; check DAG acyclicity.
3. Audit each proof step, circularity, signs/constants/exponents/domains and external theorem conditions.
4. Audit endpoints, degeneracy, regularity, local/global scope, counterexamples and numerical/analytic distinction.
5. For limits, derivatives or integrals, check every interchange and convergence condition explicitly.
6. Return only ACCEPT, REJECT or UNCERTAIN with the required checklist and smallest decisive issue.
7. Let the CLI gate promote only ACCEPT reports from the theorem_verifier role.
8. For revocation, mark the fact and every transitive descendant REVOKED and list impacted manuscript/experiment locations.

## Output gate

A schema-valid verification report, updated fact graph through the CLI, dependency impact report and issue/open-gap entry when needed.

## Verification gate

No confidence score, model reputation, majority vote or failed counterexample search substitutes for the proof audit.

## Stop conditions

Stop immediately if independence is compromised, inputs are incomplete, or a non-VERIFIED dependency appears; return UNCERTAIN/REJECT rather than guessing.

## Escalation

Escalate conflicting VERIFIED facts, suspected reference contamination, formalization mismatch or main-theorem revocation.

## Handoff record

Record verifier, cold-start attestation, dependency/source closures, checklist, outcome, graph changes and affected descendants.

