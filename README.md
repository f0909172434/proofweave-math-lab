# ProofWeave（證明織網）

**Auditable mathematics research, woven from claims, evidence, and independent verification.**

ProofWeave is a local, model-independent workspace for mathematical
research, paper writing and adversarial review. Its core is persistent files and
deterministic gates—not chat history. It separates proof, literature results,
numerical evidence, conjecture and open gaps, and records every model-routing
decision without treating model agreement as truth.

## What is implemented

- fact DAG with cycle prevention and VERIFIED-only formal dependencies;
- cold-start, independent-verifier-only promotion;
- transitive revocation cascade and impact metadata;
- validated source registry and revision issue ledger;
- experiment, bibliography, LaTeX claim-map and secret checks;
- passive host/provider/model detection with MODE A–E classification;
- deterministic task, reasoning, model, fallback and budget routing;
- benchmark harness that refuses live/paid calls and fake rankings by default;
- 28 canonical roles, 18 workflows, 14 prompts, 12 schemas and native
  Codex/Claude adapters that point back to the canonical files;
- isolated odd-sum proof workflow and six dry routing demonstrations;
- standard-library Python CLI and automated tests.

`VERIFIED` is a project workflow status. It is not human peer review or formal
certainty. Lean support is optional and counts as machine-checked only after a
pinned build with no disallowed `sorry`, `admit` or unexpected axioms—and a
human still checks that the formal statement matches the intended theorem.

## Quick start

Use Python 3.11 or newer from the repository root:

```powershell
python -m mathlab init
python -m mathlab status
python -m unittest discover -s tests -v
python -m mathlab release-check
```

On this Codex desktop host, the tested interpreter is bundled with Codex and the
bare `python` Windows alias is not reliable. The equivalent verified commands
are:

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m mathlab status
& $py -m unittest discover -s tests -v
& $py -m mathlab release-check
```

The experiment gate resolves a leading `python`, `python3` or `py` in recorded
reproduction commands to the interpreter running ProofWeave.

To start the first real project, edit `state/problem.md`,
`state/assumptions.md`, `state/notation.md` and `state/research_plan.md`. Then
give your agent this prompt:

> Read AGENTS.md and workflows/00_project_intake.md. Formalize the research
> question currently written in state/problem.md. Do not attempt a proof yet.
> Produce explicit domains, quantifiers, assumptions, notation, Definition of
> Done and an initial risk list. Separate theorem targets, conjectures,
> numerical questions and literature questions, update only the intake state
> files, and report every ambiguity as OPEN GAP or a human decision.

## Research flow

1. Intake and formalization.
2. Reproducible source search; open and verify exact support.
3. Three to five distinct strategies with bounded proof, obstruction and toy
   routes.
4. Local PROPOSED claims and counterexample attempts.
5. Independent theorem verification through the CLI gate.
6. Reproducible experiments where useful, always labeled as evidence.
7. Paper planning/writing from a frozen VERIFIED graph and complete claim map.
8. Full mathematical/referee review, revision and release check.
9. Session handoff preserving status, gaps, dead ends and decisions.

See `docs/operator_guide.md`, `docs/workflow_guide.md` and
`docs/design/architecture.md`.

## CLI

Research state:

```powershell
python -m mathlab add-source --file source.json
python -m mathlab add-claim --file claim.json
python -m mathlab verify FACT_ID --outcome ACCEPT --verifier NAME --report report.json
python -m mathlab revoke FACT_ID --reason "reason" --actor NAME
python -m mathlab graph-check
python -m mathlab experiment-check
python -m mathlab paper-check
python -m mathlab review --mode blind-referee
python -m mathlab release-check
```

Capabilities and routing:

```powershell
python -m mathlab models detect
python -m mathlab models list
python -m mathlab models show MODEL_ID
python -m mathlab models doctor
python -m mathlab models refresh
python -m mathlab models benchmark
python -m mathlab route classify TASK_FILE
python -m mathlab route recommend TASK_FILE
python -m mathlab route explain ROUTING_ID
python -m mathlab route run TASK_FILE
python -m mathlab route history
python -m mathlab budget status
python -m mathlab budget estimate TASK_FILE
python -m mathlab providers status
```

`route run` is a recorded dry handoff for native mode; it does not secretly
invoke an external provider. CLI/API/gateway execution stays disabled until the
operator explicitly changes `config/runtime_policy.json` and accepts quota,
privacy and cost consequences.

## Demonstrations

```powershell
python -m scripts.run_toy_workflow
python -m scripts.run_routing_demo
python -m scripts.compile_paper
```

The toy workflow accepts a correct induction proof, rejects an approximation
gap, maps the accepted fact to LaTeX and compiles with `pdflatex` when present.
Every successful release writes `state/release_report.json` and a
content-addressed `state/release_manifest.json`; this gives an exact file-hash
snapshot even before the operator configures a Git author and creates a commit.

## Native agents and skills

- `agents/` is the canonical policy source.
- `.codex/agents/` and `.claude/agents/` are generated thin adapters.
- `.agents/skills/` and `.claude/skills/` expose workflow entry points.
- Regenerate them with `python -m scripts.generate_native_adapters` after role
  or workflow changes.
- `.claude/settings.example.json` is an opt-in hook example; review current
  Claude Code documentation before enabling it.

## Safety and cost defaults

No real `.env` is created. Secrets, cookies and tokens are forbidden in state
and logs. Paid probes, provider APIs, CLI subprocess agents, publishing,
pushing, uploading and messaging are disabled unless explicitly authorized.
Parallel agents and escalation loops are bounded. A budget failure returns
`BLOCKED_BY_BUDGET` or `NEEDS_HUMAN_DECISION`; it never weakens verification.

Source and licensing decisions are recorded in
`docs/design/source_basis.md` and `state/source_registry.jsonl`. Danus was
studied but neither copied nor installed.
