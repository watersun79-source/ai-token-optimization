#!/usr/bin/env python3
"""Optional 82+18 LOCAL audit profile; GitHub/offline evidence, never native proof.

The original 18 fail-closed native-source rules are NOT overwritten. The new
18 roles perform different, independently checkable OFFLINE GITHUB audits over
caller-provided run/job/log snapshots. This module makes no network/API calls.
A JSON snapshot is unsigned; PASS means input consistency, NOT a provider seal.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

PINNED_SHA = "a551e6ecc290f625432aba7ce2f7c23cc6117a30"
WORKFLOW = ".github/workflows/ai-r16-hourly.yml"
REPO = "watersun79-source/ai-token-optimization"
OLD_NATIVE_IDS = (
    "L06", "L07", "L08", "L09", "L10", "A07", "A08", "A09",
    "E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10",
)
ROLE_TITLES = (
    "예약 workflow 경로 검사", "schedule 트리거 검사", "공식 GitHub run ID·URL 검사",
    "운영 HEAD 동일성 검사", "GitHub run 성공 상태 검사", "UTC 생성 시각 검사",
    "예약 슬롯 지연 검사(추정)", "job·run ID 연계 검사", "job 성공 검사",
    "job 시작·종료 시각 검사", "필수 steps 완료 검사", "run·job 시간 인과성 검사",
    "pinned checkout 원시 로그 검사", "Python 22/22 검사", "Java 20/20 검사",
    "JavaScript 20/20 검사", "100개 로컬 규칙 상태 검사", "오프라인 원장과 native 미검증 구분",
)
NEW_IDS = tuple(f"V{i:02d}" for i in range(1, 19))
assert len(OLD_NATIVE_IDS) == len(set(OLD_NATIVE_IDS)) == 18
assert len(ROLE_TITLES) == 18
UTC_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not UTC_STAMP.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        return None


def positive(value: Any) -> bool:
    return type(value) is int and value > 0


def snapshot_object(value: Any) -> dict | None:
    return value if isinstance(value, dict) else None


def event_from_log(log: str | None, predicate) -> dict | None:
    """Parse one exact JSON object from a timestamp-prefixed Actions log line."""
    if log is None:
        return None
    observed = []
    for line in log.splitlines():
        match = re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,9})?Z (\{.*\})", line)
        if match is None:
            continue
        try:
            item = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict) and predicate(item):
            observed.append(item)
    # Multiple matching records are ambiguous, even if a first record looked valid.
    return observed[0] if len(observed) == 1 else None


def evaluate(snapshot: dict) -> dict:
    """Tri-state audit, no trusted ChatGPT-native attestation possible."""
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    run, job = snapshot_object(snapshot.get("run")), snapshot_object(snapshot.get("job"))
    log = snapshot.get("raw_job_log")
    if not isinstance(log, str) or not log.strip():
        log = None
    main_sha = snapshot.get("main_sha")
    inferred_slot = utc(snapshot.get("inferred_slot_utc"))
    created = utc(run.get("created_at")) if run else None
    started = utc(job.get("started_at")) if job else None
    finished = utc(job.get("completed_at")) if job else None

    measured = event_from_log(log, lambda d: d.get("source") == "local_measured_tests")
    rules = event_from_log(log, lambda d: d.get("mode") == "OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS")
    receipt = event_from_log(log, lambda d: d.get("kind") == "OFFLINE_BACKGROUND_LOOP_NOT_NATIVE_RESERVATION")
    results: list[dict] = []

    def check(index: int, observed: bool | None, detail: str):
        status = "UNVERIFIED" if observed is None else "PASS" if observed else "FAIL"
        results.append({"id": NEW_IDS[index - 1], "replaces": OLD_NATIVE_IDS[index - 1],
                        "name": ROLE_TITLES[index - 1], "status": status, "detail": detail,
                        "scope": "OFFLINE_GITHUB_INPUT_NOT_CHATGPT_NATIVE"})

    check(1, run.get("path") == WORKFLOW if run else None, "GitHub schedule workflow path")
    check(2, run.get("event") == "schedule" if run else None, "scheduled event, not push or dispatch")
    check(3, (positive(run.get("id")) and
              run.get("html_url") == f'https://github.com/{REPO}/actions/runs/{run["id"]}')
          if run else None, "canonical run ID and URL")
    check(4, bool(SHA.fullmatch(main_sha)) and run.get("head_sha") == main_sha
          if run and isinstance(main_sha, str) else None, "main SHA observed separately")
    check(5, run.get("status") == "completed" and run.get("conclusion") == "success"
          if run else None, "GitHub result; no ChatGPT status asserted")
    check(6, created is not None if run else None, "strict UTC created_at")
    # Only an inferred slot. GitHub run API does not supply an authenticated
    # 'scheduled_for', so this is deliberately never described as native time.
    check(7, (inferred_slot.minute == 15 and inferred_slot.second == 0 and
              created is not None and 0 <= (created - inferred_slot).total_seconds() <= 5400)
          if run and inferred_slot else None, "cron :15 inferred, grace <= 90 min")
    check(8, (positive(job.get("id")) and positive(job.get("run_id")) and
              job["run_id"] == run.get("id")) if job and run else None, "job belongs to run")
    check(9, job.get("status") == "completed" and job.get("conclusion") == "success"
          if job else None, "job completed successfully")
    check(10, (started is not None and finished is not None and
               0 <= (finished-started).total_seconds() <= 300)
          if job else None, "job duration 0..300 s")
    steps = job.get("steps") if job else None
    wanted = ("Fetch CI-verified R16 sources (pinned SHA)",
              "Install offline role wrappers and validate all 100 rules",
              "Verify receipt and never claim native ChatGPT automation proof")
    check(11, bool(steps) and isinstance(steps, list) and
          all(isinstance(s, dict) and s.get("conclusion") == "success" for s in steps) and
          all(any(s.get("name") == name for s in steps) for name in wanted)
          if steps is not None else None, "all listed steps pass, required steps present")
    check(12, (created is not None and started is not None and finished is not None
               and created <= started <= finished)
          if run and job else None, "time order created <= job start <= job end")
    # Only an emitted checkout trace counts, not an echo/command that merely
    # prints the pinned SHA or contains its literal text.
    checkout_line = re.compile(
        rf"(?m)^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}T[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}"
        rf"(?:\.[0-9]{{1,9}})?Z (?:\[command\]/usr/bin/)?git checkout --progress --force {PINNED_SHA}\s*$")
    ref_line = re.compile(
        rf"(?m)^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}T[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}"
        rf"(?:\.[0-9]{{1,9}})?Z +ref: {PINNED_SHA}\s*$")
    check(13, bool(checkout_line.search(log) and ref_line.search(log))
          if log is not None else None, "pinned SHA corroborated in raw checkout log")

    counts = measured.get("counts") if measured else None
    for index, lang, count in ((14, "python", 22), (15, "java", 20), (16, "js", 20)):
        obj = counts.get(lang) if isinstance(counts, dict) else None
        check(index, obj.get("passed") == count and obj.get("total") == count
              if isinstance(obj, dict) else None,
              f"{lang} tests {count}/{count} from raw CI log")
    stats = rules.get("statuses") if rules else None
    check(17, (type(rules.get("executed_rule_checks")) is int and
               rules["executed_rule_checks"] == 100 and
               set(stats).issubset({"PASS", "FAIL", "UNVERIFIED"}) and
               all(type(value) is int and value >= 0 for value in stats.values()) and
               stats.get("PASS") == 82 and stats.get("UNVERIFIED") == 18 and
               stats.get("FAIL", 0) == 0 and sum(stats.values()) == 100)
          if rules and isinstance(stats, dict) else None, "82 offline pass, 18 original native gates still unverified")
    check(18, (receipt.get("official_unattended_app_call_success") == "UNVERIFIED" and
               receipt.get("selected_outcome") == "UNVERIFIED" and
               receipt.get("kind") == "OFFLINE_BACKGROUND_LOOP_NOT_NATIVE_RESERVATION" and
               bool(re.search(r"(?m)^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED\s*$", log)))
          if receipt and log else None, "fail closed: never convert offline receipt to native success")
    assert len(results) == 18
    totals = {s: sum(row["status"] == s for row in results) for s in ("PASS", "FAIL", "UNVERIFIED")}
    return {
        "kind": "OPTIONAL_18_GITHUB_OFFLINE_SUBSTITUTES_NOT_NATIVE_EVIDENCE",
        "profile": "LEGACY_82_PLUS_GITHUB_OFFLINE_18",
        "role_total": 18,
        "original_native_evidence_gates_retained": list(OLD_NATIVE_IDS),
        "original_native_evidence_gate_status": "UNVERIFIED",
        "source_input_trust": "UNSIGNED_SNAPSHOT_VALIDATE_WITH_AUTHENTICATED_CONNECTOR",
        "native_chatgpt_same_run_proven": False,
        "external_model_calls": 0,
        "statuses": totals,
        "roles": results,
    }


def alternate_manifest(catalog: list[dict]) -> dict:
    """Build an alternative 100-role roster without editing catalog.json."""
    if not isinstance(catalog, list) or len(catalog) != 100:
        raise ValueError("expected precisely 100 source roles")
    ids = [x.get("id") for x in catalog if isinstance(x, dict)]
    if len(ids) != 100 or len(set(ids)) != 100 or not set(OLD_NATIVE_IDS).issubset(ids):
        raise ValueError("original catalog ID provenance mismatch")
    original82 = [{"id": x["id"], "name": x["name"], "category": x["category"],
                   "scope": "ORIGINAL_OFFLINE_SNAPSHOT_CHECK_NOT_PROVIDER_ATTESTED"}
                  for x in catalog if x["id"] not in OLD_NATIVE_IDS]
    substitutes = [{"id": NEW_IDS[i], "name": ROLE_TITLES[i], "replaces": old, "original_slot": old,
                    "scope": "GITHUB_OFFLINE_AUDIT_NOT_NATIVE"}
                   for i, old in enumerate(OLD_NATIVE_IDS)]
    roles = original82 + substitutes
    if len(roles) != 100 or len(set(x["id"] for x in roles)) != 100:
        raise ValueError("alternate 100-role catalog duplicate")
    return {"kind": "OPTIONAL_ISOLATED_82_PLUS_18_ROSTER", "total_roles": 100,
            "untouched_native_gates": list(OLD_NATIVE_IDS), "roles": roles}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Local verifier: no network access, no native attestation")
    p.add_argument("--snapshot", type=Path, help="JSON run/job/raw_job_log from read-only GitHub retrieval")
    p.add_argument("--catalog", type=Path, help="Optional original 100-role catalog for roster only")
    a = p.parse_args()
    result = evaluate(json.loads(a.snapshot.read_text(encoding="utf8")) if a.snapshot else {})
    if a.catalog:
        manifest = alternate_manifest(json.loads(a.catalog.read_text(encoding="utf8")))
        result["optional_100_roster_count"] = manifest["total_roles"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
