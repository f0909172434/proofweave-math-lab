# Claim–evidence matrix

This matrix is the minimum citation map for README statements and future
papers. It records what was tested, not a theorem about every possible input.
The authoritative per-run values are in `evaluation.json`; this document must
not be edited to make a failed run appear successful.

| Technical claim | Fixed evidence | Acceptance metric | What the evidence does not establish |
| --- | --- | --- | --- |
| Every allowlisted tactic has working representative obligations. | `PW-POS-RING-*`, `PW-POS-RINGNF-*`, `PW-POS-NORMNUM-*`, `PW-POS-LINARITH-*`, `PW-POS-NLINARITH-*`, `PW-POS-POSITIVITY-*`, `PW-POS-EXACT-*` | 14/14 `PASSED` with real pinned Lean/Mathlib | Completeness for all propositions or all uses of those tactics |
| Paired false or invalid-reference obligations are not certified. | All `PW-NEG-*` cases | 0 false certifications among 14 cases | Global soundness of Lean, Mathlib, the host, or the parser |
| Known certificate-language escapes fail closed. | `PW-ATK-SORRY-01`, `PW-ATK-ADMIT-01`, `PW-ATK-AXIOM-01`, `PW-ATK-UNSAFE-01`, `PW-ATK-META-01`, `PW-ATK-IMPORT-01`, `PW-ATK-TACTIC-01`, `PW-ATK-NATIVE-01` | 0 accepted attacks among 8 cases | Absence of every possible escape or implementation vulnerability |
| Unsupported proof obligations remain partial. | `PW-FC-PARTIAL-01`; `PipelineTests.test_unsupported_node_is_partial_and_traceable` | Expected status `PARTIAL`; no promotion to `CERTIFIED` | Falsity or truth of the unsupported mathematics |
| Missing Lean/Mathlib cannot produce a certificate. | `PW-FC-HOST-01`; `LeanBackendTests.test_missing_lean_is_host_limited_not_certified` | Expected status `HOST_LIMITED`; zero Lean certificates | Host availability on systems outside the measured environments |
| Alignment confirmation becomes stale after bound content changes. | `PW-FC-STALE-01`; `PipelineTests.test_alignment_confirmation_and_source_staleness` | Expected alignment `STALE` | Semantic equivalence between prose and the formal target |
| Missing dependencies and dependency cycles are rejected. | `PW-FC-DEPENDENCY-01`, `PW-FC-DAG-01`; claim/proof DAG unit tests | Both cases `REJECTED`; no committed claim/run result | Correctness of dependency statements supplied by an author |
| A tampered cached artifact is not silently reused. | `PW-FC-TAMPER-01`; `PipelineTests.test_tampered_artifact_is_not_reused` | Expected result `RECOMPUTED`; altered digest is rejected | Integrity before the bundle is hashed, attested, and independently retained |
| An unchanged warm run performs no additional semantic or Lean work. | `PipelineTests.test_fast_path_and_unchanged_rerun`; Core evaluator replay metrics | Warm model calls = 0, semantic extractions = 0, Lean invocations = 0 | Performance on changed inputs or external verifier latency |
| A supported cold run uses at most one Lean batch. | Core evaluator invocation metrics | Cold Lean invocations ≤ 1 | Optimality of the produced proof |
| Human v1 review does not become machine certification during migration. | `MigrationTests.test_v1_verified_never_maps_to_certified` and lifecycle/dependency migration tests | v1 `VERIFIED` maps to `UNVERIFIED`; no status promotion | Mathematical validity of migrated claims |
| Evidence-pack schema v1 cannot claim completed research verification. | `PackEvidenceTests.test_verified_status_is_unsupported_without_all_external_review_evidence` | Every v1 pack marked `VERIFIED` returns `FAIL`, even when observable Lean/alignment/dependency prerequisites pass | Whether a future schema has captured cold replay, novelty recheck, and independent review adequately |
| The implementation stays within the declared Core budget. | `PipelineTests.test_repository_complexity_check`; `python -m proofweave check` | 10 production modules, 3 schemas, 4 commands, zero mandatory role/workflow files | Runtime soundness or research novelty |
| The exercised implementation has high branch-aware coverage. | Coverage report from the complete test suite | Total coverage ≥ 90% | Soundness, completeness, absence of defects, or theorem truth |

## Required wording in papers

Results over the fixed corpus are `COMPUTATIONAL`. A Lean certificate supports
only the exact formal target and dependency environment recorded in its
bundle. Natural-language alignment is a separate human attestation. A
literature search that finds no solution is evidence about the search process,
not proof that a problem remains open or that a result is novel.
