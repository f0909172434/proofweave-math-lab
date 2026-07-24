from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .io import load_json, save_json, stable_digest, utc_now


PASSIVE_ONLY = "No model inference or paid API request was made."


def _command_path(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _version(command: str | None, args: list[str] | None = None) -> dict[str, Any]:
    if not command:
        return {"installed": False, "path": None, "version": None, "evidence": "not found"}
    try:
        completed = subprocess.run(
            [command, *(args or ["--version"])],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        output = (completed.stdout or completed.stderr).strip().splitlines()
        return {
            "installed": completed.returncode == 0,
            "path": command,
            "version": output[0] if output else "UNKNOWN",
            "evidence": f"exit={completed.returncode}",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"installed": True, "path": command, "version": "UNKNOWN", "evidence": str(exc)}


def detect_tools() -> dict[str, Any]:
    return {
        "codex_cli": _version(_command_path("codex.cmd", "codex")),
        "claude_code": _version(_command_path("claude.cmd", "claude")),
        "python": _version(sys.executable),
        "node": _version(_command_path("node")),
        "git": _version(_command_path("git")),
        "lean": _version(_command_path("lean")),
        "lake": _version(_command_path("lake")),
        "pdflatex": _version(_command_path("pdflatex")),
        "xelatex": _version(_command_path("xelatex")),
        "latexmk": _version(_command_path("latexmk")),
        "pandoc": _version(_command_path("pandoc")),
    }


def credential_presence() -> dict[str, bool]:
    """Report names only; values are never returned or logged."""

    names = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "GOOGLE_API_KEY",
        "MATHLAB_LLM_GATEWAY_URL",
    )
    return {name: bool(os.environ.get(name)) for name in names}


def determine_mode(
    host: dict[str, Any],
    tools: dict[str, Any],
    credentials: dict[str, bool],
    *,
    allow_cli_subprocess_agents: bool = False,
    allow_api_routing: bool = False,
    allow_gateway_routing: bool = False,
) -> tuple[str, str]:
    if all(
        host.get(key, False)
        for key in ("native_subagents", "per_agent_model", "per_agent_reasoning_effort")
    ):
        return "MODE_A_NATIVE_MULTI_MODEL", "Host metadata verifies native per-agent model and effort controls."
    if allow_cli_subprocess_agents and any(
        tools.get(name, {}).get("installed") for name in ("codex_cli", "claude_code")
    ):
        return "MODE_B_CLI_SUBPROCESS_ROUTING", "An installed official CLI was explicitly enabled."
    if allow_api_routing and any(
        credentials.get(name) for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    ):
        return "MODE_C_API_ROUTING", "A provider credential name is present and API routing was enabled."
    if allow_gateway_routing and credentials.get("MATHLAB_LLM_GATEWAY_URL"):
        return "MODE_D_GATEWAY_ROUTING", "A gateway URL is configured and gateway routing was enabled."
    return "MODE_E_ADVISORY_ONLY", "No executable routing surface is both verified and explicitly enabled."


def _model_record(model: dict[str, Any], checked_at: str) -> dict[str, Any]:
    return {
        "provider": model.get("provider", "codex_desktop_native"),
        "model_id": model["model_id"],
        "display_name": model.get("display_name", model["model_id"]),
        "aliases": model.get("aliases", []),
        "model_family": model.get("model_family", model["model_id"]),
        "availability_status": model.get("availability_status", "VERIFIED_AVAILABLE"),
        "availability_evidence": model.get(
            "availability_evidence", "current host session capability metadata"
        ),
        "detection_method": model.get("detection_method", "HOST_CAPABILITY_METADATA"),
        "last_checked_at": checked_at,
        "account_verified": model.get("account_verified", True),
        "reasoning_support": bool(model.get("supported_reasoning_levels")),
        "supported_reasoning_levels": model.get("supported_reasoning_levels", []),
        "context_window": model.get("context_window"),
        "max_output_tokens": model.get("max_output_tokens"),
        "text_input": True,
        "image_input": model.get("image_input", True),
        "pdf_input": model.get("pdf_input", True),
        "structured_output": model.get("structured_output", True),
        "tool_calling": model.get("tool_calling", True),
        "web_search": model.get("web_search", True),
        "file_search": model.get("file_search", True),
        "code_execution": model.get("code_execution", True),
        "computer_use": model.get("computer_use", True),
        "MCP_support": model.get("MCP_support", True),
        "streaming": model.get("streaming", True),
        "snapshot_support": model.get("snapshot_support", False),
        "estimated_input_cost": model.get("estimated_input_cost"),
        "estimated_output_cost": model.get("estimated_output_cost"),
        "latency_class": model.get("latency_class", "UNKNOWN"),
        "rate_limit_information": "UNKNOWN",
        "deprecation_status": model.get("deprecation_status", "ACTIVE"),
        "provider_adapter": "host_native",
        "capability_tier": model.get("capability_tier", "FRONTIER"),
        "notes": model.get("notes", "Host-scoped availability; not a public API entitlement."),
    }


def detect_capabilities(root: Path, *, write: bool = True) -> dict[str, Any]:
    root = Path(root)
    checked_at = utc_now()
    host = load_json(root / "state" / "host_capabilities.json", default={}) or {}
    tools = detect_tools()
    credentials = credential_presence()
    policy = load_json(root / "config" / "runtime_policy.json", default={}) or {}
    mode, reason = determine_mode(
        host,
        tools,
        credentials,
        allow_cli_subprocess_agents=bool(policy.get("allow_cli_subprocess_agents", False)),
        allow_api_routing=bool(policy.get("allow_api_routing", False)),
        allow_gateway_routing=bool(policy.get("allow_gateway_routing", False)),
    )
    models = [_model_record(model, checked_at) for model in host.get("models", [])]
    inventory = {
        "inventory_version": stable_digest({"checked_at": checked_at, "models": models})[:16],
        "generated_at": checked_at,
        "execution_mode": mode,
        "execution_mode_reason": reason,
        "passive_probe": True,
        "paid_probe_performed": False,
        "models": models,
        "tools": tools,
        "credential_presence": credentials,
        "notes": [PASSIVE_ONLY, "Credential values were never read or stored."],
    }
    if write:
        save_json(root / "state" / "model_inventory.json", inventory)
        provider_status = {
            "checked_at": checked_at,
            "providers": {
                "codex_desktop_native": {
                    "status": "VERIFIED_AVAILABLE" if models else "UNKNOWN",
                    "mode": mode,
                },
                "codex_cli": {
                    "status": "INSTALLED_DISABLED" if tools["codex_cli"]["installed"] else "UNAVAILABLE"
                },
                "claude_code": {
                    "status": "INSTALLED_DISABLED" if tools["claude_code"]["installed"] else "UNAVAILABLE"
                },
                "openai_api": {
                    "status": "CONFIGURED_UNVERIFIED"
                    if credentials["OPENAI_API_KEY"]
                    else "DISABLED"
                },
                "anthropic_api": {
                    "status": "CONFIGURED_UNVERIFIED"
                    if credentials["ANTHROPIC_API_KEY"]
                    else "DISABLED"
                },
                "gateway": {
                    "status": "CONFIGURED_UNVERIFIED"
                    if credentials["MATHLAB_LLM_GATEWAY_URL"]
                    else "DISABLED"
                },
            },
            "paid_probe_performed": False,
        }
        save_json(root / "state" / "provider_status.json", provider_status)
    return inventory
