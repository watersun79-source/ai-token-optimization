#!/usr/bin/env python3
"""Offline causal audit of Activepieces *self-reported* task checkpoints.

This validates *checkpoint timestamps and coverage*, NEVER provider-authenticated
ChatGPT scheduled runs. No network, credentials, provider calls or external writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

AUTOMATION_ID = "6acb017062a08191a4136238b78b313a"
SELF_REPORTED = "SELF_REPORTED_UNATTENDED_NOT_INDEPENDENTLY_PROVEN"
SLOT_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:00 Asia/Seoul$")
UTC_FORMAT = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.([0-9]{1,9}))?Z$")
KST = ZoneInfo("Asia/Seoul")
MAX_ROWS = 500
MAX_HOURS = 168


def parse_slot(value: Any) -> datetime | None:
    if not isinstance(value, str) or SLOT_FORMAT.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value[:-11], "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return None


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or UTC_FORMAT.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError:
        return None


def parse_utc_ns(value: Any) -> tuple[datetime, int] | None:
    """Preserve 7th–9th fractional digits that Python datetime truncates."""
    parsed = parse_utc(value)
    if parsed is None:
        return None
    match = UTC_FORMAT.fullmatch(value)
    fraction = (match.group(1) or "").ljust(9, "0")
    return parsed, int(fraction[6:])


def delay_seconds_ns(observed: tuple[datetime, int], slot: datetime) -> float:
    """Compute signed nanosecond delta with integer timedelta arithmetic."""
    at, sub_micro_ns = observed
    elapsed = at - slot.astimezone(timezone.utc)
    ns = ((elapsed.days * 86400 + elapsed.seconds) * 1_000_000_000
          + elapsed.microseconds * 1000 + sub_micro_ns)
    return round(ns / 1_000_000_000, 9)


def audit_checkpoints(rows: list[dict], first_slot: str, last_slot: str) -> dict:
    """Fail-closed audit of authenticated *table reads*, not ChatGPT native runs.

    A PASS here means only the order of a self-reported checkpoint is plausible.
    The caller must separately authenticate the Activepieces retrieval, and no
    caller-provided officialRunId can raise ChatGPT-native verification status.
    """
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("expected at most 500 checkpoint rows")
    first, last = parse_slot(first_slot), parse_slot(last_slot)
    if first is None or last is None or last < first or (last - first) >= timedelta(hours=MAX_HOURS):
        raise ValueError("invalid or excessive slot window")
    by_slot: dict[str, list[dict]] = {}
    rejected_rows = 0
    claimed_run_ids = 0
    self_reported_success_text = 0
    for entry in rows:
        if not isinstance(entry, dict):
            rejected_rows += 1
            continue
        cells = entry.get("cells", entry)
        if not isinstance(cells, dict):
            rejected_rows += 1
            continue
        slot_text = cells.get("scheduledSlotKst")
        slot = parse_slot(slot_text)
        if slot is None or not first <= slot <= last:
            rejected_rows += 1
            continue
        by_slot.setdefault(slot_text, []).append(cells)
        run_id = cells.get("officialRunId")
        if isinstance(run_id, str) and run_id.strip() and run_id != "미제공":
            claimed_run_ids += 1
        read_result = cells.get("readResult")
        if isinstance(read_result, str) and read_result.startswith("SUCCESS"):
            self_reported_success_text += 1
    checks = []
    for i in range(int((last - first) / timedelta(hours=1)) + 1):
        slot = first + timedelta(hours=i)
        label = slot.strftime("%Y-%m-%d %H:00 Asia/Seoul")
        matches = by_slot.get(label, [])
        if not matches:
            status, reason, delta = "UNVERIFIED", "NO_CHECKPOINT", None
        elif len(matches) > 1:
            status, reason, delta = "FAIL", "DUPLICATE_CHECKPOINTS", None
        else:
            cell = matches[0]
            at_ns = parse_utc_ns(cell.get("observedAtUtc"))
            at = at_ns[0] if at_ns is not None else None
            task_id = cell.get("automationId")
            level = cell.get("evidenceLevel")
            if task_id is not None and task_id != AUTOMATION_ID:
                status, reason, delta = "FAIL", "WRONG_AUTOMATION", None
            elif at is None:
                status, reason, delta = "FAIL", "INVALID_OBSERVED_TIME", None
            elif at_ns < (slot.astimezone(timezone.utc), 0):
                status, reason = "FAIL", "PRE_SLOT_OBSERVATION"
                delta = delay_seconds_ns(at_ns, slot)
            elif task_id is None:
                status, reason, delta = "UNVERIFIED", "TASK_ID_NOT_INCLUDED", None
            elif level != SELF_REPORTED:
                status, reason, delta = "UNVERIFIED", "SELF_REPORTED_ORIGIN_NOT_CONFIRMED", None
            else:
                status, reason = "PASS", "CHECKPOINT_CHRONOLOGY_ONLY"
                delta = delay_seconds_ns(at_ns, slot)
        checks.append({"slot": label, "checkpoint_status": status, "reason": reason,
                       "delay_seconds": delta, "native_execution_proven": False})
    totals = {s: sum(c["checkpoint_status"] == s for c in checks)
              for s in ("PASS", "FAIL", "UNVERIFIED")}
    return {
        "kind": "ACTIVEPIECES_SELF_REPORTED_CHECKPOINT_ORDER_AUDIT_NOT_NATIVE",
        "source_trust": "CALLER_MUST_ATTEST_CONNECTED_TABLE_READ",
        "native_unattended_success_verified": False,
        "official_native_run_id_verified": False,
        "native_run_success_count": None,
        "rows_checked": len(rows),
        "out_of_window_or_malformed_rows": rejected_rows,
        "claimed_run_id_fields_not_authenticated": claimed_run_ids,
        "self_reported_success_text_count_not_authenticated": self_reported_success_text,
        "slot_counts": totals,
        "slots": checks,
    }


def main() -> None:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Local self-reported ledger triage; no native proof")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--from-slot", required=True)
    parser.add_argument("--to-slot", required=True)
    a = parser.parse_args()
    obj = json.loads(a.input.read_text(encoding="utf8"))
    data = obj.get("records") if isinstance(obj, dict) else obj
    print(json.dumps(audit_checkpoints(data, a.from_slot, a.to_slot), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
