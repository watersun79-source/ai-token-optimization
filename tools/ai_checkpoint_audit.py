#!/usr/bin/env python3
"""Offline integrity checks for an Activepieces scheduled-run evidence export.

This checks syntax and chronology, NOT authenticity of platform logs or tool calls.
No network, authentication, paid services, or mutation of upstream records.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

SLOT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):00 Asia/Seoul$")
SHA_RE = re.compile(r"^[a-fA-F0-9]{40}$")
SLACK_RE = re.compile(r"^\d{10}\.\d{6}$")
SELF_REPORTED = "SELF_REPORTED_UNATTENDED_NOT_INDEPENDENTLY_PROVEN"
MAX_FILE_BYTES = 1024 * 1024


def _iso_timestamp(value):
    """Return UTC datetime if value is timezone-aware, otherwise None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo else None


def _slot_start(value):
    if not isinstance(value, str):
        return None
    match = SLOT_RE.fullmatch(value)
    if not match:
        return None
    day, hour = match.groups()
    try:
        local = datetime.fromisoformat(f"{day}T{hour}:00:00").replace(
            tzinfo=timezone(timedelta(hours=9)))
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


def check(payload):
    """Validate recorded checkpoint timing without claiming independent run proof."""
    entries = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return {"status": "CHECKPOINT_ANOMALY", "total": 0,
                "errors": [{"issue": "records_list_missing"}], "rows": [],
                "official_run_proven": False}
    if not entries:
        return {"status": "CHECKPOINT_ANOMALY", "total": 0,
                "errors": [{"issue": "no_checkpoints"}], "rows": [],
                "official_run_proven": False}
    errors = []
    summaries = []
    seen = set()

    for index, record in enumerate(entries):
        item = record if isinstance(record, dict) else {}
        cells = item.get("cells") if isinstance(item.get("cells"), dict) else {}
        rid = str(item.get("id") or f"item-{index}")
        problems = []
        slot = cells.get("scheduledSlotKst")
        automation = cells.get("automationId")
        start = _slot_start(slot)
        observed = _iso_timestamp(cells.get("observedAtUtc"))
        offset_sec = None
        if not isinstance(automation, str) or not automation.strip():
            problems.append("automation_id_missing")
        if start is None:
            problems.append("invalid_or_unknown_slot")
        if observed is None:
            problems.append("invalid_or_missing_utc_observation")
        if start is not None and observed is not None:
            offset_sec = round((observed - start).total_seconds(), 3)
            if offset_sec < 0:
                problems.append("observation_precedes_declared_slot")
            elif offset_sec >= 3600:
                problems.append("observation_outside_declared_slot_hour")
        if isinstance(automation, str) and automation.strip() and start is not None:
            key = (automation, slot)
            if key in seen:
                problems.append("duplicate_automation_slot")
            seen.add(key)
        for field in ("githubIndexSha", "githubProtocolSha", "githubReportSha"):
            val = cells.get(field)
            if val not in (None, "") and (not isinstance(val, str) or not SHA_RE.fullmatch(val)):
                problems.append(f"{field}_invalid")
        for field in ("slackParentTs", "slackLatestMessageTs"):
            val = cells.get(field)
            if val not in (None, "") and (not isinstance(val, str) or not SLACK_RE.fullmatch(val)):
                problems.append(f"{field}_invalid")
        if cells.get("evidenceLevel") != SELF_REPORTED:
            problems.append("unsupported_evidence_level")
        # The checkpoint is self-authored: an "officialRunId" value alone
        # is not authenticated platform run evidence. Fail closed when an
        # export asserts such an ID without an independent platform log.
        # Even a self-declared officialLogOrigin cannot authenticate it.
        claimed_run_id = cells.get("officialRunId")
        if claimed_run_id not in (None, "", "미제공"):
            problems.append("unverified_official_run_id_claim")
        if str(cells.get("readResult", "")).startswith("SUCCESS"):
            required = ("githubIndexSha", "githubProtocolSha", "githubReportSha", "slackLatestMessageTs")
            if any(not cells.get(field) for field in required):
                problems.append("claimed_success_missing_source_fingerprint")
        errors.extend({"record_id": rid, "issue": e} for e in problems)
        summaries.append({"record_id": rid, "slot": slot,
                          "observation_offset_seconds": offset_sec,
                          "issues": problems})

    return {"status": "CHECKPOINT_ANOMALY" if errors else "CHECKPOINTS_CONSISTENT_NOT_INDEPENDENTLY_PROVEN",
            "total": len(entries), "errors": errors, "rows": summaries,
            "official_run_proven": False,
            "note": "Source values and UUIDs in self-reported records do not authenticate platform run logs."}


def main():
    parser = argparse.ArgumentParser(description="Offline Activepieces checkpoint timing/schema audit")
    parser.add_argument("records", type=Path, help="JSON export containing a records array with cells")
    args = parser.parse_args()
    if args.records.stat().st_size > MAX_FILE_BYTES:
        parser.error("JSON export exceeds 1 MiB")
    outcome = check(json.loads(args.records.read_text(encoding="utf-8")))
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    if outcome["status"] == "CHECKPOINT_ANOMALY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
