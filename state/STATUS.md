# Status

Updated: 2026-07-24

## Current objective

Initialize and validate ProofWeave. No real mathematical research problem has been entered.

## Verified results

- No production mathematical facts. The production fact graph is empty.
- The isolated odd-sum toy workflow has its own VERIFIED demonstration fact and is not part of production truth.

## Proposed results

- None.

## Refuted claims

- None in production. The toy workflow contains one deliberately rejected proof packet.

## Active workers

- None.

## Blocking gaps

- The first real research question, assumptions and notation are not yet supplied.
- No live provider API/gateway/CLI-subprocess executor is configured; native host routing is available in this Codex task.
- Benchmark answer keys have not received independent human review; no performance ranking is available.
- No Git author is configured, so the exact content-addressed release manifest is
  the baseline and no local commit has been created.

## Failed approaches

- `latexmk` is installed but unusable because Perl is absent; direct `pdflatex` succeeds and is the tested compiler path.

## Latest experiments

- No production experiments.
- Toy odd-sum workflow, 71 automated tests and six dry routing demonstrations
  pass with zero paid provider calls; production and toy LaTeX compile directly.
- Independent release QA reproduced the prior edge cases and confirmed they now
  fail closed. See `state/release_report.json` for the current release result.

## Next recommended action

Enter the first research problem in `state/problem.md` and run workflows 00 and 01 without attempting a proof.

## Additional model usage justified

No additional model call is justified until a real problem is formalized. Paid probes remain disabled.

## Current execution mode

MODE_A_NATIVE_MULTI_MODEL for this Codex desktop session.

## Verified available models

See `state/model_inventory.json`; availability is host-session-scoped and must be refreshed in a future environment.

## Configured unverified models

The host advertises GPT-5.6 Luna, GPT-5.5 and GPT-5.4 Mini, but this project did not complete a successful dispatch for them. One GPT-5.5 dispatch attempt returned a host validation error. They remain CONFIGURED_UNVERIFIED and are excluded from automatic routing.

## Disabled models/providers

Codex CLI subprocess, Claude Code subprocess, OpenAI API, Anthropic API, OpenAI-compatible endpoint and gateway.

## Budget mode

BALANCED; no paid probes; bounded parallel/frontier/escalation counts.

## Recent routing decisions

Dry demonstration results are in `examples/routing_demo/results.json`; production routing log is empty.

## Escalations

None.

## Downgrades

Formatting and DOI tasks route to the lowest sufficient non-frontier profile in the dry demonstration.

## Tasks lacking independent verification

- Bundled benchmark answer keys require independent human review before model evaluation.
- Any future production theorem until a cold-start verifier report exists.
