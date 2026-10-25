#!/usr/bin/env python3
"""AI BOT v8.1 isolated local swarm: 10 groups, 4-thread cap, serial oracle.

This runs offline rule checks, NOT independent LLMs or ChatGPT native tasks.
No network, subprocess, model APIs, credentials or operational changes.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path

import runner
import v81_split_bench as reference

ROOT = Path(__file__).resolve().parent
MAX_LOCAL_WORKERS = 4
MODES = ("audit", "all")


def _snapshot(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return json.loads(raw), raw


def _plan(catalog, mode, max_workers):
    if mode not in MODES:
        raise ValueError("expected offline audit or all")
    if type(max_workers) is not int or not 1 <= max_workers <= MAX_LOCAL_WORKERS:
        raise ValueError("local thread cap must be 1..4")
    if (not isinstance(catalog, list) or len(catalog) != 100
            or not all(isinstance(x, dict) and isinstance(x.get("id"), str)
                       for x in catalog)
            or {x["id"] for x in catalog} != reference.IDS):
        raise ValueError("complete 100-ID local catalogue required")
    groups = {prefix: [] for prefix in sorted(reference.GOALS[mode])}
    for role in catalog:
        if role["id"][0] in groups:
            groups[role["id"][0]].append(role)
    if any(len(v) != 10 for v in groups.values()):
        raise ValueError("each group needs ten roles")
    return [(p, sorted(v, key=lambda x: x["id"])) for p, v in groups.items()]


def _check(role, evidence, fixture):
    name = role["id"]
    if name not in reference.REPLACEMENTS:
        return runner.validate(role, evidence)
    try:
        passed = reference.CHECKS[name](fixture)
        status = "PASS" if passed else "FAIL"
    except (KeyError, ValueError, TypeError, AssertionError, AttributeError,
            OverflowError, RecursionError):
        status = "UNVERIFIED"
    return {
        "id": name, "category": role["category"],
        "name": reference.ORIGINAL_REPLACEMENT_NAMES[name],
        "scope": "LOCAL_FIXTURE_ONLY",
        "source": "SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE",
        "status": status,
        "detail": (
            "offline synthetic fixture rule passed; never authenticates real scheduling"
            if status == "PASS" else "offline synthetic fixture rule failed"
            if status == "FAIL" else
            "fixture missing/malformed; cannot run local check"
        ),
    }


def _category(group, evidence, fixture):
    _, roles = group
    return [_check(role, evidence, fixture) for role in roles]


def collaborate(catalog, evidence, mode="audit", max_workers=4, fixture=None):
    """Coordinator -> concurrently executed local groups -> serial verifier.

    The serial oracle is a second code path; it is NOT platform attestation.
    No worker exception is retried or echoed into potentially public logs.
    """
    if not isinstance(evidence, dict) or (fixture is not None and not isinstance(fixture, dict)):
        raise ValueError("offline evidence and fixture must be objects")
    payload, raw = _snapshot([catalog, evidence,
                              reference.sample_fixture() if fixture is None else fixture])
    catalog, evidence, fixture = payload
    groups = _plan(catalog, mode, max_workers)
    cap = min(max_workers, len(groups))
    digest = hashlib.sha256(raw).hexdigest()
    try:
        with ThreadPoolExecutor(max_workers=cap) as pool:
            shards = list(pool.map(lambda group: _category(group, evidence, fixture), groups))
        actual = sorted((record for shard in shards for record in shard), key=lambda x: x["id"])
        serial = reference.execute(catalog, evidence, mode, fixture)
    except Exception:
        return {
            "kind": "ISOLATED_OFFLINE_SWARM_NOT_NATIVE", "status": "BLOCKED",
            "reason": "LOCAL_WORKER_OR_ORACLE_ERROR", "input_sha256": digest,
            "selected_roles": len(groups) * 10, "group_count": len(groups),
            "effective_worker_cap": cap, "external_model_calls": 0,
            "native_chatgpt_run_verified": False, "production_changes": 0,
        }
    match = (len(actual) == serial["selected_count"]
             and actual == serial["details"])
    counts = dict(sorted(Counter(x["status"] for x in actual).items()))
    if not match:
        status, reason = "BLOCKED", "INDEPENDENT_ORACLE_MISMATCH"
    else:
        status = ("FAIL" if counts.get("FAIL") else
                  "UNVERIFIED" if counts.get("UNVERIFIED") else "PASS")
        reason = ("OFFLINE_RULES_ONLY" if status == "PASS"
                  else "LOCAL_ROLE_EVIDENCE_NOT_ALL_PASS")
    return {
        "kind": "ISOLATED_OFFLINE_SWARM_NOT_NATIVE", "status": status,
        "reason": reason, "mode": mode, "input_sha256": digest,
        "category_groups": [prefix for prefix, _ in groups],
        "selected_roles": len(actual), "group_count": len(groups),
        "effective_worker_cap": cap, "parallel_backend": "LOCAL_THREAD_POOL",
        "independent_serial_oracle_match": match, "status_counts": counts,
        "replacements_fixture_only": sum(x["id"] in reference.REPLACEMENTS for x in actual),
        "failed_or_unknown_roles": sorted(x["id"] for x in actual if x["status"] != "PASS"),
        "external_model_calls": 0, "external_provider_calls": 0,
        "native_chatgpt_run_verified": False,
        "same_run_github_slack_proven": False,
        "original_v81_source_deployed": False,
        "production_changes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description="v8.1 isolated offline role swarm")
    parser.add_argument("--mode", choices=MODES, default="audit")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    try:
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
        evidence = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))
        report = collaborate(catalog, evidence, args.mode, args.workers)
    except (OSError, ValueError, TypeError):
        report = {"kind": "ISOLATED_OFFLINE_SWARM_NOT_NATIVE",
                  "status": "BLOCKED", "reason": "BAD_INPUT_OR_FILE",
                  "external_model_calls": 0,
                  "native_chatgpt_run_verified": False, "production_changes": 0}
    print("R16_V81_SWARM=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
