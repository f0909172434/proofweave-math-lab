# Source basis

Access date for every source in this document: **2026-07-24 (Asia/Taipei)**.

This is an implementation evidence log, not a claim that any cited system proves
mathematical truth.  Official documentation, original papers, official
repositories, and standards bodies are preferred.  No Danus source code was
copied or installed; its architecture was studied and independently reimplemented
as a smaller standard-library Python system.

## Selection method

- Opened the original page, paper, repository, or official manual; search-result
  snippets were not treated as evidence.
- Recorded moving documentation as rolling documentation rather than inventing a
  publication date.
- Kept public availability, local installation, account availability, and tested
  executability as distinct states.
- Conflicts are retained below instead of silently selecting a convenient claim.

## Primary source matrix

| ID | Source | Author / organization | Date | Type and trust | Project use | Important boundary |
|---|---|---|---|---|---|---|
| SRC-DANUS-PAPER | [Danus: Orchestrating Mathematical Reasoning Agents with Fact-Graph Memory](https://arxiv.org/html/2607.06447) | Jihao Liu et al. | arXiv v2, 2026-07-08 | Original preprint; high for reported design, not independent validation | Fact DAG, separate truth/global/local memory, stateless verifier gate, cascade revocation, recovery | Informal verifier can miss gaps; cited facts may be wrong; cases are author-reported; expert review remains necessary |
| SRC-DANUS-REPO | [frenzymath/Danus](https://github.com/frenzymath/Danus) and [ARCHITECTURE](https://github.com/frenzymath/Danus/blob/main/ARCHITECTURE.md) | FrenzyMath | inspected 2026-07-24 | Official repository; high for implementation; Apache-2.0 | Role-gated writes, persisted rounds, content-addressed facts, crash recovery | Linux/WSL-oriented, external endpoints and keys required for many paths; README contains a dangerous-permissions example that this project does not adopt |
| SRC-DANUS-BLOG | [Danus technical introduction](https://frenzymath.com/blog/danus/) | FrenzyMath / AI4M, BICMR | 2026-07-07 | Official introduction; medium, derivative of paper | Terminology cross-check | Not independent evidence and no separate license statement |
| SRC-OAI-PROCESS | [Improving mathematical reasoning with process supervision](https://openai.com/index/improving-mathematical-reasoning-with-process-supervision/) and [Let's Verify Step by Step](https://cdn.openai.com/improving-mathematical-reasoning-with-process-supervision/Lets_Verify_Step_by_Step.pdf) | Karl Cobbe et al., OpenAI | 2023-05-31 | Original publication/paper; high for its experiment | Step-level checking, explicit first-error reports, false-acceptance emphasis | MATH benchmark result does not establish general theorem-verification reliability; authors note contamination and generalization limits |
| SRC-OAI-FIRSTPROOF | [Our First Proof submissions](https://openai.com/index/first-proof-submissions/) and [proof attempts](https://cdn.openai.com/pdf/26177a73-3b75-4828-8c91-e8f1cf27aaa0/oai_first_proof.pdf) | OpenAI | 2026-02-20 | Official research report and artifact; high for reported process | Long-chain proof attempts, expert feedback, rechecking and failure disclosure | One initially favored proof was later judged wrong; selection and interaction were not a controlled evaluation; correctness requires expert review |
| SRC-OAI-SCIENCE | [Early experiments in accelerating science with GPT-5](https://cdn.openai.com/pdf/4a25f921-e4e0-479a-9b38-5367b47e8fd0/early-science-acceleration-experiments-with-gpt-5.pdf) | OpenAI and collaborators | 2025-11 | Official case-study report; medium-high for reported cases | Separate generation from human checking; record failed attempts and scaffolding | Case studies are not a benchmark and do not justify automatic truth promotion |
| SRC-CODEX-MANUAL | [Codex manual](https://developers.openai.com/codex/codex-manual.md) | OpenAI | rolling; local cache confirmed current 2026-07-24 | Official manual; high for current documented behavior | AGENTS.md, project agents, subagents, model/reasoning settings, MCP, hooks, CLI | Surface/account availability can differ; current-session callable behavior wins when it conflicts with prose |
| SRC-ANTHROPIC-AGENTS | [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | Erik Schluntz, Barry Zhang / Anthropic | 2024-12-19 | Official engineering guidance; high for design patterns | Sequential, parallel, orchestrator-worker, evaluator-optimizer selection | Agentic designs increase latency, cost, and compounding-error risk; patterns are not math verification |
| SRC-ANTHROPIC-HARNESS | [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Justin Young / Anthropic | 2025-11-26 | Official engineering experiment; medium-high | Progress file, one-step sessions, smoke tests, git recovery | Tested mainly on software tasks; general multi-agent optimum remains unknown |
| SRC-ANTHROPIC-SCI | [Long-running Claude for scientific computing](https://www.anthropic.com/research/long-running-Claude) | Siddharth Mishra-Sharma / Anthropic | 2026-03-23 | Official research/implementation report; medium-high | Lab notebook, numerical oracle, dependency-topology-based parallelism | Numerical agreement is not scientific or mathematical proof; strong pipelines benefit from sequential causal debugging |
| SRC-ANTHROPIC-MULTI | [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Jeremy Hadfield et al. / Anthropic | 2025-06-13 | Official production retrospective; medium-high | Bounded breadth-first research, summary compression, citation agent | Internal evaluation and roughly 15x token usage; tightly coupled tasks are poor candidates |
| SRC-CLAUDE-MEMORY | [Claude Code memory](https://code.claude.com/docs/en/memory) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | CLAUDE.md versus auto-memory, session handoff | Memory is context rather than enforcement; machine-local auto-memory is not truth |
| SRC-CLAUDE-SUBAGENTS | [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | Isolated roles, tools, permissions, optional persistent memory | Features vary by version; parallel reports still consume main context |
| SRC-CLAUDE-SKILLS | [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands) and [built-in commands](https://code.claude.com/docs/en/commands) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | Project skills and compatible command entry points | Skills are prompted workflows, not deterministic gates; command availability varies |
| SRC-CLAUDE-HOOKS | [Hooks guide](https://code.claude.com/docs/en/hooks-guide) and [reference](https://code.claude.com/docs/en/hooks) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | Deterministic pre/post validation and protected writes | Prompt hooks remain model decisions; agent hooks are experimental; hooks do not replace OS sandboxing |
| SRC-CLAUDE-MCP | [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | Local/remote MCP adapter documentation and limits | Servers enlarge the trusted tool surface; secrets, permissions, and third-party terms remain separate concerns |
| SRC-CLAUDE-MODELS | [Configure Claude models and effort](https://code.claude.com/docs/en/model-config) and [CLI reference](https://code.claude.com/docs/en/cli-usage) | Anthropic | rolling, checked 2026-07-24 | Official documentation; high | Model/effort precedence and CLI adapter | Aliases drift, full IDs pin snapshots, effort support differs by model/plan/provider |
| SRC-LEAN-REF | [Lean reference: Validating a Lean Proof](https://lean-lang.org/doc/reference/latest/ValidatingProofs/) and [Axioms](https://lean-lang.org/doc/reference/latest/Axioms/) | Lean team | rolling, checked 2026-07-24 | Official language reference; high | Formalization gate, `#print axioms`, trusted-kernel boundary | Formal proof only proves the encoded statement under imported axioms; faithfulness still needs review |
| SRC-LEAN-REPO | [leanprover/lean4](https://github.com/leanprover/lean4) and [mathlib4](https://github.com/leanprover-community/mathlib4) | Lean team / mathlib community | rolling | Official repositories; Apache-2.0 | Pin toolchains and compile formal artifacts | Monthly releases and compatibility movement require lockfiles; not all mathematics is formalized |
| SRC-ARXIV | [arXiv API User's Manual](https://info.arxiv.org/help/api/user-manual.html) and [Terms](https://info.arxiv.org/help/api/tou.html) | arXiv / Cornell | rolling | Official API documentation; high | Search and version metadata | Rate limit across legacy interfaces; metadata CC0 does not make every e-print redistributable |
| SRC-CROSSREF | [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) and [access limits](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/) | Crossref | rolling | Official API documentation; high | DOI and deposited metadata verification | Deposits can be incomplete/wrong; abstracts and linked full text may retain copyright; cache and back off on 429 |
| SRC-OPENALEX | [OpenAlex authentication and pricing](https://developers.openalex.org/api-reference/authentication) | OurResearch | rolling | Official current API reference; high | Scholarly graph and metadata discovery | Freemium limits and pricing changed; old help pages conflict; read current response headers before automation |
| SRC-SEMANTIC | [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/graphs) and [current license](https://api.semanticscholar.org/license/) | Allen Institute for AI | rolling | Official API and license; high | Citation graph and paper metadata when permitted | Current terms are more restrictive than an older product-license page; keep disabled until terms are accepted |
| SRC-ZBMATH | [zbMATH Open tools and resources](https://zbmath.org/tools-and-resources/) and [terms](https://oai.zbmath.org/static/terms-and-conditions.html) | FIZ Karlsruhe | rolling / terms June 2021 | Official service pages; high | Mathematics-specific metadata and MSC | API is not the entire database; reasonable-rate limit is not numeric; license version wording differs across pages |
| SRC-MATHSCINET | [MathSciNet terms](https://mathscinet.ams.org/mathscinet/2006/mathscinet/help/mathscinet_terms_of_use.html?version=2) and [free tools](https://mathscinet.ams.org/mathscinet/info/docs/search-extras/free-tools) | American Mathematical Society | terms 2010-09 | Official terms; high | Manual subscriber verification and limited MR Lookup/MRef | Automated scripted search/download of the subscription database is prohibited; no general harvesting adapter is enabled |
| SRC-DOI | [DOI Handbook](https://www.doi.org/doi-handbook/html/) and [Crossref content negotiation](https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/) | DOI Foundation / Crossref | 2025 / rolling | Official standards/service documentation; high | Persistent resolution and registration-agency routing | A DOI proves identity/resolution, not metadata correctness, theorem entailment, access rights, or license |

## Conflicts and conservative resolutions

1. **Danus write-gate versus truth.**  The verifier is the sole software writer,
   but the paper reports verifier mistakes and reference contamination.  This
   project therefore calls `VERIFIED` a workflow status, not human peer review or
   formal certainty; release documents retain that disclaimer.
2. **Parallel versus sequential agents.**  The Anthropic sources agree once
   dependency topology is made explicit: independent, low-sharing work may run
   in parallel; strongly coupled pipelines stay sequential.  The router uses
   this criterion rather than agent count as a quality proxy.
3. **Rolling model names and effort levels.**  Public catalogs and aliases drift.
   The inventory records detection time/evidence and never turns
   `PUBLICLY_LISTED` into executable availability.  Current host metadata and
   successful local probes are stronger evidence than catalog pages.
4. **OpenAlex and Semantic Scholar terms changed.**  Current official API/terms
   pages take precedence; the corresponding adapters stay advisory or disabled
   until a user explicitly configures and accepts them.
5. **Lean release pages can briefly disagree.**  The local executable and pinned
   project toolchain are recorded; the word “latest” is never used as a build
   guarantee.

## Design consequences

- Truth is an append-preserving fact graph with explicit statuses and dependency
  closure; research notes are separate files.
- Only a cold-start independent verifier identity can promote a fact, and code
  checks role, authorship separation, dependencies, assumptions, and cycles.
- Revocation propagates to every transitive descendant and produces manuscript
  and experiment impact lists.
- Numerical artifacts require a command, environment, raw output, limitations,
  and sensitivity checks.  They remain numerical evidence.
- Provider adapters expose verified capabilities and hard failures; they do not
  pretend that an installed CLI, public model, or environment variable proves
  account access.
- Formalization is optional and must record toolchain, imports, axioms, `sorry`,
  `admit`, and build output.

