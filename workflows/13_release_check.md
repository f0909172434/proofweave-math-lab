# 13 Release check

## Purpose

Apply deterministic final gates before a manuscript/system artifact is called release-ready.

## Entry gate

Writing/revision has stopped; graph, sources, issue ledger, experiments, claim map and LaTeX are frozen.

## Inputs

Repository snapshot, model inventory, routing/audit logs, paper and all research artifacts.

## Required stages

1. Validate schemas, fact DAG, VERIFIED dependencies, revocations and source registry.
2. Require every formal LaTeX claim to map to a VERIFIED fact.
3. Check bibliography registration and citation entailment audit status.
4. Check experiment reproduction commands, environments, data/report paths and limitations.
5. Run unit tests, secret scan and provider/routing-policy checks.
6. Compile LaTeX when a compiler is installed; record HOST_LIMITED otherwise.
7. Verify no FATAL/MAJOR issue remains open and disclaim AI-verifier limitations.

## Output gate

Machine-readable PASS/FAIL report with warnings. Publishing/pushing remains a separate explicitly authorized action.

## Verification gate

Any failed mandatory gate blocks release. A budget shortage never converts a failure into acceptance.

## Stop conditions

Stop on the first unsafe external action; otherwise collect all validation failures in one report.

## Escalation

Escalate open fatal/major issues, secrets, invalid truth state, failed compilation or HOST_LIMITED mandatory tooling.

## Handoff record

Record snapshot, commands, test counts, compiler result, failures/warnings, limitations and exact next repair.

