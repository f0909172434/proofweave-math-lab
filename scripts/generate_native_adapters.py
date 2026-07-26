from __future__ import annotations

import json
from pathlib import Path


ROLES = [
    "orchestrator", "problem_formalizer", "literature_scout", "strategy_generator",
    "proof_worker", "counterexample_hunter", "toy_model_explorer", "asymptotics_auditor",
    "computation_experimenter", "theorem_verifier", "dependency_auditor", "reference_auditor",
    "formalization_agent", "paper_architect", "mathematical_writer", "paper_math_verifier",
    "numerical_reproducibility_auditor", "referee_agent", "revision_manager", "style_editor",
    "model_capability_scanner", "task_complexity_classifier", "model_router",
    "reasoning_effort_router", "model_benchmark_agent", "budget_manager", "routing_auditor",
    "provider_adapter_manager",
]

SKILLS = {
    "research-init": "workflows/00_project_intake.md",
    "literature-map": "workflows/02_literature_review.md",
    "idea-swarm": "workflows/03_idea_swarm.md",
    "prove": "workflows/04_proof_search.md",
    "disprove": "workflows/05_counterexample_search.md",
    "verify-claim": "workflows/06_fact_verification.md",
    "audit-asymptotics": "agents/asymptotics_auditor.md",
    "run-experiment": "workflows/07_computational_experiment.md",
    "write-paper": "workflows/10_paper_writing.md",
    "review-paper": "workflows/11_full_paper_review.md",
    "revise-paper": "workflows/12_revision_cycle.md",
    "release-check": "workflows/13_release_check.md",
    "status": "docs/operator_guide.md",
    "handoff": "workflows/14_session_handoff.md",
    "models": "workflows/15_model_detection.md",
    "model-doctor": "docs/model_detection_limits.md",
    "model-benchmark": "workflows/17_model_benchmarking.md",
    "route-task": "workflows/16_model_routing.md",
    "explain-route": "docs/model_routing_guide.md",
    "budget-status": "agents/budget_manager.md",
    "provider-status": "docs/provider_setup.md",
}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    codex_agents = root / ".codex" / "agents"
    claude_agents = root / ".claude" / "agents"
    for role in ROLES:
        canonical = f"agents/{role}.md"
        write(
            codex_agents / f"{role}.toml",
            f'''name = "{role}"\ndescription = "ProofWeave {role} adapter; canonical contract is {canonical}."\ndeveloper_instructions = """\nBefore acting, read {canonical} from the repository root in full and follow it together with its mandatory shared-contract references. Do not weaken, duplicate, or rewrite the canonical contracts.\n"""\n''',
        )
        tools = "Read, Grep, Glob, Bash" if role in {"theorem_verifier", "reference_auditor", "dependency_auditor"} else "Read, Grep, Glob, Bash, Edit, Write"
        write(
            claude_agents / f"{role}.md",
            f'''---\nname: {role}\ndescription: ProofWeave {role} adapter; canonical contract is {canonical}.\ntools: {tools}\n---\n\nBefore acting, read `{canonical}` in full and follow it together with its mandatory shared-contract references. Do not weaken, duplicate, or rewrite the canonical contracts.\n''',
        )
    for skill, target in SKILLS.items():
        body = f'''---\nname: {skill}\ndescription: Run the ProofWeave {skill} workflow using the canonical project artifact.\n---\n\nRead `{target}` in full, then follow it. Canonical role contracts remain in `agents/`; truth-layer changes must go through deterministic CLI gates. Do not perform paid calls, publish, push, upload, or expose credentials without explicit authorization.\n'''
        write(root / ".agents" / "skills" / skill / "SKILL.md", body)
        write(root / ".claude" / "skills" / skill / "SKILL.md", body)
    write(
        root / ".codex" / "config.toml",
        "[agents]\nenabled = true\nmax_concurrent_threads_per_session = 4\n",
    )
    hook_example = {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python scripts/validate_project.py --quick",
                        }
                    ]
                }
            ]
        },
        "_note": "Opt-in example. Copy to .claude/settings.local.json only after reviewing the current Claude Code hooks documentation.",
    }
    write(root / ".claude" / "settings.example.json", json.dumps(hook_example, indent=2) + "\n")
    print(json.dumps({"codex_agents": len(ROLES), "claude_agents": len(ROLES), "skills_per_host": len(SKILLS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
