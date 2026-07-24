# Workflow guide

All workflows have entry, output, verification, stop, escalation and handoff
gates. They are composable but not optional labels.

| No. | Workflow | Main output | Mandatory independent gate |
|---:|---|---|---|
| 00 | Project intake | problem/assumptions/notation/plan/DoD/risks | scope and consistency review |
| 01 | Problem formalization | precise claims and evidence classes | assumption/quantifier audit |
| 02 | Literature review | opened sources and literature map | reference audit |
| 03 | Idea swarm | 3–5 distinct bounded routes | evidence comparison, no voting |
| 04 | Proof search | local PROPOSED proof packets | theorem verifier + counterexample attempt |
| 05 | Counterexample search | validated refutation or bounded failure report | assumption check and exact witness audit |
| 06 | Fact verification | ACCEPT/REJECT/UNCERTAIN, graph update | cold-start independent verifier |
| 07 | Computational experiment | reproducible numerical/symbolic evidence | numerical reproducibility audit |
| 08 | Formalization | pinned Lean artifact/build report | compiler, axioms and placeholder audit |
| 09 | Paper planning | dependency outline and claim map | VERIFIED-fact coverage |
| 10 | Paper writing | compilable traced manuscript | paper math + reference audits |
| 11 | Full paper review | internal/blind referee report | proof-reading of all main claims |
| 12 | Revision cycle | issue-linked repairs and reruns | affected-fact/section re-verification |
| 13 | Release check | machine-readable PASS/FAIL | all deterministic and review gates |
| 14 | Session handoff | durable state and next action | state/ledger consistency |
| 15 | Model detection | inventory, provider status, MODE A–E | passive evidence; no paid probe |
| 16 | Model routing | deterministic route/fallback/budget record | policy/tool/context/independence audit |
| 17 | Model benchmarking | fixed-version results without fake ranking | independent keys and false-acceptance focus |

Use evidence classes literally. Literature conclusions are source reports;
experiments are numerical/empirical evidence; worker proofs are PROPOSED;
verifier rejection is REJECTED/UNCERTAIN; only the graph gate creates VERIFIED.

Do not run a downstream workflow while its formal input dependency is merely
PROPOSED. Revision after revocation returns to the earliest affected workflow,
not just the prose-editing stage.

