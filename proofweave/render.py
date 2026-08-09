from __future__ import annotations

import re
from typing import Any

TACTIC_PROOFS = {
    "ring": "After polynomial normalization, both sides are identical.",
    "ring_nf": "Normalizing the polynomial expressions proves the identity.",
    "norm_num": "Direct numerical normalization proves the claim.",
    "linarith": "The conclusion follows from the stated linear relations.",
    "nlinarith": "Polynomial arithmetic from the stated hypotheses proves the conclusion.",
    "positivity": "Positivity normalization proves the required sign.",
    "exact": "The result is exactly the cited previously certified lemma.",
}


def _banner(alignment: str, proof_status: str) -> str:
    lines = [f"> **Proof status:** `{proof_status}`  ", f"> **Alignment:** `{alignment}`"]
    if alignment != "CONFIRMED":
        lines.append(
            "> Lean certification, when present, applies only to the formal target; equivalence with the human statement is not confirmed."
        )
    if proof_status != "CERTIFIED":
        lines.append("> This output contains uncertified or failed deductive obligations; it is not a certified proof.")
    return "\n".join(lines)


def render_paper(
    parsed: dict[str, Any],
    distilled: dict[str, Any],
    result: dict[str, Any],
    alignment: str,
) -> str:
    assumptions = "\n".join(f"- {item}" for item in parsed["assumptions"])
    quantifiers = "\n".join(f"- {item}" for item in parsed["quantifiers"]) or "- none stated"
    if result["fast_path"]:
        tactic = parsed["top_certificate"].get("tactic")
        proof = TACTIC_PROOFS.get(tactic, "The fixed certificate establishes the formal target.")
    else:
        proof = "\n\n".join(
            f"{index}. **{node['id']}** ({node['role']}): {node['text']}"
            for index, node in enumerate(distilled["nodes"], 1)
        )
    return (
        f"# {parsed['title']}\n\n"
        f"{_banner(alignment, result['proof_status'])}\n\n"
        f"## Statement\n\n{parsed['statement']}\n\n"
        f"## Quantifiers\n\n{quantifiers}\n\n"
        f"## Assumptions\n\n{assumptions}\n\n"
        f"## Proof\n\n{proof}\n"
    )


def _mermaid_id(identifier: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", identifier)


def _label(node: dict[str, Any]) -> str:
    text = " ".join(node["text"].split())
    if len(text) > 72:
        text = text[:69] + "..."
    return f"{node['id']} [{node['role']}] {text}".replace('"', "'")


def render_concept_map(
    parsed: dict[str, Any],
    distilled: dict[str, Any],
    result: dict[str, Any],
    alignment: str,
) -> str:
    nodes = distilled["nodes"]
    diagram = ["```mermaid", "flowchart TD"]
    if result["fast_path"]:
        diagram.append('  claim["Whole claim: single certificate obligation"]')
    else:
        for node in nodes:
            diagram.append(f'  {_mermaid_id(node["id"])}["{_label(node)}"]')
        known = {node["id"] for node in nodes}
        for node in nodes:
            for dependency in node["depends_on"]:
                if dependency in known:
                    diagram.append(f"  {_mermaid_id(dependency)} --> {_mermaid_id(node['id'])}")
    diagram.append("```")
    spine = "\n".join(f"- `{node['id']}`: {node['text']}" for node in nodes)
    trace = "\n".join(
        f"- `{key}` → {', '.join(f'`{value}`' for value in values)}"
        for key, values in distilled.get("presentation_to_certificate", {}).items()
    )
    return (
        f"# Proof spine: {parsed['title']}\n\n"
        f"{_banner(alignment, result['proof_status'])}\n\n"
        + "\n".join(diagram)
        + f"\n\n## Spine\n\n{spine or '- Whole claim certified directly.'}\n\n"
        f"## Presentation-to-certificate trace\n\n{trace or '- `claim` → `claim`'}\n"
    )
