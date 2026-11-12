"""Provider-free integration boundary for ten upstream AI projects.

Each adapter performs a *local, deterministic contract simulation* only. It does not
import or run vendor packages. No network, filesystem writes, model calls or credentials.
This is a staging gateway, never proof of operational vendor integrations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from safe_adoption import SafetyBlock, load_catalog, validate

SCHEMA = "OSS_TOP10_ADAPTER_DRY_RUN_V1"
PROTECTED = frozenset({"main", "d1", "site", "booking", "secrets", "production"})
NAME_MAX = 80
SECRET = re.compile(r"(?i)(sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_-]{12,}|(?<![a-z])(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=])")
ALL_IDS = (
    "langgraph", "activepieces", "openhands", "mem0", "langfuse",
    "agent-framework", "crewai", "letta", "openai-agents", "flowise",
)


def _safe_goal(goal: str) -> str:
    if not isinstance(goal, str) or not 1 <= len(goal) <= NAME_MAX:
        raise SafetyBlock("Goal must be a bounded nonempty string")
    if SECRET.search(goal) or any(ord(c) < 32 for c in goal):
        raise SafetyBlock("Potential credential or control character in goal")
    return goal


def _digest(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16]


def _langgraph(goal: str) -> dict:
    return {"checkpoint": "in_memory_only", "states": ["queued", "research", "verify", "done"], "transitions": 3}


def _activepieces(goal: str) -> dict:
    return {"trigger": "manual_dry_run", "steps": ["validate_input", "emit_mock_result"], "published": False}


def _openhands(goal: str) -> dict:
    return {"change_request": f"review:{_digest(goal)}", "shell_executed": False, "patch_applied": False}


def _mem0(goal: str) -> dict:
    return {"memory_proposal": _digest(goal), "scope": "volatile_local", "d1_written": False}


def _langfuse(goal: str) -> dict:
    return {"trace_id": f"offline-{_digest(goal)}", "status": "SIMULATED", "telemetry_exported": False}


def _agent_framework(goal: str) -> dict:
    return {"routing": ["research", "build", "verify"], "selected_runtime": False}


def _crewai(goal: str) -> dict:
    return {"crew": ["researcher", "builder", "verifier"], "model_agents_started": 0}


def _letta(goal: str) -> dict:
    return {"session_id": f"ephemeral-{_digest(goal)}", "persistence": "none", "remote_state_created": False}


def _openai_agents(goal: str) -> dict:
    return {"handoff": "research_to_verify", "tool_permissions": "none", "provider_calls": 0}


def _flowise(goal: str) -> dict:
    return {"nodes": ["input", "dry_run", "output"], "edges": [["input", "dry_run"], ["dry_run", "output"]], "engine_started": False}


_ADAPTERS = {
    "langgraph": _langgraph,
    "activepieces": _activepieces,
    "openhands": _openhands,
    "mem0": _mem0,
    "langfuse": _langfuse,
    "agent-framework": _agent_framework,
    "crewai": _crewai,
    "letta": _letta,
    "openai-agents": _openai_agents,
    "flowise": _flowise,
}


def simulate_all(catalog: dict, goal: str, *, mode: str = "dry_run") -> dict:
    """Exercise exactly ten offline adapters, excluding any live vendor runtime."""
    if mode != "dry_run":
        raise SafetyBlock("Live integrations, installation, deploy or writes are not authorized")
    goal = _safe_goal(goal)
    records = validate(catalog)
    indexed = {r["id"]: r for r in records}
    if set(indexed) != set(_ADAPTERS) or set(_ADAPTERS) != set(ALL_IDS):
        raise SafetyBlock("Ten-project adapter registry drift")
    results = []
    for project_id in ALL_IDS:
        record = indexed[project_id]
        if record["archived"] and project_id != "flowise":
            raise SafetyBlock("New archived project blocks simulated activation")
        artifact = _ADAPTERS[project_id](goal)
        results.append({
            "project": project_id,
            "upstream": record["repo"],
            "status": "EOL_VISUAL_REFERENCE_ONLY" if record["archived"] else "LOCAL_CONTRACT_EXERCISED",
            "vendor_runtime_imported": False,
            "artifact": artifact,
        })
    return {
        "schema": SCHEMA,
        "mode": mode,
        "goal_digest": _digest(goal),
        "adapter_count": len(results),
        "adapter_contracts_exercised": len(results),
        "vendor_runtime_integrations_verified": 0,
        "vendor_packages_installed": 0,
        "external_requests": 0,
        "production_writes": 0,
        "selection": {"orchestrator": "langgraph", "memory": "mem0", "observability": "langfuse", "automation": "activepieces"},
        "selection_is_live": False,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise all ten provider-free adapter contracts")
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("catalog.json"))
    parser.add_argument("--goal", default="Audit validated evidence without changing production")
    parser.add_argument("--mode", default="dry_run")
    args = parser.parse_args()
    print(json.dumps(simulate_all(load_catalog(args.catalog), args.goal, mode=args.mode), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
