# 08 formalization

## Purpose

formalize selected statements and report machine-checked scope.

## Entry gate

Work may start only with a task identifier, named owner, explicit truth-layer status for referenced claims, and a cold-start artifact packet. Numerical evidence is never accepted as proof; no participant may self-verify.

## Inputs

Verified or explicitly proposed statements, definitions, and proof-assistant target.

## Required stages

1. Record assumptions, dependencies, and evidence class.
2. Execute the named workflow scope with provenance for sources, tools, models, and computations.
3. Produce the stated output and a failure/gap log.
4. Route any PROPOSED theorem claim to an independent theorem_verifier; only that role may promote it to VERIFIED.

## Output gate

Formal source files, tool versions, build results, and an exact statement-to-artifact map.

## Verification gate

The output must be independently checkable from recorded artifacts. Theorem verification is cold-start and independent of the author. Citation claims require reference audit; numerical claims require reproducibility audit where they support a result. A failed check leaves the claim PROPOSED, COMPUTATIONAL, REFUTED, or OPEN as appropriate.

## Stop conditions

Stop on encoding mismatch or unproved obligations. Escalate ambiguity to problem_formalizer and proof gaps to proof_worker.

## Escalation

Escalate scope changes, missing inputs, conflicts, failed checks, suspected false claims, or policy violations to the orchestrator. Preserve all negative results and do not silently repair or relabel evidence.

## Handoff record

Include task/claim IDs, owner, versioned inputs, assumptions, actions, artifacts, truth-layer table, verification state, unresolved items, next owner, and escalation decision.

