# ProofWeave Core v2

[繁體中文](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Core CI](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/ci.yml)
[![CodeQL](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/codeql.yml/badge.svg)](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/codeql.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![Lean 4.32.2](https://img.shields.io/badge/Lean-4.32.2-4E64C4.svg)](lean-toolchain)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Turn one structured mathematical proof into a small, inspectable certification run.**

ProofWeave Core v2 reads a UTF-8 Markdown claim and writes:

- a normalized UTF-8 copy of the parsed input, while the raw input bytes remain
  bound by `source_hash`;
- a concise paper-proof view and Mermaid proof-spine/concept map;
- obligation-by-obligation deductive coverage;
- a generated Lean source file and deterministic certificate result when the
  claim is inside the deliberately small certificate language; and
- content-addressed run metadata, hashes, and explicit claim-revision state.

Core does not discover a proof, translate arbitrary natural language into Lean,
or call an LLM. It has no agents, providers, prompts, model router, reviewer
loop, hosted service, or telemetry. It certifies author-supplied formal targets
and keeps unsupported obligations visibly `PARTIAL`.

> **Project status:** experimental research infrastructure. In this checkout,
> the repository/evidence release is `v0.1.0`, while the Core runtime and
> protocol version is `2.0.0`. Those are separate version axes.

## See the result first

Running the bundled ring identity with the pinned toolchain produces the
following shape of result (abridged; paths and hashes are shortened):

```json
{
  "claim_id": "square-successor",
  "proof_status": "CERTIFIED",
  "alignment": "UNCONFIRMED",
  "fast_path": true,
  "cache_hit": false,
  "coverage": {
    "deductive_total": 1,
    "certified": 1,
    "failed": 0,
    "unsupported": 0,
    "host_limited": 0,
    "percentage": 100.0,
    "dependencies_ready": true
  },
  "invocations": {
    "model": 0,
    "semantic_extraction": 0,
    "certifier": 1
  },
  "artifact_directory": ".../artifacts/square-successor/<run-id>"
}
```

This is intentionally `CERTIFIED + UNCONFIRMED`: Lean proved the exact formal
target, but ProofWeave did not infer that the target means the same thing as the
human statement. Re-running unchanged input reuses the verified artifact only
after checking its hashes; the returned run has `cache_hit: true` and zero
model, semantic-extraction, and certifier invocations.

## When ProofWeave fits

Use Core when you need to:

- put an algebraic or arithmetic claim behind a pinned Lean check;
- expose which steps of a longer proof have certificates and which remain
  unsupported;
- keep assumptions, quantifiers, claim dependencies, revisions, and lifecycle
  visible instead of collapsing them into one “verified” label;
- detect dependency cycles, missing active dependencies, stale alignment, and
  tampered cached artifacts deterministically;
- produce a conservative paper view and proof map without changing the
  certificate obligations; or
- build a reproducible, checksummed evaluation bundle for a fixed corpus or a
  theorem pack.

Core is not a good fit when you need:

- automated proof search, natural-language formalization, arbitrary Lean
  tactics/imports, or an interactive proof-assistant UI;
- mathematical discovery, literature search, novelty determination, peer
  review, or proof of a theorem's real-world interpretation;
- multi-agent orchestration, model routing, research project management, or a
  hosted collaboration database; or
- a global soundness, completeness, or “simplest proof” guarantee.

## Quick start from source

### 1. Prerequisites

- Python 3.11 or newer;
- Git; and
- [Elan](https://github.com/leanprover/elan), the Lean toolchain manager.

The repository pins Lean in [`lean-toolchain`](lean-toolchain), Mathlib in
[`lakefile.toml`](lakefile.toml), and the complete dependency revisions in
[`lake-manifest.json`](lake-manifest.json). Although the bootstrap commands use
`lake` from the shell, certification resolves `lean` and `lake` from the
Elan-managed directory selected by the project pin (or `ELAN_HOME`). A
PATH-only shim is not treated as a frozen certifier.

### 2. Install and freeze the formal environment

```console
git clone https://github.com/f0909172434/proofweave-math-lab.git
cd proofweave-math-lab
python -m pip install --no-deps --editable .
lake update mathlib
lake exe cache get
```

On Windows, `py -3.14` can replace `python` in every command. The first Mathlib
checkout/cache download can take several minutes. Core itself has no Python
runtime dependency; Lean/Mathlib is required only for real certification.
Without the complete pinned environment, Core fails closed with
`PARTIAL/HOST_LIMITED` instead of manufacturing a certificate.

### 3. Initialize and certify the example

```console
python -m proofweave init
python -m proofweave run examples/simple_ring/theorem.md
python -m proofweave status square-successor
```

`init` creates `workspace/claims/` and `artifacts/` without overwriting existing
files. `run` prints JSON and writes the complete run. `status` reads claim
revision state and returns counts for all three independent status axes.

Do not add `--confirm-alignment` mechanically. After a human compares the exact
`## Statement` plus quantifiers with the Lean `target`—and separately checks
that the assumptions and dependencies match the intended theorem—this command
records a local alignment attestation:

```console
python -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

The alignment hash binds `statement_hash` (statement plus quantifiers) to the
formal-target hash; the stored source hash detects other source edits. The flag
does not authenticate the reviewer or establish novelty, peer review, or truth
outside the encoded formal target. A later source change makes the stored
alignment appear `STALE` until the new revision is inspected and run.

## Input contract

A claim begins with TOML front matter, then `## Statement` and `## Proof`. A
whole-claim certificate goes in an optional `## Certificate` section:

````markdown
+++
claim_id = "square-successor"
title = "Square of a successor"
assumptions = ["x is an integer"]
quantifiers = ["for every integer x"]
dependencies = []
+++

## Statement

For every integer x, (x + 1)^2 = x^2 + 2x + 1.

## Proof

Expand the square and collect like terms.

## Certificate

```proofweave-lean
target = "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1"
tactic = "ring"
```
````

Important parsing rules:

- `claim_id` must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.
- `assumptions` must be explicit; use `["none"]` when appropriate.
- `quantifiers` and `dependencies` are arrays. Every dependency must already
  have exactly one `ACTIVE` claim revision in the same project.
- Claim dependencies and proof-node dependencies must be acyclic.
- Unknown front-matter and certificate fields fail closed.
- Input bytes must be UTF-8.

### Longer, partially formalized proofs

Without a whole-claim `## Certificate`, Core builds one deterministic proof IR.
Use headings of the following form:

````markdown
### normalize [computational]

Normalize the polynomial endpoint.

```proofweave-lean
target = "(20 + 22 : Int) = 42"
tactic = "norm_num"
```

### interpret [semantic]
Depends: normalize

Explain why the certified endpoint establishes the intended mathematical step.
````

The roles are `semantic`, `bridge`, `computational`, and `alias`. Every
non-`alias` node is a deductive obligation. A node without a supported
certificate remains in the output as unsupported, so the whole run is
`PARTIAL`; Core never starts a reviewer loop to hide the gap. See the bundled
[`partial_proof`](examples/partial_proof/theorem.md) example.

## Commands and exit status

Core deliberately exposes exactly four top-level commands:

| Command | What it does | Writes project state? |
| --- | --- | --- |
| `proofweave init [--root DIR]` | Create `workspace/claims/` and `artifacts/` | Only missing directories |
| `proofweave run INPUT [--root DIR] [--confirm-alignment]` | Parse, certify, render, hash, and record one claim revision | Yes |
| `proofweave status [CLAIM_ID] [--root DIR]` | Show stored revisions and counts by status axis | No |
| `proofweave check [--root DIR]` | Verify schemas, hashes, DAGs, artifact integrity, and Core budgets | No |

Use either the installed `proofweave` entry point or
`python -m proofweave`. Exit codes are automation-safe:

| Invocation | Exit `0` | Exit `1` | Exit `2` |
| --- | --- | --- | --- |
| `run` | `CERTIFIED` | `FAILED` or invalid input/runtime error | `PARTIAL`, including `HOST_LIMITED` |
| `check` | `PASS` | `FAIL` or error | — |
| `init`, `status` | Success | Error | — |

Treat exit `2` as an incomplete proof, not a successful warning.

## Reading the three status axes

The axes are orthogonal; never infer one from another.

| Axis | Values | Meaning |
| --- | --- | --- |
| `proof_status` | `UNVERIFIED`, `PARTIAL`, `CERTIFIED`, `FAILED` | Machine-certificate result for this revision. `UNVERIFIED` is retained for records such as conservative v1 migrations. |
| `alignment` | `UNCONFIRMED`, `CONFIRMED`, `STALE` | Whether a human hash-bound statement/formal-target comparison is current. |
| `lifecycle` | `ACTIVE`, `SUPERSEDED`, `REVOKED` | Revision governance; it does not change certificate truth. |

Common combinations:

- `CERTIFIED + UNCONFIRMED + ACTIVE`: Lean proved the formal target; prose
  equivalence has not been attested.
- `CERTIFIED + CONFIRMED + ACTIVE`: the formal target passed and a human
  attested the bound pair. This still says nothing about novelty or peer review.
- `CERTIFIED + STALE`: the prior certificate record still exists, but the
  source bytes changed after alignment; re-inspect and re-run.
- `PARTIAL + UNCONFIRMED`: at least one obligation is unsupported or the host
  lacks the frozen Lean environment.
- `FAILED`: at least one submitted formal obligation failed Lean.

Research-pack statuses (`OPEN`, `PROPOSED`, `COMPUTATIONAL`, `VERIFIED`) are a
separate evidence layer, not a fourth Core claim axis. The current theorem-pack
schema intentionally rejects every `VERIFIED` pack because it cannot bind all
required independent-review and novelty evidence.

## Pipeline and artifact layout

```text
UTF-8 TOML + Markdown
        │
        ▼
preserving parser ──► revision/hash identity ──► claim + proof DAG checks
        │
        ▼
pinned-environment fingerprint ──► cache validation ──► allowlisted Lean batch
        │
        ▼
exact coverage/status ──► conservative rendering ──► hashed run + claim state
```

A fast-path run writes:

```text
workspace/claims/
└── square-successor--<revision-prefix>.json

artifacts/square-successor/<run-id>/
├── input.md
├── paper_proof.md
├── concept_map.md
├── coverage.json
├── certificate.json
├── certificate.lean
├── run.json
└── run.sha256
```

Structured long proofs also write `proof_ir.json`. `paper_proof.md` and
`concept_map.md` are presentation views, never extra proof authority. Every
payload artifact is hashed in `run.json`; `run.sha256` separately protects that
run record. A cache key binds the material claim, certificate, dependency,
certifier, and toolchain inputs. Missing, moved, inconsistent, or modified
artifacts are not silently reused.

## Certificate language and trust boundary

The generated Lean file always starts with fixed `import Mathlib` and disables
automatic implicit parameters. The certificate block accepts only:

- `ring`, `ring_nf`, `norm_num`, `linarith`, `nlinarith`, and `positivity`; or
- restricted `exact`, referring to an earlier certified node in the same
  generated batch.

Core rejects arbitrary commands/imports, tactics outside the allowlist,
`sorry`, `admit`, custom axioms, unsafe/meta execution, `run_tac`,
`native_decide`, and certificate syntax that attempts to define its own theorem
or declaration.

What is bound into certification and reuse includes:

- the statement, assumptions, quantifiers, and dependency certificate digests;
- the complete certificate view and certifier version;
- `lean-toolchain`, `lakefile.toml`, `lake-manifest.json`;
- Elan-managed Lean/Lake executables and Lean library artifacts; and
- exact, clean dependency Git revisions plus the observed Lean-artifact
  digests.

The trusted computing base still includes the Python implementation, operating
system, Git executable, Elan-managed Lean toolchain, Lean kernel/compiler, and
the pinned Mathlib dependency closure. Hashes detect changed bytes; they do not
prove that the host was uncompromised. A passing Lean result proves only the
generated formal target under that environment. It does not establish:

- equivalence to the natural-language statement without human alignment;
- truth of informal assumptions or the intended domain interpretation;
- novelty, openness, publication priority, peer review, or expert consensus;
- completeness of the tactic allowlist or absence of every implementation bug;
  or
- global Lean/Mathlib/host soundness.

See the [threat model](docs/design/threat_model.md) and the destructive
[Core v2 architecture record](docs/v2_refactor.md) for the full boundary.

## Evaluation and theorem packs

Install the pinned test-only dependencies, then run the local gate:

```console
python -m pip install -r requirements-test.txt
python -m coverage run -m unittest discover -s tests -v
python -m coverage report --fail-under=90 --show-missing
python -m proofweave check
python -m tools.check_workflow_security
```

For a real fixed-corpus evidence bundle, first freeze the Lean environment as in
the quick start and require it explicitly:

```powershell
$env:PROOFWEAVE_REQUIRE_LEAN = "1"
python -m tools.evaluate core --output artifacts/evaluation
```

On POSIX shells, use
`PROOFWEAVE_REQUIRE_LEAN=1 python -m tools.evaluate core --output artifacts/evaluation`.
The bundle contains `evaluation.json`, `summary.md`, `environment.txt`, retained
Lean sources, and `SHA256SUMS`.

The fixed corpus has 42 stable cases: 14 positive, 14 paired negative, 8 escape
attempts, and 6 fail-closed state/integrity cases, plus a cold/warm replay. A
passing result is finite-corpus `COMPUTATIONAL` evidence, not a global soundness
proof. For research packs, attestation format, release evidence, and exact
promotion limits, read the [evaluation protocol](docs/evaluation_protocol.md)
and [claim–evidence matrix](docs/claim_evidence_matrix.md).

CI runs Python 3.11 and 3.14 on Ubuntu and Windows, with real pinned Lean
certification on both platforms. Tag workflows build and attest candidate
evidence and create a **draft** release only; publication remains a separate
human action.

## Relationship to the other projects

The repositories are complementary, but there is no implied runtime dependency
or automatic data interchange:

| Project | Narrow responsibility |
| --- | --- |
| **ProofWeave Core** | Certify exact formal targets, expose partial obligations, and retain content-addressed proof runs. |
| [RigorGraph](https://github.com/f0909172434/rigorgraph) | Audit broader claim–evidence traceability and human workflow records; it is not a theorem prover. |
| [HonestCI](https://github.com/f0909172434/honest-ci) | Check whether expected test evidence actually ran; it makes no mathematical truth claim. |

## Development and migration

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing Core. The enforced design
budget is ten production modules, three schemas, four commands, no Python
runtime dependencies, no model calls/reviewer loops, at most one supported cold
Lean batch, and zero extra work on an unchanged warm run.

Core v1 remains recoverable from Git history; v2 does not ship a compatibility
runtime. One-time formal-record migration is available as an explicit tool:

```console
python -m tools.migrate_v1 OLD_FACT_GRAPH --root .
```

Migration preserves formal statement fields and dependencies after validation.
Non-formal evidence is reported and skipped. Every v1 human `VERIFIED` record
maps conservatively to `UNVERIFIED + UNCONFIRMED`, never to `CERTIFIED`.

## License and security

ProofWeave Core is available under the [MIT License](LICENSE). Report suspected
vulnerabilities through [SECURITY.md](SECURITY.md), not a public issue.
