# One actual certification run

This directory records a local run of the bundled square-successor identity on
September 5, 2026, with Python 3.12.14 and pinned Lean/Mathlib 4.32.2 on macOS arm64.
The exact source commit is recorded in [`run-summary.json`](run-summary.json).

The input states `(x + 1)² = x² + 2x + 1` for every integer x. Its author-supplied
Lean target is certified with the `ring` tactic. Read the [input](input.md),
[generated Lean](certificate.lean), [certificate](certificate.json), and
[coverage](coverage.json) together.

| Observation | First run | Unchanged second run |
|---|---|---|
| Formal proof | `CERTIFIED` | `CERTIFIED` |
| Prose-to-target alignment | `UNCONFIRMED` | `UNCONFIRMED` |
| Deductive obligations | 1 / 1 certified | Same verified artifact |
| Model calls | 0 | 0 |
| Certifier calls | 1 | 0 |
| Cache hit | false | true |

The second run reused the first run ID after checking artifact integrity. It did
not create a new independent proof. No human alignment attestation was supplied.
Lean's result applies to the exact formal target; it does not establish that the
target captures every intended meaning of the prose.

## Reproduce

Follow the repository's [environment setup](../../../README.md#quick-start-from-source),
then run from its root:

```sh
python -m proofweave init
python -m proofweave run examples/simple_ring/theorem.md
python -m proofweave status square-successor
python -m proofweave run examples/simple_ring/theorem.md
```

Use a clean checkout for an uncached first run. Toolchain fingerprints and run IDs
can differ across hosts. Missing formal tooling must remain `HOST_LIMITED`, not a
successful certificate. Do not add `--confirm-alignment` just to change a label.

`run-summary.json` selects fields from the actual CLI outputs and omits absolute
host paths. The four proof artifact files are byte-for-byte copies of that run;
[`SHA256SUMS`](SHA256SUMS) binds them and the summary. This is one reproducible
walkthrough, separate from the released 42-case evaluation corpus.
