"""Fail-closed read-only evidence reconciler for ChatGPT native task snapshots.

AI BOT v8.5.8 isolated candidate. This is not a scheduler/clock repair, an
autonomous listener or proof that any native task called a remote app.
"""
from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Mapping

VERSION = "8.5.14-isolated-native-result-chronology-bound"
_STATUSES = frozenset({"completed", "no_update", "in_progress", "failed"})


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("INVALID_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if parsed.tzinfo is None:
        raise ValueError("NAIVE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def reconcile_native_snapshot(task: Mapping[str, object]) -> dict[str, object]:
    """Compare only the SAME officially reported run and result identifiers.

    A task's last_run and latest_result are not necessarily the same run.
    Return evidence metadata only; never persist the free-form result text.
    """
    if not isinstance(task, Mapping) or not isinstance(task.get("id"), str) or not task["id"]:
        raise ValueError("INVALID_TASK_ID")
    details = task.get("run_details")
    if not isinstance(details, Mapping):
        return {
            "schema": VERSION, "task_id": task["id"], "verdict": "RUN_UNVERIFIED",
            "result_link": "UNVERIFIED", "timing": "UNVERIFIED",
            "native_call_ledger": "UNVERIFIED",
            "scheduler_root_cause": "UNVERIFIED",
        }
    run = details.get("last_run")
    result = details.get("latest_result")
    if run is None:
        return {
            "schema": VERSION, "task_id": task["id"], "verdict": "RUN_UNVERIFIED",
            "result_link": "UNVERIFIED", "timing": "UNVERIFIED",
            "native_call_ledger": "UNVERIFIED",
            "scheduler_root_cause": "UNVERIFIED",
        }
    if not isinstance(run, Mapping) or not isinstance(run.get("id"), str) or not run["id"]:
        raise ValueError("INVALID_RUN_ID")
    status = run.get("recorded_status")
    if status not in _STATUSES:
        raise ValueError("INVALID_RECORDED_STATUS")
    scheduled = _instant(run.get("scheduled_for"))
    started = _instant(run.get("started_at"))
    ended = _instant(run["completed_at"]) if run.get("completed_at") is not None else None
    if ended is not None and ended < started:
        raise ValueError("INVALID_CHRONOLOGY")
    if status in ("completed", "no_update", "failed") and ended is None:
        raise ValueError("MISSING_COMPLETION")
    if status == "in_progress" and ended is not None:
        raise ValueError("IN_PROGRESS_WITH_COMPLETION")
    timing = "STARTED_BEFORE_SCHEDULED_FOR" if started < scheduled else "STARTED_AT_OR_AFTER_SCHEDULED_FOR"
    linked = "NO_RESULT"
    if result is not None:
        if not isinstance(result, Mapping):
            raise ValueError("INVALID_RESULT")
        required = ("run_id", "scheduled_for", "completed_at", "created_at", "requires_user_action", "is_failure_message")
        if not all(k in result for k in required):
            raise ValueError("INVALID_RESULT")
        # Official result metadata includes scheduled_for; always verify its match.
        # Missing/invalid action flags must not be interpreted as success.
        if not isinstance(result.get("requires_user_action"), bool) or not isinstance(result.get("is_failure_message"), bool):
            raise ValueError("INVALID_RESULT_FLAGS")
        result_scheduled = _instant(result["scheduled_for"])
        result_created = _instant(result["created_at"])
        result_end = _instant(result["completed_at"]) if result["completed_at"] is not None else None
        if (
            result.get("run_id") != run["id"]
            or result_scheduled != scheduled
            or result_end != ended
            # Only link result metadata created during the official run.
            # Earlier or later timestamps are not same-run proof, even when
            # the run ID and scheduled/completed values happen to match.
            or result_created < started
            or (ended is not None and result_created > ended)
        ):
            linked = "DIFFERENT_RUN_RESULT"
        elif result.get("is_failure_message") is True:
            linked = "SAME_RUN_FAILURE_MESSAGE"
        elif result.get("requires_user_action") is True:
            linked = "SAME_RUN_ACTION_REQUIRED"
        else:
            linked = "SAME_RUN_RESULT_METADATA"
    if status == "no_update":
        verdict = "RECORDED_NO_UPDATE_NOT_WORK_SUCCESS"
    elif status == "failed":
        verdict = "RECORDED_FAILED"
    elif status == "in_progress":
        verdict = "RECORDED_IN_PROGRESS"
    elif linked == "SAME_RUN_RESULT_METADATA":
        verdict = "RECORDED_COMPLETED_SAME_RUN_RESULT"
    else:
        verdict = "RECORDED_COMPLETED_RESULT_UNVERIFIED"
    return {
        "schema": VERSION,
        "task_id": task["id"], "run_id": run["id"],
        "recorded_status": status,
        "verdict": verdict, "result_link": linked, "timing": timing,
        "native_call_ledger": "UNVERIFIED",
        "scheduler_root_cause": "UNVERIFIED",
    }
