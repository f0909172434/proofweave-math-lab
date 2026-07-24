# 16 Model routing

## Purpose

Classify a task and recommend the lowest sufficient verified model/effort with an auditable fallback and budget decision.

## Entry gate

Model inventory, user/provider/privacy policy and budget state are current; the task is a versioned file.

## Inputs

Task type/domain/depth/novelty/error cost/context/tools/ambiguity/risk/latency/cost/privacy plus previous worker execution profile.

## Required stages

1. Compute complexity/risk from semantics, dependencies and error cost—not prompt length alone.
2. Exclude unavailable, unverified-unapproved, deprecated, forbidden, tool-deficient, context-deficient and privacy-incompatible models.
3. Score capability, benchmark, tools, context, reliability and independence minus cost, latency, deprecation, availability and correlation risks.
4. Map abstract NONE–MAXIMUM effort to actual supported settings and record native, loop-based or unsupported control.
5. Check budget before selection/escalation; bound reasoning/model/provider/repair loops.
6. Prefer a different family/provider/method for high-risk verifier work; model voting never replaces proof.
7. Write a redacted deterministic routing record and fallback chain.

## Output gate

A schema-valid RECOMMENDED, ADVISORY_ONLY, BLOCKED_BY_BUDGET, NEEDS_HUMAN_DECISION or ROUTING_FAILED record.

## Verification gate

Same task and inventory version produce the same decision. Routing logs contain no secrets and cannot claim a switch that did not execute.

## Stop conditions

Stop when no compliant route exists; return advisory/manual status rather than silently substituting a model.

## Escalation

Escalate verifier uncertainty/rejection, conflicts, counterexamples, unjustified analytic exchanges, grid sensitivity or main-conclusion impact in the configured order.

## Handoff record

Record task hash, scores, selected/rejected candidates, effort mapping, cost, independence, fallback, inventory version and execution result.

