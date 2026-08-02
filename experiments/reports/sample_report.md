# Experiment harness smoke test

## Question

Can the repository execute a recorded, dependency-free experiment command from its root?

## Configuration

`experiments/configs/sample_experiment.yml`; Python 3.11+; no seed, grid or numerical solver.

## Result

The script checks that the supplied config exists, prints a JSON PASS record and exits 0.

## Reproduction

```powershell
py -3.12 experiments/scripts/sample_experiment.py --config experiments/configs/sample_experiment.yml
```

## Limits of inference

This tests only the experiment harness. It produces no mathematical or numerical evidence and proves no theorem.
