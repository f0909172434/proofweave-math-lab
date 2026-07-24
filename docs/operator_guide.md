# Operator guide

## Start a project

Run `python -m mathlab init`, then fill the four intake files under `state/`.
State the mathematical domain, natural-language question, intended formal
claim(s), deliverable, time/cost limits, whether numerics/formalization are
allowed, and privacy/provider constraints. `workflows/00_project_intake.md` and
`01_problem_formalization.md` define the gates.

Do not add a claim before its domains, quantifiers, assumptions, notation and
exact target are explicit. A formal claim must list assumptions even when the
entry says “no additional assumptions.”

## Choose a workflow

- Unknown literature/status: workflow 02.
- Need distinct directions: 03.
- Local proof or counterexample: 04/05.
- Independent claim decision or revocation audit: 06.
- Symbolic/numerical evidence: 07.
- Lean feasibility/build: 08.
- Paper outline, writing, review or revision: 09–12.
- Final validation and handoff: 13–14.
- Model detection, routing or benchmark maintenance: 15–17.

The default is sequential. Parallel workers require independent dependencies,
non-overlapping write scopes, bounded count/cost and summary artifacts. Use an
evaluator-optimizer loop only with an explicit measurable rubric and iteration
cap.

## Add a source

Create a JSON object matching `schemas/source.schema.json`. FOUND means a lead,
OPENED means the original page/artifact was read, and VERIFIED means metadata,
exact supported claim and applicability were checked. Add with:

```powershell
python -m mathlab add-source --file source.json
```

Never use a search snippet as the verified source. Record conflicts and license
limits instead of resolving them silently.

## Add and verify a claim

Prepare a complete fact JSON matching `schemas/fact.schema.json`. Use
PROPOSED—not VERIFIED—and submit it:

```powershell
python -m mathlab add-claim --file claim.json
```

Give an independent theorem verifier only the explicit cold-start packet. The
verifier returns ACCEPT, REJECT or UNCERTAIN in a verification-schema record.
Only then run the verify command. The CLI rejects the proof author's identity,
wrong role, non-ACCEPT report, missing checklist, non-cold-start report,
unverified dependency or graph cycle.

If a verified fact fails, revoke it immediately:

```powershell
python -m mathlab revoke FACT_ID --reason "counterexample/source error" --actor NAME
```

Every descendant becomes REVOKED and must be removed/repaired in the paper and
experiments.

## Experiments and papers

Each experiment needs config, executable script, environment, raw data/output,
reproduction command and limitations. Run `experiment-check`. Paper writing
uses a frozen graph, labels every formal LaTeX environment and maps labels to
VERIFIED facts in `paper/claim_map.yml`. Each entry also records the current
LaTeX-body and normalized-fact-statement SHA-256 values plus an independent,
timezone-stamped `paper_math_verifier` attestation. This makes later text/fact
changes fail closed; the verifier still has to judge mathematical equivalence.
Run `paper-check`, compile and then conduct full review before release.

## Models, costs and failures

Refresh models at each materially different host/account session. Public model
lists are advisory. The current native MODE A inventory is host-scoped.
`route recommend` records a recommendation; `route run` makes no external call
in native mode. Provider/CLI/API execution is separately authorized.

On budget exhaustion, stop and record BLOCKED_BY_BUDGET or
NEEDS_HUMAN_DECISION. Do not use a weaker model to approve a proof merely to
finish. On provider failure use only a verified fallback; otherwise record
ROUTING_FAILED.

## Handoff

After material work, update STATUS, CHANGELOG, open gaps, dead ends and
decisions. The next session must be able to resume from files. End with tests,
release check, exact limitations and the next bounded action.
