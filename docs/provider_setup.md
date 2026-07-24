# Provider setup

Initialization enables no external API, gateway or CLI subprocess model call.
The native Codex desktop session is represented by `host_native`; installed
Codex/Claude CLIs are detected but disabled for subprocess routing.

## Before enabling any provider

1. Read the current official provider/host documentation and terms.
2. Decide permitted data classes, network destinations and retention/privacy.
3. Configure credentials outside the repository; never pass secrets in CLI
   arguments or routing logs.
4. Record model/account availability evidence, tool/context/effort support,
   snapshot/alias behavior, rate limits and estimated costs.
5. Set task/workflow/daily/monthly limits and confirmation threshold.
6. Run only an explicitly approved minimal probe if passive evidence is
   insufficient; record that it may cost money.
7. Validate fallback and failure behavior before using the provider on research.

## Adapters

`codex_adapter.py` and `claude_code_adapter.py` build official CLI dry-run plans
and execute only with explicit authorization. OpenAI, Anthropic,
OpenAI-compatible and gateway adapters report configuration/dry plans but do not
pretend live support. They remain EXPERIMENTAL/DISABLED until a reviewed executor
and current API contract are supplied.

Modify `config/runtime_policy.json` deliberately. A requested but unavailable
model is reported; it is never silently replaced. High-risk use of an unsuitable
requested model produces a warning/failure rather than lowering the gate.

MathSciNet automation is not a provider adapter: its official terms prohibit
general scripted harvesting. Semantic Scholar stays disabled until its current
license is accepted. arXiv requester-pays bulk data and other charged services
require separate cost authorization.

