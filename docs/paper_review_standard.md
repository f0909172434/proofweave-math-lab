# Paper review standard

## Review modes

**Internal audit** may use project ledgers and asks whether the artifact is
ready. **Blind referee** starts without worker/writer discussion and judges the
frozen manuscript and supplied evidence. Both read the main proofs completely.

## Required coverage

Trace every main theorem through its statement, assumptions, proof steps,
VERIFIED dependency closure and source dependencies. Audit definitions,
notation, endpoint/degenerate cases, local-to-global transitions, asymptotics,
limit/differentiation/integration exchanges, numerics, claim map, bibliography,
novelty positioning, abstract/body/conclusion consistency and reproducibility.
Attempt simple counterexamples where hypotheses appear weak.

## Severity

- **FATAL:** false main theorem, inconsistent/vacuous assumptions, valid
  counterexample, circular key proof, nonexistent/misapplied dependency, or no
  repair without changing the main conclusion.
- **MAJOR:** important unproved lemma, missing uniformity/regularity, inadequate
  central numerics, conclusion stronger than proof, critical literature gap or
  major rewrite.
- **MINOR:** notation, typography, local explanation or noncritical citation.
- **STRENGTH:** new method, retained valid result, clear parameterization,
  reproducible evidence, good positioning or effective proof structure.

Each item records issue ID, severity, location, affected claims, explanation,
failed step, counterexample when present, required fix and verification after
fix. FATAL/MAJOR issues cannot be closed by style edits. Mathematical repairs
rerun affected fact verification and full-paper audit.

The recommendation is conditional on the checked snapshot and must state unread
or unverifiable material. AI review is not a substitute for expert peer review.

