# ProofWeave Roles

This directory defines canonical role contracts. The explicit list currently contains 28 role files (although the original request says 27); this README treats the enumerated names as authoritative.

## Truth-layer protocol

Every claim has exactly one current status: FACT (definition or direct datum), CITED (source-backed pending source audit), COMPUTATIONAL, HEURISTIC, PROPOSED, VERIFIED, or OPEN. Numerical, symbolic, and formal experiments may support a claim but are not a proof. Authors may create only PROPOSED claims. Only an independent `theorem_verifier` may promote a PROPOSED claim to VERIFIED; that verifier must not be the claim author, must work cold-start from recorded artifacts, and must log the decision. No role may self-verify, and every failure or gap must be reported honestly.

## Common handoff minimum

Each handoff names the task and claim identifiers, inputs, assumptions, dependency statuses, evidence class, artifacts, unresolved gaps, next owner, and escalation reason. Missing information blocks promotion rather than being inferred.

## Authority boundary

Routing, writing, editing, computation, citation checks, and formalization do not confer theorem-verification authority. The orchestrator coordinates but cannot override a failed or missing independent verification.
