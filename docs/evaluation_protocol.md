# Evaluation and theorem-pack protocol

## Purpose and status boundary

The evaluator creates reproducible evidence for a fixed Core corpus or one
research theorem pack. A passing bundle is `COMPUTATIONAL` evidence about the
recorded implementation, corpus, commit, environment, and formal targets. It is
not a global soundness proof, a natural-language alignment proof, or a novelty
determination.

The evaluator performs no model calls and never passes
`confirm_alignment=True`. Human alignment is accepted only from a
version-controlled, hash-bound attestation supplied by a theorem pack.

## Reproducing the Core evaluation

Use a clean checkout of the commit being evaluated. Certification requires the
project-pinned Lean 4.32.2 and Mathlib 4.32.2 environment.

```powershell
py -3.14 -m pip install -e . -r requirements-test.txt
lake update mathlib
lake exe cache get
$env:PROOFWEAVE_REQUIRE_LEAN = "1"
py -3.14 -m coverage run -m unittest discover -s tests -v
py -3.14 -m coverage report --fail-under=90 --show-missing
py -3.14 -m proofweave check
py -3.14 -m tools.evaluate core --output artifacts/evaluation
git diff --exit-code
Remove-Item Env:PROOFWEAVE_REQUIRE_LEAN
```

With `PROOFWEAVE_REQUIRE_LEAN=1`, an unavailable Lean/Mathlib environment or a
skipped formal test is a failure, never a successful partial evaluation.

The fixed corpus contains 42 stable case IDs: 14 positive obligations (two per
allowlisted tactic), 14 paired negative obligations, 8 escape attempts, and 6
fail-closed state/integrity cases. The evaluator also performs a cold/warm
replay. Acceptance requires all positive cases to pass, zero false
certifications, zero accepted attacks, all fail-closed cases to match their
expected status, at most one cold Lean batch, and zero model, semantic, and
Lean invocations on the unchanged warm run.

## Bundle contract

Both evaluator modes write the same evidence layout:

```text
evaluation.json
summary.md
environment.txt
SHA256SUMS
certificates/*.lean
```

`evaluation.json` records the Git commit and tracked dirty state, corpus/input
digest, Python/OS and Lean/Mathlib fingerprints, individual results, metrics,
and a `normalized` object. `normalized` deliberately excludes timestamps and
host-specific environment fields; it includes the corpus digest, retained
certificate-source digests, expected/observed results, and replay metrics.
Ubuntu and Windows release evidence must have byte-equivalent canonical
`normalized` JSON. Every other bundle file is covered by `SHA256SUMS`.

The retained `.lean` files are the exact certificate sources submitted during
evaluation. Their digests support integrity and replay; neither a digest nor a
GitHub provenance attestation independently proves the theorem.

## Theorem-pack manifest

Keep unfinished research outside the Core repository. At the root of a research
workspace, create a `PACK.toml` whose paths stay inside that workspace:

```toml
schema_version = 1
pack_id = "example-pack-v1"
title = "Example theorem evidence pack"
sources = ["DOI or stable source URL", "independent source URL"]
research_status = "OPEN"
dependencies = []

[[claims]]
id = "example-lemma"
path = "claims/example-lemma.md"
expected_proof_status = "CERTIFIED"
alignment_attestation = "attestations/example-lemma.toml"
```

The schema recognizes `OPEN`, `PROPOSED`, `COMPUTATIONAL`, and `VERIFIED` so it
can reject an unsupported promotion explicitly. Schema v1 can successfully
evaluate only `OPEN`, `PROPOSED`, and `COMPUTATIONAL`. Every v1 pack marked
`VERIFIED` fails closed because v1 cannot encode version-bound cold replay,
literature novelty recheck, and independent human-review evidence. Expected
proof statuses are `UNVERIFIED`, `PARTIAL`, `CERTIFIED`, and `FAILED`. Claim IDs
must match the structured-Markdown `claim_id`. Sources must not be empty, claim
IDs must be unique, and claim/attestation paths may not escape the pack
directory.

Evaluate the pack without changing Core state:

```powershell
py -3.14 -m tools.evaluate pack PACK.toml --output artifacts/evaluation
git diff --exit-code
```

The command returns 0 only when every expected proof status matches and the
research status is supported by schema v1. Even when Lean certificates,
alignment attestations, and dependency closure pass, a v1 `VERIFIED` pack
returns `FAIL`. A pack result of `PASS` is necessary evidence, not permission to
promote research status.

## Human alignment attestation

An attestation is a separate TOML file committed with the research pack:

```toml
schema_version = 1
attestation_id = "example-lemma-alignment-v1"
claim_id = "example-lemma"
statement_hash = "<64 lowercase hexadecimal characters>"
formal_target_hash = "<64 lowercase hexadecimal characters>"
alignment_hash = "<64 lowercase hexadecimal characters>"
reviewer = "<human reviewer identity>"
reviewed_at = "<ISO 8601 timestamp>"
```

The evaluator recomputes all three hashes. To obtain the values for human
review, inspect the exact prose and formal target first, then run this read-only
helper from the Core checkout:

```powershell
py -3.14 -c "from pathlib import Path; from proofweave.core import hash_json, parse_input; p=parse_input(Path(r'claims/example-lemma.md')); f=hash_json(p['top_certificate']['target']); print('statement_hash =',p['statement_hash']); print('formal_target_hash =',f); print('alignment_hash =',hash_json({'statement_hash':p['statement_hash'],'formal_target_hash':f}))"
```

Any statement or formal-target change invalidates the attestation. CI must not
create or refresh this file. Reviewer identity and approval remain human
controlled. Blank attestation/reviewer identities, malformed timestamps, and
timestamps without an explicit timezone are invalid. Evaluator status `VALID`
means only that the record is structurally valid and its hashes match; it does
not authenticate the reviewer or establish the reviewer's competence.

## CI and release evidence

`.github/workflows/ci.yml` runs the branch-aware suite on Python 3.11 and 3.14
across Ubuntu and Windows, enforces at least 90% coverage, and runs real pinned
Lean certification on both operating systems with
`PROOFWEAVE_REQUIRE_LEAN=1`. All Actions are pinned to immutable commit SHAs.

`.github/workflows/evidence.yml` builds two-platform evidence on manual dispatch
and `v*.*.*` tags, verifies each checksum manifest, and rejects differences in
normalized results. Manual runs upload candidate evidence only. A tag run
creates provenance attestations and a **draft** GitHub release; it never
publishes the release. GitHub's attestation binds artifacts to repository,
workflow, and commit provenance, not mathematical truth. See the official
[artifact-attestation documentation](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
and the official [Lean action](https://github.com/leanprover/lean-action).

After an independent human review, a maintainer may publish the draft. If the
repository supports immutable releases, locking is a separate human-controlled
post-publication action; see GitHub's
[immutable-release documentation](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).

## Research promotion rule

Schema v1 must retain `OPEN`, `PROPOSED`, or `COMPUTATIONAL`; it cannot represent
a successful `VERIFIED` pack. A future evidence-schema version may support that
promotion only after it version-binds all of the following:

1. a passing Lean certificate for every required formal target;
2. a valid human alignment attestation for every required claim;
3. complete certified dependency closure;
4. a successful cold-start replay from the pinned environment;
5. a dated literature and forward-citation novelty recheck; and
6. an independent human mathematical review.

Finite scans never promote a claim to theorem status. Failure to find a later
solution is recorded as `OPEN` search evidence and is not proof of openness or
novelty. Coverage percentage measures exercised code paths and must not be
described as a soundness guarantee.
