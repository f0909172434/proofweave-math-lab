# Benchmark methodology

## Purpose and categories

Benchmarks inform routing; provider marketing does not. The versioned suite
covers assumption consistency, proof-gap detection, counterexample validation,
asymptotic audit, algebra/sign audit, citation entailment, numerical
methodology, LaTeX/claim mapping, research planning and long-context
consistency.

## Dataset governance

Pin dataset and prompt versions. Separate public seed cases from hidden cases.
Keep hidden prompts/keys outside model-visible workspaces. The same model must
not create and certify its answer key. Record independent reviewer, provenance,
license, inclusion criteria, modifications and digest. Retest representative
cases after model/snapshot/prompt/adapter changes.

## Execution record

For each case save provider, model/snapshot, effort, prompt version, tools,
output, evaluator decision, correctness, false acceptance/rejection, latency,
estimated/actual cost and environment. Failures/timeouts count; do not discard
them. Use identical task inputs and inventory versions for comparisons.

## Metrics and routing use

Report sample size and uncertainty, overall/category accuracy, false acceptance,
false rejection, cost and latency. The theorem-verifier profile prioritizes low
false acceptance. Do not collapse sparse heterogeneous evidence into a precise
rank. This implementation requires the configured minimum case count and at
least two eligible models before emitting a ranking.

The ten bundled cases validate harness coverage only. They were generated
during initialization and require independent human key review before they can
measure a model. `python -m mathlab models benchmark` performs no model call.
Live execution remains disabled until the dataset and provider executor are
explicitly approved.

