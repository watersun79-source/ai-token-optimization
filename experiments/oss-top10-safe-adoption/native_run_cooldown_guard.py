"""PR #30-compatible, standalone read-only boundary for native-run and cooldown evidence.

Adapts the two non-overlapping checks from the provided evolving_ai_guard v0.1.
Does not import vendor SDKs, call APIs, change GitHub, or write to D1/Sites.
Any automated retry or write remains prohibited; no operational authorization is issued.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HEADING = re.compile(
    r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*"
    r"(\d{1,2})시(?:\s*(\d{1,2})분)?"
)
DENIALS = frozenset({"COOLDOWN", "UPSTREAM_BACKOFF", "HTTP_401", "HTTP_403", "GITHUB_HTTP_403", "HTTP_404", "HTTP_429", "PERMISSION_DENIED"})


def _instant(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp missing")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def _title_matches(title: object, when: datetime) -> bool | None:
    if not isinstance(title, str):
        return None
    # First line only; text mentioning the scheduled date later is not proof of a matching heading.
    first_line = title.splitlines()[0][:200] if title else ""
    # Do not treat a date mentioned in a warning/status sentence as the report heading.
    heading = first_line.strip()
    heading = re.sub(r"^진화하는 AI\s*[·:]\s*", "", heading)
    match = HEADING.match(heading)
    if match is None:
        return None
    year, month, day, ampm, hour, minute = match.groups()
    h = int(hour)
    if not 1 <= h <= 12:
        return False
    hh = h % 12 + (12 if ampm == "오후" else 0)
    return ((int(year), int(month), int(day), hh) ==
            (when.year, when.month, when.day, when.hour) and
            (minute is None or int(minute) == when.minute))


def check_native(last_run: object, latest_result: object) -> dict:
    """Correlate by authoritative run/scheduled-for and time, not report wording alone."""
    codes: list[str] = []
    if not isinstance(last_run, dict) or not isinstance(latest_result, dict):
        return {"status": "UNVERIFIED", "finding_codes": ["MISSING_NATIVE_SOURCE"]}
    run_id, result_id = last_run.get("id"), latest_result.get("run_id")
    id_equal = bool(isinstance(run_id, str) and run_id.strip() and
                    isinstance(result_id, str) and result_id.strip() and run_id == result_id)
    if not id_equal:
        codes.append("RUN_RESULT_ID_MISMATCH")
    try:
        scheduled = _instant(last_run.get("scheduled_for"))
        result_scheduled = _instant(latest_result.get("scheduled_for"))
        started = _instant(last_run.get("started_at"))
        created = _instant(latest_result.get("created_at"))
        completed = _instant(last_run.get("completed_at"))
    except (ValueError, OverflowError, TypeError):
        return {"status": "UNVERIFIED", "id_equal": id_equal,
                "finding_codes": sorted(set(codes + ["MISSING_OR_INVALID_TIMESTAMPS"]))}
    schedule_equal = scheduled == result_scheduled
    time_order = started <= created <= completed
    local = scheduled.astimezone(KST)
    title_equal = _title_matches(latest_result.get("content_text"), local)
    if not schedule_equal:
        codes.append("SCHEDULED_FOR_MISMATCH")
    if not time_order:
        codes.append("RESULT_TIME_ORDER")
    if title_equal is False:
        codes.append("KST_TITLE_MISMATCH")
    if title_equal is None:
        codes.append("TITLE_NOT_VERIFIABLE")
    recorded_status = last_run.get("recorded_status")
    if recorded_status != "completed":
        codes.append("RUN_NOT_COMPLETED")
    hard_failure = any(c in codes for c in (
        "RUN_RESULT_ID_MISMATCH", "SCHEDULED_FOR_MISMATCH", "RESULT_TIME_ORDER", "KST_TITLE_MISMATCH"))
    status = "FAIL" if hard_failure else ("UNVERIFIED" if codes else "PASS")
    return {"status": status, "scheduled_kst": local.isoformat(),
            "id_equal": id_equal, "scheduled_equal": schedule_equal,
            "time_order": time_order, "title_equal": title_equal,
            "start_offset_seconds": round((started - scheduled).total_seconds(), 3),
            "finding_codes": sorted(set(codes))}


def check_cycle(cycle: object) -> dict:
    """A successful MCP transport receipt NEVER authorizes a retry, write, or success claim."""
    if not isinstance(cycle, dict):
        return {"status": "UNVERIFIED", "reason": "MISSING_CYCLE", "receipt_pass": False,
                "allow_retry": False, "allow_write": False}
    debug = cycle.get("debug") if isinstance(cycle.get("debug"), dict) else {}
    fix = cycle.get("fix") if isinstance(cycle.get("fix"), dict) else {}
    update = cycle.get("update") if isinstance(cycle.get("update"), dict) else {}
    receipt = cycle.get("mcp_receipt") if isinstance(cycle.get("mcp_receipt"), dict) else {}
    raw_reason = debug.get("reason")
    reason = raw_reason.strip() if isinstance(raw_reason, str) and raw_reason.strip() else "UNKNOWN"
    reason_code = re.split(r"[\s:]", reason, maxsplit=1)[0]
    op_status = cycle.get("status")
    stage_names = ("debug", "analysis", "fix", "update", "verify")
    stage_statuses = [cycle[name]["status"] for name in stage_names
                      if isinstance(cycle.get(name), dict) and "status" in cycle[name]]
    stage_unverified = (any(name in cycle and not isinstance(cycle[name], dict)
                            for name in stage_names) or
                        any(name in cycle and isinstance(cycle[name], dict) and
                            "status" not in cycle[name]
                            for name in stage_names) or
                        any(status not in ("PASS", "SKIP", "NO_UPDATE")
                            for status in stage_statuses))
    denied = (op_status in ("BLOCKED", "FAIL") or reason_code in DENIALS or
              re.fullmatch(r"(?:GITHUB_)?HTTP_[45]\d{2}", reason_code) is not None or
              any(status in ("BLOCKED", "FAIL") for status in stage_statuses))
    # An outcome of NO_UPDATE is not evidence of a successful repair.
    if denied:
        verdict = "BLOCKED"
    elif op_status == "NO_UPDATE" and reason == "SAME_HEAD" and not stage_unverified:
        verdict = "NO_UPDATE"
    else:
        verdict = "UNVERIFIED"  # PASS requires separate source/write/readback evidence.
    return {"status": verdict, "reason": reason,
            "operation_status": op_status or "UNVERIFIED",
            "debug_status": debug.get("status", "UNVERIFIED"),
            "fix_status": fix.get("status", "UNVERIFIED"),
            "update_status": update.get("status", "UNVERIFIED"),
            "receipt_pass": receipt.get("status") == "PASS",
            "allow_retry": False, "allow_write": False}


def audit(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("payload must be mapping")
    native = check_native(payload.get("last_run"), payload.get("latest_result"))
    cycle = check_cycle(payload.get("evolution_cycle"))
    overall = ("FAIL" if native["status"] == "FAIL" else
               "BLOCKED" if cycle["status"] == "BLOCKED" else
               "UNVERIFIED" if native["status"] == "UNVERIFIED" else
               cycle["status"])
    return {"schema": "PR30_NATIVE_RUN_COOLDOWN_READONLY_V1", "native": native,
            "cycle": cycle, "external_mutations": 0, "overall": overall}
