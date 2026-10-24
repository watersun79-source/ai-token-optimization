#!/usr/bin/env python3
"""Isolated v8.1 speed planner. NO network, provider APIs, billing or scheduler writes.
Caches only successful local offline results within THIS process; never native proof.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import statistics
import time

import v81_split_bench as adapter

ROOT = Path(__file__).resolve().parent
GOOD = {"PASS": 20}
ALL_GOOD = {"PASS": 100}


def fingerprint(catalog, evidence, code_sha: str) -> str:
    """Bind source HEAD and exact inputs. A digest is not a provider signature."""
    if not isinstance(code_sha, str) or len(code_sha) != 40 or any(c not in "0123456789abcdef" for c in code_sha):
        raise ValueError("40-character lowercase source SHA required")
    raw = json.dumps([code_sha, catalog, evidence], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def plan_ci(current_sha: str, verified_previous: dict | None) -> str:
    """Advisory only. Caller MUST independently authenticate previous GitHub CI.
    A fabricated status string alone is never accepted as a native task receipt.
    """
    if not isinstance(current_sha, str) or len(current_sha) != 40 or any(c not in "0123456789abcdef" for c in current_sha):
        raise ValueError("invalid current SHA")
    p = verified_previous if isinstance(verified_previous, dict) else {}
    if (p.get("source") == "GITHUB_API_INDEPENDENTLY_CHECKED"
            and p.get("head_sha") == current_sha and p.get("status") == "completed"
            and p.get("conclusion") == "success" and p.get("changed_inputs") is False):
        return "REUSE_ONLY_AFTER_INDEPENDENT_READBACK"
    return "RUN_FAST_AUDIT_THEN_FULL_REGRESSION_ON_CHANGED_INPUTS"


class AdaptiveOfflineRunner:
    """Fast audit first. Cache only results actually computed by this instance."""
    def __init__(self):
        self._cache = {}

    def run(self, catalog, evidence, head_sha: str):
        key = fingerprint(catalog, evidence, head_sha)
        if key in self._cache:
            return {"mode": "REUSED_LOCAL_PASS", "input_sha256": key,
                    "fast_checks": 0, "full_checks": 0,
                    "native_chatgpt_verified": False, "provider_call_count": 0}
        quick = adapter.execute(catalog, evidence, "audit")
        if quick["selected_count"] != 20 or quick["statuses"] != GOOD:
            raise ValueError("fail-closed: quick audit did not pass")
        full = adapter.execute(catalog, evidence, "all")
        if full["selected_count"] != 100 or full["statuses"] != ALL_GOOD:
            raise ValueError("fail-closed: full regression did not pass")
        self._cache[key] = True
        return {"mode": "FAST_THEN_FULL_LOCAL", "input_sha256": key,
                "fast_checks": 20, "full_checks": 100,
                "native_chatgpt_verified": False, "provider_call_count": 0}


def batch_read(requests, reader, max_workers=4):
    """Deduplicate exact read-only keys and overlap independent lookups.
    Reader is caller supplied; not a credentialed connector or network client.
    """
    if not isinstance(requests, list) or not 1 <= max_workers <= 4:
        raise ValueError("invalid batch")
    uniq = list(dict.fromkeys(requests))
    if not all(isinstance(k, tuple) and len(k) == 2 and all(isinstance(x, str) and x for x in k) for k in uniq):
        raise ValueError("only nonempty (tool, locator) read keys supported")
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        replies = list(pool.map(lambda k: reader(*k), uniq))
    return {"results": dict(zip(uniq, replies)), "requested": len(requests),
            "unique": len(uniq), "skipped_duplicates": len(requests)-len(uniq),
            "native_provider_authenticity": "UNVERIFIED"}


def compact_report(previous: dict, current: dict) -> dict:
    """Suppress unchanged PASS text, NEVER suppress fresh failures/unknowns."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise ValueError("status snapshots must be dictionaries")
    delta = {k: v for k, v in current.items()
             if previous.get(k) != v or v in ("FAIL", "ERROR", "UNVERIFIED")}
    return {"changed": delta, "changed_count": len(delta),
            "unattended_native_run": "UNVERIFIED"}


def bench(repeats=35):
    if not 5 <= repeats <= 150:
        raise ValueError("repeats out of bounds")
    catalog = json.loads((ROOT/"catalog.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT/"evidence.json").read_text(encoding="utf-8"))
    sha = "a"*40
    baseline, cached = [], []
    runner = AdaptiveOfflineRunner()
    first = runner.run(catalog, evidence, sha)
    assert first["fast_checks"] == 20 and first["full_checks"] == 100
    for _ in range(repeats):
        t = time.perf_counter_ns()
        out = adapter.execute(catalog, evidence, "all")
        assert out["statuses"] == ALL_GOOD
        baseline.append((time.perf_counter_ns()-t)/1e6)
        t = time.perf_counter_ns()
        reused = runner.run(catalog, evidence, sha)
        assert reused["mode"] == "REUSED_LOCAL_PASS"
        cached.append((time.perf_counter_ns()-t)/1e6)
    requests=[("GitHub","head"),("GitHub","head"),("Slack","thread"),
              ("GitHub","ci"),("Slack","thread"),("GitHub","file")]
    def mock_read(tool,locator):
        time.sleep(0.006)  # synthetic I/O delay; NOT real app latency
        return tool+"/"+locator
    serial_ms, parallel_ms=[], []
    for _ in range(8):
        t=time.perf_counter_ns()
        serial=[mock_read(*p) for p in requests]
        serial_ms.append((time.perf_counter_ns()-t)/1e6)
        t=time.perf_counter_ns()
        batched=batch_read(requests,mock_read)
        assert [batched["results"][p] for p in requests] == serial
        parallel_ms.append((time.perf_counter_ns()-t)/1e6)
    result={"kind":"ISOLATED_OFFLINE_SPEED_PROOF_NOT_NATIVE_SCHEDULER",
            "samples_local_rule_eval":repeats,
            "full_100_median_ms":round(statistics.median(baseline),4),
            "unchanged_sha_reuse_median_ms":round(statistics.median(cached),4),
            "local_reuse_ratio":round(statistics.median(baseline)/statistics.median(cached),2),
            "mock_io_samples":8,
            "mock_serial_median_ms":round(statistics.median(serial_ms),3),
            "mock_parallel_dedup_median_ms":round(statistics.median(parallel_ms),3),
            "mock_io_only":True,"unique_queries":4,"requested_queries":6,
            "native_chatgpt_same_run_proven":False,"paid_model_calls":0}
    print("R16_V81_SPEED="+json.dumps(result,sort_keys=True))
    return result


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--repeats",type=int,default=35)
    args=p.parse_args()
    bench(args.repeats)
