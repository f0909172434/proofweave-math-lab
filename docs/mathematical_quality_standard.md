# Mathematical quality standard

This standard governs research artifacts and manuscripts. `VERIFIED` means an
independent theorem verifier accepted the recorded proof packet under this
workflow; it does not mean formal proof, human peer review, or infallibility.

## 1. Statement completeness

State the domain, all quantifiers, parameter ranges, regularity, boundary and
initial conditions, endpoint conventions and exact target. A formal claim with
an empty assumption list is invalid; write an explicit “no additional
assumptions” entry when appropriate.

## 2. Assumption consistency

Check that hypotheses can hold simultaneously and are used at the claimed
strength. Detect vacuous or empty cases. Do not silently add connectedness,
compactness, positivity, smoothness, nondegeneracy or uniqueness.

## 3. Definition and notation discipline

Define each object before use; give domains/codomains and distinguish constants,
parameters and variables. One symbol has one meaning within a scope. Renaming in
the manuscript must preserve the normalized fact statement.

## 4. Proof completeness

Justify each nontrivial inference. Avoid “obviously,” “clearly,” “standard,” “it
follows,” or “after simplification” when they hide the operative argument.
Display relevant algebra, signs, exponents, constants and denominators. A GAP
keeps a claim PROPOSED/UNCERTAIN.

## 5. Dependency validity

Every formal dependency is identified by fact ID and must be VERIFIED at the
time of submission and release. External theorems require an opened/verified
source, exact supported claim and applicability check. Cycles are forbidden.

## 6. Endpoint and degenerate cases

Test zero/empty objects, boundaries, singular parameters, equality cases,
loss of rank, vanishing denominators, roots/log domains and changes of topology
or regularity. A generic-parameter proof cannot be advertised at excluded
endpoints.

## 7. Asymptotic rigor

Specify the limiting variable, other parameters and uniformity regime. Audit
little-o/big-O constants, leading powers and multi-parameter paths. A C0
asymptotic cannot be differentiated as a C1 asymptotic without additional
control. Every exchange of limit, derivative or integral needs its theorem and
conditions (uniform convergence, domination, monotonicity, regularity, etc.).

## 8. Numerical reproducibility

Save config, executable code, environment, seed/initial data, tolerances, raw
data, output and reproduction command. Test grids, steps, tolerances, initial
conditions, endpoints and alternative solvers as applicable. Analyze floating,
discretization and root-finding error. Numerical results remain numerical
evidence even after perfect reproduction.

## 9. Citation validity

Verify authors, title, date, venue, version, DOI/arXiv and theorem/section/page
where available. Record the exact proposition supported. A DOI or search hit
does not prove entailment, correctness, access rights or license. Search for
negative/contradictory literature as well as support.

## 10. Global manuscript consistency

Trace every theorem through `paper/claim_map.yml`. Check definition order,
notation, cross-section assumptions, glue arguments and dependencies. Abstract,
introduction, discussion and conclusion must not state stronger results than
the body. Editing that changes mathematical force triggers re-verification.
Matching an environment type and fact ID is not enough: bind hashes of the
current LaTeX statement and normalized fact statement, plus an independent
`paper_math_verifier` attestation. This review record detects later substitution
but is not an automated proof that two mathematical formulations are equivalent.

## 11. Claim strength control

Keep theorem, lemma, proposition, corollary, conjecture, heuristic, numerical
evidence, empirical observation, refuted claim, open gap and unknown distinct.
Do not convert finite computation, failed counterexample search, high confidence
or multiple-model agreement into a universal result.

## 12. Research honesty

Never invent a source, DOI, page, theorem number, tool invocation, model switch
or proof. Preserve failed routes and corrections. Use OPEN GAP, UNCERTAIN,
UNKNOWN, NOT VERIFIED or I DO NOT KNOW whenever they are the accurate status.

## Mandatory theorem audit

Before a theorem can be used formally, it must pass statement, proof,
assumption, dependency, counterexample-attempt, citation,
numerical-distinction and manuscript-consistency audits. The verifier report
records each gate. Only a cold-start independent `theorem_verifier` may issue
ACCEPT and invoke the promotion command.
