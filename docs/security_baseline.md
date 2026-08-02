# Security baseline snapshot

This document records the repository-content baseline prepared on 2026-08-02.
It is an audit checkpoint, not a claim that the project is free of
vulnerabilities.

## Fixed review point

- Repository: `f0909172434/proofweave-math-lab`
- Baseline commit: `4d9e1bce919f329a54d0a5d38b60e77629489a13`
- Product status: experimental `0.1`
- Public author metadata: Wang Chih Kai

The baseline commit identifies the code that was inspected before this
hardening change. Future reviews must record a new commit rather than silently
reusing this snapshot.

## Repository-managed controls

- cross-platform unit, graph, structure, and release checks with a stable
  `ci-gate` result;
- Python CodeQL analysis using GitHub's repository-native action;
- Dependabot update definitions for Python and GitHub Actions;
- full commit-SHA pins for every workflow action, with version comments;
- a private vulnerability-reporting policy, contribution rules, templates, and
  explicit threat/data/credential boundaries.

## Owner-managed controls still requiring live verification

Files in a commit cannot activate repository settings. Before treating this
baseline as enforced, the owner must verify the live GitHub state and record the
result:

1. Enable Dependabot alerts and security updates.
2. Enable secret scanning and push protection where the account and repository
   plan support them.
3. Create a disabled `main` ruleset that requires pull requests, `ci-gate`, and
   `CodeQL (python)`; block deletion and force pushes without requiring a
   second reviewer. GitHub Free does not provide ruleset evaluate mode, so keep
   the ruleset disabled until the named checks have succeeded on a pull request.
4. Create the immutable `v*.*.*` tag ruleset disabled, inspect its target, then
   activate it. A moving `v1` tag, if the project later publishes one, must be
   updated only by an approved release workflow.
5. Confirm private vulnerability reporting is available.
6. After observing the expected checks on a pull request, activate the disabled
   rulesets and record their identifiers and activation date outside this
   snapshot.

These settings remain **unverified** until checked against the live repository.

## External security scanning boundary

Codex Security results are deliberately not stored in this repository. A scan
must target an exact commit, keep raw output in a private directory outside the
clone, and report coverage as `complete`, `partial`, or `unknown`. No scan in
this snapshot may be described as complete unless that status was returned by
the scanner. Critical and high findings block release; medium and low findings
need a fix, an explicit risk decision, or a tracked follow-up before a security
maturity claim.
