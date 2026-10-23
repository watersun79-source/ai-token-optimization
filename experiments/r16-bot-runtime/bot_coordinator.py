"""Offline role routing for scheduled R16 checks; no remote or LLM calls."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from supervisor import run_once
from runner import validate, ROOT as RUNTIME_ROOT

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


def evaluate_selected_rules(goal: str, *, catalog=None, evidence=None):
    """Execute only selected rule IDs with the existing offline validator.

    PASS means snapshot values matched, not real provider authentication.
    """
    roles = select_roles(goal)
    if catalog is None:
        catalog = json.loads((RUNTIME_ROOT / "catalog.json").read_text(encoding="utf-8"))
    if evidence is None:
        evidence = json.loads((RUNTIME_ROOT / "evidence.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, list) or not isinstance(evidence, dict):
        raise ValueError("catalog/evidence must be list/object")
    ids = [row["id"] for row in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate catalog role ID")
    index = {row["id"]: row for row in catalog}
    selected_ids = [rule_id for role in roles for rule_id in ROLES[role]]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("duplicate selected rule ID")
    if any(rule_id not in index for rule_id in selected_ids):
        raise ValueError("selected rule ID missing from catalog")
    results = [validate(index[rule_id], evidence) for rule_id in selected_ids]
    if any(item.get("id") != selected_ids[i] or
           item.get("status") not in ("PASS", "FAIL", "UNVERIFIED", "ERROR")
           for i, item in enumerate(results)):
        raise ValueError("invalid rule result")
    statuses = Counter(item["status"] for item in results)
    outcome = ("FAIL" if statuses["FAIL"] or statuses["ERROR"]
               else "UNVERIFIED" if statuses["UNVERIFIED"] else "PASS")
    return {
        "selected_roles": list(roles),
        "selected_rule_ids": selected_ids,
        "executed_selected_rule_checks": len(results),
        "selected_statuses": dict(statuses),
        "selected_outcome": outcome,
        "selected_result_statuses": [
            {"id": row["id"], "status": row["status"]} for row in results
        ],
        "selected_evidence_scope": "OFFLINE_SNAPSHOT_NOT_PROVIDER_AUTHENTICATED",
    }


def dispatch(goal: str, state_dir: Path, *, script=None):
    roles = select_roles(goal)
    verify_role_catalog(Path(__file__).resolve().parent / "catalog.json")
    # First validate the whole local runtime/integrity snapshot, then evaluate
    # exactly the selected subset. These are not independent LLM model calls.
    receipt = run_once(state_dir, **({"script": script} if script else {}))
    response = {
        "goal": goal,
        "selected_roles": list(roles),
        "status": receipt["status"],
        "kind": "OFFLINE_ROLE_ROUTING_NOT_NATIVE_SCHEDULED_TOOL_CALL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "official_unattended_app_call_success": "UNVERIFIED",
    }
    if receipt["status"] != "PASS":
        response.update({
            "executed_selected_rule_checks": 0,
            "selected_outcome": "UNVERIFIED",
            "selected_statuses": {},
        })
        return response
    try:
        selected = evaluate_selected_rules(goal)
        response.update(selected)
        if selected["selected_outcome"] == "FAIL":
            response["status"] = "ERROR"
    except (OSError, ValueError, TypeError, KeyError) as exc:
        response["status"] = "ERROR"
        response["selected_outcome"] = "UNVERIFIED"
        response["executed_selected_rule_checks"] = 0
        response["selected_statuses"] = {}
        response["error_type"] = type(exc).__name__
    return response


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
