"""Offline role routing for scheduled R16 checks; no remote or LLM calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from supervisor import run_once

ROLES = {
    "research": ("O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08", "O09", "O10"),
    "build": ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"),
    "verify": ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09", "G10"),
    "scheduled_audit": ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10"),
}
GOALS = {
    "research": ("research", "verify"),
    "build": ("research", "build", "verify"),
    "audit": ("scheduled_audit", "verify"),
    "verify": ("verify",),
}


def select_roles(goal: str):
    if goal not in GOALS:
        raise ValueError("unknown goal; fail closed")
    return GOALS[goal]


def verify_role_catalog(catalog_path: Path):
    """Reject missing, duplicated or changed role IDs before dispatch."""
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        raise ValueError("catalog must be a list")
    ids = [row["id"] for row in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate catalog role ID")
    missing = sorted({item for group in ROLES.values() for item in group} - set(ids))
    if missing:
        raise ValueError("missing catalog role IDs: " + ", ".join(missing))
    return True


def dispatch(goal: str, state_dir: Path, *, script=None):
    roles = select_roles(goal)
    verify_role_catalog(Path(__file__).resolve().parent / "catalog.json")
    # Offline rules are categorized, not independently invoked AI agents.
    receipt = run_once(state_dir, **({"script": script} if script else {}))
    return {
        "goal": goal,
        "selected_roles": list(roles),
        "selected_rule_ids": sorted({item for role in roles for item in ROLES[role]}),
        "status": receipt["status"],
        "kind": "OFFLINE_ROLE_ROUTING_NOT_NATIVE_SCHEDULED_TOOL_CALL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", choices=sorted(GOALS), default="audit")
    parser.add_argument("--state-dir", type=Path, default=Path(__file__).resolve().parent / ".supervisor_state")
    args = parser.parse_args()
    result = dispatch(args.goal, args.state_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
