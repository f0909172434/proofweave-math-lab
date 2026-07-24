from __future__ import annotations

from typing import Any


ABSTRACT_LEVELS = ["NONE", "LOW", "MEDIUM", "HIGH", "VERY_HIGH", "MAXIMUM"]
NATIVE_ALIASES = {
    "none": "NONE",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "xhigh": "VERY_HIGH",
    "very_high": "VERY_HIGH",
    "max": "MAXIMUM",
    "maximum": "MAXIMUM",
    "ultra": "MAXIMUM",
}


def map_reasoning(
    requested: str,
    supported_native_levels: list[str] | None,
    *,
    host_can_control: bool = True,
    prompt_loop_control: bool = True,
) -> dict[str, Any]:
    abstract = requested.upper()
    if abstract not in ABSTRACT_LEVELS:
        raise ValueError(f"Unknown reasoning profile: {requested}")
    if not host_can_control:
        return {
            "requested_reasoning_profile": abstract,
            "effective_reasoning_setting": "UNKNOWN",
            "reasoning_control_method": "HOST_UNSUPPORTED",
            "degraded": True,
        }
    supported = supported_native_levels or []
    normalized: list[tuple[str, str]] = []
    for native in supported:
        key = NATIVE_ALIASES.get(native.lower())
        if key:
            normalized.append((native, key))
    if normalized:
        requested_rank = ABSTRACT_LEVELS.index(abstract)
        native, mapped = min(
            normalized,
            key=lambda item: (
                abs(ABSTRACT_LEVELS.index(item[1]) - requested_rank),
                ABSTRACT_LEVELS.index(item[1]) > requested_rank,
            ),
        )
        return {
            "requested_reasoning_profile": abstract,
            "effective_reasoning_setting": native,
            "reasoning_control_method": "NATIVE",
            "degraded": mapped != abstract,
        }
    return {
        "requested_reasoning_profile": abstract,
        "effective_reasoning_setting": abstract if prompt_loop_control else "UNKNOWN",
        "reasoning_control_method": "PROMPT_OR_LOOP_BASED" if prompt_loop_control else "HOST_UNSUPPORTED",
        "degraded": True,
    }

