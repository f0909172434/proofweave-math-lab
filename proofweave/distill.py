from __future__ import annotations

from typing import Any


def distill(proof_ir: dict[str, Any], certificate: dict[str, Any]) -> dict[str, Any]:
    """Create a conservative presentation view without changing obligations."""

    nodes = proof_ir["nodes"]
    results = certificate.get("results", {})
    references = {node["id"]: 0 for node in nodes}
    for node in nodes:
        for dependency in node["depends_on"]:
            references[dependency] = references.get(dependency, 0) + 1
        if node["alias_of"]:
            references[node["alias_of"]] = references.get(node["alias_of"], 0) + 1
    folded_aliases = {
        node["id"]: node["alias_of"]
        for node in nodes
        if node["role"] == "alias" and references.get(node["id"], 0) <= 1
    }

    def visible(identifier: str) -> str:
        seen: set[str] = set()
        while identifier in folded_aliases and identifier not in seen:
            seen.add(identifier)
            identifier = folded_aliases[identifier]
        return identifier

    presentation: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    mapping: dict[str, list[str]] = {}
    for node in nodes:
        if node["id"] in folded_aliases:
            target = visible(node["id"])
            mapping.setdefault(target, []).append(node["id"])
            continue
        text = node["text"]
        if node["role"] == "computational" and results.get(node["id"]) == "PASSED":
            target = (node.get("certificate") or {}).get("target", "the stated computation")
            text = f"A certified computation establishes `{target}`."
        elif node["role"] == "computational" and results.get(node["id"]) != "PASSED":
            text = f"[Uncertified computation retained] {text}"
        dependencies = []
        for dependency in node["depends_on"]:
            projected = visible(dependency)
            if projected != node["id"] and projected not in dependencies:
                dependencies.append(projected)
        item = {
            "id": node["id"],
            "role": node["role"],
            "text": text,
            "depends_on": dependencies,
            "certificate_nodes": [node["id"]],
        }
        mapping.setdefault(node["id"], []).insert(0, node["id"])
        item["certificate_nodes"] = mapping[node["id"]]
        presentation.append(item)
        by_id[node["id"]] = item
    for presentation_id, certificate_ids in mapping.items():
        if presentation_id in by_id:
            by_id[presentation_id]["certificate_nodes"] = list(dict.fromkeys(certificate_ids))
    return {
        "nodes": presentation,
        "presentation_to_certificate": {
            node["id"]: node["certificate_nodes"] for node in presentation
        },
    }
