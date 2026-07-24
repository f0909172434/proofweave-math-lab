# 03 Idea swarm

## Purpose

Generate three to five genuinely different seed ideas, then compare them without using model voting as a truth test.

## Entry gate

`problem.md`, explicit assumptions/notation, risk list, verified prerequisites, task budget, and termination criteria exist.

## Inputs

Formal target; verified fact IDs; opened source IDs; permitted tools; maximum workers and cost.

## Required stages

1. Produce at least one direct route, one different method, one obstruction/counterexample route, and one toy/special-parameter route.
2. For every route record prerequisites, candidate lemmas, tools, risks, measurable milestones, cost estimate and stop condition.
3. Parallelize only routes whose writes and mathematical dependencies are independent; otherwise run sequentially.
4. Assign a counterexample hunter and toy-model explorer when universal or global claims are present.
5. Stop each route at a verifiable local claim, a valid counterexample, a documented obstruction, or its resource cap.
6. Preserve failures and compare routes by evidence, tractability, risk and cost—not majority agreement.

## Output gate

A versioned strategy portfolio plus worker artifacts; every mathematical result remains DRAFT/PROPOSED/refuted/open until separately verified.

## Verification gate

Dependencies and source entailment are checked. Any PROPOSED claim goes to a cold-start theorem verifier; the generating worker cannot promote it.

## Stop conditions

Stop when all routes reach a defined terminal state or the bounded budget is exhausted. Mark unresolved work OPEN GAP.

## Escalation

Escalate conflicting assumptions, suspected counterexamples, two no-progress attempts, or a risk increase to the orchestrator.

## Handoff record

Record task/route IDs, owners, execution profiles, artifacts, statuses, failed approaches, costs, open gaps and recommended next route.

