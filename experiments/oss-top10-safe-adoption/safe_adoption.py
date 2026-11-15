"""Offline, fail-closed adoption planner. Does not install, import, or call upstream packages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "OSS_TOP10_SAFE_ADOPTION_V1"
EXPECTED_IDS = frozenset({
    "langgraph", "activepieces", "openhands", "mem0", "langfuse",
    "agent-framework", "crewai", "letta", "openai-agents", "flowise",
})
MODES = frozenset({"primary_candidate", "existing_reference", "sandbox_candidate", "alternative", "excluded"})
RESTRICTED_ACTIONS = frozenset({"install", "connect", "deploy", "enable", "write", "invoke", "merge", "schedule"})
EXPECTED_GUARDS = frozenset({
    "allow_install", "allow_external_api", "allow_paid_api", "allow_production_write",
    "allow_scheduled_task_change", "allow_flow_change", "allow_d1_write", "allow_main_change",
})


class SafetyBlock(ValueError):
    """An unsafe or unverifiable adoption proposal was rejected."""


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(catalog: dict) -> list[dict]:
    if catalog.get("schema") != SCHEMA:
        raise SafetyBlock("Unrecognized catalog schema")
    guard = catalog.get("guard_policy", {})
    if set(guard) != EXPECTED_GUARDS or any(value is not False for value in guard.values()):
        raise SafetyBlock("All write, installation, billing and provider guards must be explicitly false")
    projects = catalog.get("projects", [])
    if len(projects) != 10 or {x.get("id") for x in projects} != EXPECTED_IDS:
        raise SafetyBlock("Must enumerate exactly 10 unique official projects")
    chosen = set()
    for item in projects:
        if item.get("mode") not in MODES or not item.get("repo") or not item.get("license"):
            raise SafetyBlock(f"Invalid project metadata: {item.get('id')}")
        if item.get("archived") and item["mode"] != "excluded":
            raise SafetyBlock("Archived project cannot be selected")
        if item["mode"] == "primary_candidate":
            cap = item.get("capability")
            if cap in chosen:
                raise SafetyBlock(f"Conflicting primary integration: {cap}")
            chosen.add(cap)
    if next(x for x in projects if x["id"] == "flowise")["archived"] is not True:
        raise SafetyBlock("Known EOL fact removed without independent evidence")
    return projects


def create_plan(catalog: dict, action: str = "plan") -> dict:
    if action != "plan":
        raise SafetyBlock(f"Action '{action}' denied; planner is strictly offline/read-only")
    projects = validate(catalog)
    mapping = {
        "primary_candidate": "DESIGN_CANDIDATE",
        "existing_reference": "EXISTING_REFERENCE_UNVERIFIED",
        "sandbox_candidate": "SANDBOX_CANDIDATE",
        "alternative": "REVIEW_ONLY_CONFLICT_AVOIDANCE",
        "excluded": "BLOCKED_EOL",
    }
    return {
        "schema": "OSS_TOP10_GATED_PLAN_V1",
        "target": catalog.get("target_repository"),
        "source_main_sha": catalog.get("source_main_sha"),
        "reviewed_count": len(projects),
        "installed_upstream_packages": 0,
        "runtime_upstream_integrations_verified": 0,
        "external_ai_calls": 0,
        "production_writes": 0,
        "decision": [
            {"id": p["id"], "repo": p["repo"], "status": mapping[p["mode"]], "license": p["license"]}
            for p in projects
        ],
        "next_gate": "Per-component license, isolated trial, verified free quota, explicit operational approval",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("catalog.json"))
    parser.add_argument("--action", default="plan")
    args = parser.parse_args()
    print(json.dumps(create_plan(load_catalog(args.catalog), action=args.action), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
