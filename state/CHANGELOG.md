# Changelog

## 2026-07-24 — Initial validated system

- Researched and recorded official sources for Danus, OpenAI, Anthropic/Claude Code, Codex, Lean/mathlib and scholarly metadata services.
- Added canonical agents, workflows, prompts, schemas, model-independent state and native adapters.
- Implemented fact DAG, verifier gate, cascade revocation, source/issue registries, capability detection, routing, budgets, fallback, benchmarks and CLI.
- Added isolated toy proof workflow, dry routing demonstrations, LaTeX compilation and automated release checks.
- Recorded MODE A for the current host; external providers and paid probes remain disabled.
- Preserved known limitation: `latexmk` lacks Perl; tested `pdflatex` is used directly.
- Hardened the verifier gate after independent release QA: truth-layer kind
  separation, report identity/outcome/all-PASS/closure checks, transitive source
  coverage, exact formal-claim kind mapping and revocation impact reports.
- Added fail-closed privacy, cross-provider, deprecated fallback, paid/external
  approval, experiment command-binding and persistent-schema gates.
- Added whitespace/comment/custom-environment LaTeX detection, citation audit,
  PDF-inclusive content snapshots and paper-math statement digest bindings.
- Final regression suite contains 71 passing tests; independent QA reran the toy
  workflow, six routing demonstrations and LaTeX successfully.
