from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def fact(fact_id: str, *, status: str = "PROPOSED", dependencies: list[str] | None = None, created_by: str = "worker") -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "title": fact_id,
        "statement": f"Statement {fact_id}",
        "normalized_statement": f"statement-{fact_id}",
        "kind": "lemma",
        "assumptions": ["explicitly no extra assumptions"],
        "quantifiers": ["for every admissible input"],
        "mathematical_domain": "test",
        "proof": "A complete test proof packet.",
        "dependencies": dependencies or [],
        "source_dependencies": [],
        "created_by": created_by,
        "status": status,
    }


def accept_report(
    fact_id: str,
    verifier: str = "verifier",
    *,
    dependencies: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "verification_id": f"verify-{fact_id}",
        "fact_id": fact_id,
        "outcome": "ACCEPT",
        "verifier": verifier,
        "verifier_role": "theorem_verifier",
        "cold_start": True,
        "dependencies_checked": dependencies or [],
        "sources_checked": sources or [],
        "checklist": [{"item": "all steps", "result": "PASS", "note": "checked"}],
        "created_at": "2026-07-24T00:00:00Z",
    }


def model(
    model_id: str,
    *,
    status: str = "VERIFIED_AVAILABLE",
    tier: str = "ADVANCED",
    provider: str = "host",
    family: str | None = None,
    tools: bool = True,
    context: int | None = None,
    deprecated: bool = False,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model_id": model_id,
        "display_name": model_id,
        "aliases": [],
        "model_family": family or model_id,
        "availability_status": status,
        "availability_evidence": "test",
        "detection_method": "test",
        "last_checked_at": "2026-07-24T00:00:00Z",
        "account_verified": status == "VERIFIED_AVAILABLE",
        "reasoning_support": True,
        "supported_reasoning_levels": ["low", "medium", "high", "xhigh", "max"],
        "context_window": context,
        "max_output_tokens": None,
        "text_input": True,
        "image_input": tools,
        "pdf_input": tools,
        "structured_output": tools,
        "tool_calling": tools,
        "web_search": tools,
        "file_search": tools,
        "code_execution": tools,
        "computer_use": tools,
        "MCP_support": tools,
        "streaming": True,
        "snapshot_support": False,
        "estimated_input_cost": None,
        "estimated_output_cost": None,
        "latency_class": "LOW",
        "rate_limit_information": "UNKNOWN",
        "deprecation_status": "DEPRECATED" if deprecated else "ACTIVE",
        "provider_adapter": "test",
        "capability_tier": tier,
        "notes": "test model",
    }


def inventory(*models: dict[str, Any]) -> dict[str, Any]:
    return {"inventory_version": "test-v1", "models": list(models)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
