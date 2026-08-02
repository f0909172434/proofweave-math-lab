# Threat model

## Assets and trust boundaries

Protected assets are mathematical truth status, source/experiment provenance,
manuscript integrity, private research data, credentials, budget/quota and
reproducible history. Untrusted inputs include model output, web/MCP content,
uploaded papers, external code/data, source metadata and worker memory. A
VERIFIED project fact remains fallible and revocable.

Repository files and deterministic Python checks are the durable control
plane. Native agent prompts, chat history, model identity, and the operating
system account are outside that control plane and must not be treated as a
sandbox or proof boundary.

## Data boundaries

- **Public tracked data:** anything committed to this repository must be
  treated as public, including examples, logs, reports, source metadata, and
  Git history. Do not commit unpublished research or personal data to a public
  clone.
- **Local private data:** operator-approved private inputs belong only in
  ignored locations such as `state/private/` or another access-controlled
  directory outside the repository. Ignore rules reduce accidental commits but
  are not encryption or access control.
- **Restricted data:** credentials, identity documents, regulated data, and
  third-party confidential material must not enter context packets, prompts,
  logs, fixtures, issues, or release artifacts.
- **External inputs:** web pages, papers, archives, MCP results, model output,
  and contributed code are untrusted until their provenance, license, and
  content are reviewed.
- **Generated output:** reports can echo source text, local paths, and tool
  output. Inspect and redact them before sharing, committing, or attaching them
  to an issue.

The standard-library core does not require network access. Browsers, MCP tools,
hosted agents, and explicitly enabled provider adapters cross the local data
boundary and may transmit selected content under their own terms. Detection or
configuration is not consent to transmit data.

## Credential boundaries

The core CLI and CI test suite require no API key. Real credentials must never
be committed, placed in command-line arguments, copied into research state, or
printed to logs. `.env.example` contains names only; a local `.env` is ignored
and is permitted only for an explicitly authorized provider workflow.

GitHub Actions run with least-privilege tokens: ordinary CI receives read-only
repository contents, while CodeQL alone receives `security-events: write` for
uploading analysis. Pull-request workflows do not receive project secrets and
must not use `pull_request_target` to execute untrusted code. Provider keys and
publication credentials are outside ProofWeave's trust boundary and remain
operator-managed.

## Main threats

- plausible invalid proof or circular dependency enters the truth layer;
- worker self-verifies or orchestrator/writer bypasses the verifier;
- numerical scan, consensus or confidence is upgraded to theorem;
- citation exists but does not entail the sentence, or has license/version
  problems;
- hidden assumptions, endpoint failures or unjustified analytic exchanges;
- stale/wrong model identity, unsupported effort or fake model switch;
- correlated author/verifier errors;
- revocation fails to invalidate descendants/manuscript claims;
- prompt injection in web/PDF/MCP content changes tool behavior;
- unbounded agents/repair loops exhaust quota;
- secrets/private data enter state, logs, subprocess arguments or providers;
- unsafe external code, destructive commands, upload/push/publish without
  authority.

## Controls

Programmatic role/independence/dependency/cycle gates; cold-start verification;
opened-source records and citation audit; evidence-class schemas; reproducible
experiment manifests; cascade revocation; claim-map/release checks; model
availability states and deterministic routing; redacted logs; disabled paid
probes/providers; bounded parallelism/escalation; `.gitignore` and secret scan;
safe CLI flags; human approval for cost/external side effects.

Native role files are prompts rather than security boundaries. Deterministic
Python checks and OS/host permissions are the enforcement layer. MCP, hooks and
provider adapters require separate review and least privilege.

## Residual risk

An independent AI verifier may accept a false proof, humans may formalize the
wrong statement, source registries may contain errors and secret scanners can
miss formats. Core results therefore retain expert-review requirements; high
risk lemmas should additionally use different methods/models, adversarial
counterexample search and, when cost-effective, pinned formalization.

## Incident response

On suspected error: freeze release, revoke the fact, cascade descendants, open
a FATAL/MAJOR issue, preserve the failed artifacts, rerun source/experiment
checks, repair with a new fact version, independently reverify and repeat the
full paper review. On secret exposure: stop tools, remove/rotate the credential
outside this repository, sanitize logs/history and record the incident without
the secret value.

Report suspected vulnerabilities through the private process in
[`SECURITY.md`](../../SECURITY.md).
