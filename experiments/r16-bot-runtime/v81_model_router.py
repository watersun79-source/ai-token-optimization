#!/usr/bin/env python3
"""Fail-closed AI BOT v8.1 model selection plan.

Pure local routing. This module NEVER invokes an LLM, network, API, provider,
ChatGPT native automation or billing. A routing plan is not execution proof.
"""
from __future__ import annotations

import argparse
import json

MODEL_IDS = {
    "terra": "gpt-6.1-terra",
    "sol": "gpt-6.1-sol",
    "astra": "gpt-6-astra",
}
TASK_MODELS = {
    "routine": "terra",       # extraction, recurring categorization
    "screen": "terra",        # computer/visual work
    "scoped_fix": "terra",    # bounded code patch
    "engineering": "sol",    # sustained implementation / CI diagnosis
    "project": "sol",        # long-running coordinated work
    "deep_review": "astra", # high-complexity independent review
}
PROVIDER_CALLS = 0


def make_plan(task_kind: str, *, failed_checks: int = 0,
              material_risk: bool = False, available_models=None) -> dict:
    """Return a *recommendation* with explicit execution/availability gates.

    Unknown tasks, malformed failure counts and unknown model identifiers fail
    closed. No silent downgrade of quality on missing model availability.
    """
    if not isinstance(task_kind, str) or task_kind not in TASK_MODELS:
        raise ValueError("unknown task kind; fail closed")
    if type(failed_checks) is not int or failed_checks < 0:
        raise ValueError("failed_checks must be nonnegative integer")
    if type(material_risk) is not bool:
        raise ValueError("material_risk must be boolean")
    if available_models is not None:
        if not isinstance(available_models, (list, tuple, set, frozenset)):
            raise ValueError("available_models must be model-key collection or None")
        if any(type(value) is not str or value not in MODEL_IDS
               for value in available_models):
            raise ValueError("unknown available model key; fail closed")

    choice = TASK_MODELS[task_kind]
    reason = "TASK_CLASS"
    if material_risk or task_kind == "deep_review":
        choice = "astra"
        reason = "MATERIAL_RISK_OR_DEEP_REVIEW"
    elif failed_checks >= 2:
        choice = "sol" if choice == "terra" else "astra"
        reason = "REPEATED_VERIFICATION_FAILURE"

    if available_models is None:
        availability = "UNVERIFIED"
    elif choice in available_models:
        availability = "AVAILABLE_AS_DECLARED_NOT_AUTHENTICATED"
    else:
        availability = "NOT_AVAILABLE_AS_DECLARED"

    return {
        "task_kind": task_kind,
        "recommended_model": choice,
        "model_id": MODEL_IDS[choice],
        "selection_reason": reason,
        "model_availability": availability,
        "provider_calls": PROVIDER_CALLS,
        "status": "ROUTING_ONLY_NOT_EXECUTED",
        "runtime_model_identity": "UNVERIFIED",
        "native_automation_execution": "UNVERIFIED",
        "same_run_github_slack_provenance": "UNVERIFIED",
        "external_paid_api_autocall": False,
        "requires_separate_access_and_billing_approval": True,
        "production_changes": 0,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Offline model routing, no provider calls")
    p.add_argument("--task-kind", required=True, choices=sorted(TASK_MODELS))
    p.add_argument("--failed-checks", type=int, default=0)
    p.add_argument("--material-risk", action="store_true")
    p.add_argument("--available-model", action="append", choices=sorted(MODEL_IDS),
                   default=None, help="self-declared only; not authenticated")
    args = p.parse_args(argv)
    try:
        plan = make_plan(args.task_kind, failed_checks=args.failed_checks,
                         material_risk=args.material_risk,
                         available_models=args.available_model)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(plan, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
