# ProofWeave Core v2 threat model

## Scope and assets

This model covers the ten-module `proofweave` runtime, three JSON schemas, four
CLI commands, the one-time v1 migration tool, Lean/Mathlib certification,
content-addressed artifacts and caches, evidence evaluation, CI, and release
bundles.

Protected assets are exact claim meaning, dependency topology, certificate and
coverage results, alignment/lifecycle separation, cache identity, retained
artifacts, release provenance, and repository credentials.

## Trust boundaries

Untrusted inputs include theorem Markdown, pack and migration files, claim IDs,
paths, cached artifacts, alignment attestations, and pull-request code. Lean,
Lake, Git, and Mathlib checkouts are external execution dependencies whose
observed identity is bound or explicitly treated as a host limitation. Hosted
runners and the operating system remain outside that identity boundary.

Core does not trust model output, confidence, votes, reviewer roles, finite
search, test coverage, or a human alignment statement as a machine certificate.

## Required security properties

1. Certification preserves statements, assumptions, quantifiers, and dependency IDs.
2. Claim and proof dependency graphs are acyclic.
3. Cache keys bind all semantic inputs, dependency certificates, certifier and
   Lean identities, certificate view, and dependency closure.
4. `CERTIFIED` is derived only from a deterministic certificate with complete
   deductive coverage of the exact formal target.
5. Workspace, manifest, and checksum paths remain inside their declared roots;
   migration validates claim IDs and output containment before writing.
6. Missing, mismatched, timed-out, skipped, or error-producing formal tooling
   fails closed as `PARTIAL`, `HOST_LIMITED`, or failure rather than success.
7. Runtime code imports neither model infrastructure nor `tools/migrate_v1.py`.

## Attack surfaces and controls

### Structured Markdown and schemas

Malformed or adversarial claims can hide assumptions, duplicate IDs, dependency
cycles, or path traversal. Parsing is deterministic, schemas reject invalid
instances, dependency closure is explicit, and root containment is tested.

### Lean certification

Generated Lean could attempt `sorry`, axioms, arbitrary imports or tactics,
unsafe/meta execution, or statement substitution. Core emits a fixed import,
accepts an enumerated tactic surface, binds the exact target, rejects forbidden
constructs and error diagnostics, and requires the pinned toolchain when formal CI is
mandatory.

### Cache and artifact reuse

An incomplete cache key or mutable dependency tree could replay a certificate
under different semantics. The fingerprint binds lockfiles, executable and Git
identity, toolchain libraries, package checkouts, and semantic artifacts. Dirty
checkouts, invalid package names or revisions, and ancestor-repository layouts
fail closed.

### Migration

Legacy `VERIFIED` or reviewer status could be mistaken for a certificate.
Migration preserves formal content but maps review status to `UNVERIFIED` and
alignment to `UNCONFIRMED`; revoked/superseded state affects lifecycle only.

### CI and releases

Unpinned actions, write-capable default tokens, credential persistence, fork
execution, partial matrix success, or mutable assets can compromise evidence.
Workflows use read-only top-level permissions, full-SHA action pins, disabled
checkout credential persistence, explicit aggregate gates, checksum validation,
and isolated release-job write permissions.

## Residual risks and non-claims

The operating system, administrator, kernel, compiler bootstrap, and network
remain outside a user-space proof. Hosted images and package mirrors can drift.
Coverage and a finite adversarial corpus measure exercised behavior but are not
a global soundness theorem. Lean proves only the elaborated formal target.
Natural-language alignment and reviewer competence require separate human
judgment. Failure to find a published solution is not proof of novelty.
