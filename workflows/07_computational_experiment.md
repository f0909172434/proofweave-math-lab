# 07 Computational experiment

## Purpose

Create reproducible symbolic/numerical evidence without presenting floating-point output as proof.

## Entry gate

The mathematical question, acceptable evidence class, method, cost estimate, error targets and stop criteria are explicit.

## Inputs

Versioned config, executable script, environment, parameters, tolerances, seeds, initial data and solver choices.

## Required stages

1. Save configuration, code, environment, raw data path, report path and exact reproduction command.
2. Test multiple grids/steps, tolerances, initial values, endpoint parameters and at least one alternative solver when applicable.
3. Estimate floating-point, discretization and solver error; check root-finding coverage and sensitivity.
4. Generate figures/tables only from saved raw data and label the tested parameter domain.
5. Record hardware/version/seed and every failure or unstable regime.
6. Have a numerical reproducibility auditor rerun the experiment from artifacts.

## Output gate

Config, script, environment record, raw data, output, report, reproduction command and limitations exist. Status remains numerical evidence/empirical observation.

## Verification gate

Analytic consequences require a separate proof. Grid agreement, many samples and absence of a found counterexample are not proof.

## Stop conditions

Stop on irreproducibility, unresolved solver instability, unbounded cost or evidence that does not answer the stated question.

## Escalation

Escalate grid-sensitive signs, missed-root risk, endpoint failures or conflict with an analytic claim.

## Handoff record

Record experiment ID, commands, environment, inputs, hashes/paths, sensitivity results, failures, evidence scope and next action.

