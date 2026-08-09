# ProofWeave Core v2

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

ProofWeave Core v2 reads an AI-generated theorem and proof and emits a concise paper proof, a proof spine/concept map, and—when supported—a Lean certificate with exact deductive coverage.

It is not a multi-agent governance platform. The runtime has no agents, workflows, providers, model router, budget manager, paper-review system, reviewer loop, or LLM calls.

## Quick start

Python 3.11+, Lean 4.32.2, and Mathlib 4.32.2 are required for certification:

```powershell
py -3.14 -m pip install -e .
lake update mathlib
lake exe cache get
py -3.14 -m proofweave init
py -3.14 -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

The normal workflow is just `py -3.14 -m proofweave run theorem.md`. The only other commands are `init`, `status [CLAIM_ID]`, and the read-only `check`.

Inputs use TOML front matter for ID, assumptions, quantifiers, and dependencies, followed by `## Statement` and `## Proof`. An optional `## Certificate` contains one fixed `proofweave-lean` block. Long proofs may use `### STEP_ID [semantic|bridge|computational|alias]` and `Depends:`.

`CERTIFIED` is derived only from a deterministic Lean result with 100% deductive coverage. Alignment is independent: `CERTIFIED + UNCONFIRMED` means Lean proved the formal target, not that its equivalence to the human statement was established. `run --confirm-alignment` records a hash-bound human attestation; later changes make it `STALE`.

The Lean allowlist is `ring`, `ring_nf`, `norm_num`, `linarith`, `nlinarith`, `positivity`, and restricted `exact`. Arbitrary commands/imports, `sorry`, `admit`, custom axioms, unsafe meta execution, `run_tac`, and `native_decide` are rejected. Missing Lean/Mathlib yields `PARTIAL/HOST_LIMITED`.

ProofWeave does not claim a globally simplest proof and does not automatically prove semantic equivalence between natural language and Lean. Migrate v1 data once with `py -3.14 -m tools.migrate_v1 OLD_FACT_GRAPH --root .`; v1 human `VERIFIED` records become `UNVERIFIED`.

## Tests and paper evidence

Development tests use pinned test-only dependencies and add no runtime dependency:

```powershell
py -3.14 -m pip install -e . -r requirements-test.txt
py -3.14 -m coverage run -m unittest discover -s tests -v
py -3.14 -m coverage report --fail-under=90 --show-missing
py -3.14 -m proofweave check
py -3.14 -m tools.evaluate core --output artifacts/evaluation
py -3.14 -m tools.evaluate pack PACK.toml --output artifacts/evaluation
```

CI runs the fast suite on Python 3.11/3.14 and Ubuntu/Windows, then performs real certification with the pinned Lean/Mathlib on both platforms. The manual workflow produces candidate evidence; a `v*.*.*` tag creates a draft release only and never publishes it automatically.

Finite-corpus results are `COMPUTATIONAL`, and coverage is not a soundness proof. A Lean certificate proves only its formal target; natural-language alignment requires a hash-bound human attestation. Failure to find a published solution does not prove that a problem remains open or that a result is novel. Evidence-pack schema v1 fails closed on `VERIFIED` until a future schema can bind cold replay, novelty recheck, and independent-review evidence. See the [evaluation protocol](docs/evaluation_protocol.md) and [claim–evidence matrix](docs/claim_evidence_matrix.md).
