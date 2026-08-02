# Security policy

ProofWeave is experimental research infrastructure. Security controls reduce
risk but do not guarantee the absence of vulnerabilities or mathematical
errors.

## Supported versions

| Version | Support |
| --- | --- |
| Current `main` branch | Active security fixes |
| Most recent `0.1.x` tag, if published | Best effort |
| Older snapshots and forks | Not supported by this repository |

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability. Use
[GitHub's private vulnerability reporting form](https://github.com/f0909172434/proofweave-math-lab/security/advisories/new).
If that form is unavailable, open a public issue containing no exploit details,
credentials, private research, or sensitive paths and ask the maintainer for a
private reporting channel.

Include only the information needed to reproduce and assess the problem:

- the affected commit, platform, Python version, and component;
- a minimal reproduction or proof of concept with secrets removed;
- the expected and observed security boundary;
- likely impact and any known workaround;
- whether the report is safe to reproduce in a disposable local clone.

Never send live API keys, tokens, cookies, private keys, personal data, or
unpublished research. Revoke an exposed credential immediately through its
provider; repository cleanup is not a substitute for rotation.

## What belongs in a security report

Examples include arbitrary code execution, path traversal, secret disclosure,
unsafe workflow permissions, dependency or release-chain compromise, and a
programmatic bypass that lets an unauthorized role change truth status. A
disagreement about a proof is normally a research-correctness issue, but report
it privately when public disclosure would expose sensitive material or a
repeatable integrity bypass.

## Response and disclosure

The maintainer will validate reports as capacity permits, keep confirmed issues
private while a fix is prepared, and credit reporters who request credit.
There is no guaranteed response-time SLA for this experimental project. Please
coordinate public disclosure until a fix or reasonable mitigation is available.

See the [threat model](docs/design/threat_model.md) for trust, data, credential,
and residual-risk boundaries.
