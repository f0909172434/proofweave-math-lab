# Security policy

ProofWeave Core v2 is experimental research infrastructure. Security controls
reduce risk but do not guarantee the absence of software vulnerabilities or
mathematical errors.

## Supported versions

| Version | Support |
| --- | --- |
| Current `main` branch | Active security fixes |
| Most recent published `v*.*.*` tag, if any | Best effort |
| Older snapshots and forks | Not supported by this repository |

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability. Use
[GitHub private vulnerability reporting](https://github.com/f0909172434/proofweave-math-lab/security/advisories/new).
If that form is unavailable, open a public issue containing no exploit details,
credentials, theorem text, private research, or sensitive paths and ask for a
private reporting channel.

Include only what is needed to reproduce and assess the issue:

- affected commit, platform, Python/Lean/Mathlib versions, and component;
- a minimal sanitized reproduction;
- the expected and observed integrity boundary;
- likely impact and any known workaround;
- whether reproduction is safe in a disposable clone.

Never send live credentials, cookies, private keys, personal data, or
unpublished research. Rotate exposed credentials immediately; repository
cleanup is not a substitute for rotation.

## Security and integrity issues

Report arbitrary code execution, path traversal, secret disclosure, unsafe
workflow permissions, dependency or release compromise, and programmatic
bypasses such as:

- changing a statement, assumption, quantifier, or dependency during certification;
- accepting cyclic claim or proof dependencies;
- deriving `CERTIFIED` without a deterministic certificate and complete coverage;
- omitting semantic inputs from a cache key or reusing a certificate across differing bound toolchain/dependency environments;
- escaping the pinned Lean import/tactic policy with `sorry`, axioms, unsafe/meta code, or arbitrary imports;
- accepting missing tooling, skipped checks, tampered artifacts, or invalid checksums;
- upgrading migrated v1 review status into a Core v2 certificate;
- treating alignment attestations or finite evaluation as a theorem proof.

A mathematical disagreement without a repeatable integrity bypass normally
belongs in the research-correctness issue form.

## Response and disclosure

Reports are handled as maintainer capacity permits. Confirmed issues remain
private while a fix or mitigation is prepared. There is no guaranteed response
time for this experimental project. Coordinate disclosure until a fix or
reasonable mitigation is available.

See `docs/design/threat_model.md` for trust boundaries and residual risks.
