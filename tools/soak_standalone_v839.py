"""v8.3.9: bounded, isolated repeated-process SQLite soak; NEVER an always-on service.

Only deterministic synthetic offline jobs, no provider APIs, scheduler, secrets,
webhooks, production data or external side effects. GitHub CI runner/local disk
survives across test child-process exits, NOT across machine replacement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.standalone_parallel_v836 import run_parallel

PROFILES = ("cpu", "mixed", "waiting")


def soak(*, seconds: int = 10, jobs_per_wave: int = 12,
         per_process: int = 3) -> dict:
    if type(seconds) is not int or not 1 <= seconds <= 30:
        raise ValueError("INVALID_SOAK_DURATION")
    if type(jobs_per_wave) is not int or not 4 <= jobs_per_wave <= 32:
        raise ValueError("INVALID_WAVE_JOB_COUNT")
    if type(per_process) is not int or not 1 <= per_process <= 16:
        raise ValueError("INVALID_BATCH_LIMIT")
    with tempfile.TemporaryDirectory(prefix="v839-soak-") as root:
        db = str(Path(root) / "soak.sqlite3")
        queue = DurableLeaseQueue(db)
        started = time.perf_counter()
        deadline = started + seconds
        waves = total = max_workers = 0
        profile_totals = {p: 0 for p in PROFILES}
        # Intentionally start and stop fresh actual subprocesses each wave.
        while (time.perf_counter() < deadline or waves < 2) and waves < 500:
            profile = PROFILES[waves % len(PROFILES)]
            batch = [f"synthetic-v83-v839-soak-{waves}-{i}"
                     for i in range(jobs_per_wave)]
            for task in batch:
                queue.enqueue(task, "offline_check",
                              hashlib.sha256(task.encode("ascii")).hexdigest())
            current = 0
            while current < jobs_per_wave:
                result = run_parallel(db, processes="auto",
                                      per_process=per_process, profile=profile)
                if result["verdict"] not in {"PASS", "PARTIAL"} or (
                    result["dead"] or result["lease_conflicts"] or
                    result["child_failures"] or result["succeeded"] < 1
                ):
                    raise RuntimeError("SOAK_WORKER_UNVERIFIED")
                current += result["succeeded"]
                max_workers = max(max_workers, result["processes_started"])
                if current > jobs_per_wave:
                    raise RuntimeError("SOAK_DOUBLE_PROCESSING")
            total += current
            profile_totals[profile] += current
            waves += 1
            if queue.summary() != {"SUCCEEDED": total}:
                raise RuntimeError("SOAK_WAVE_READBACK_FAILED")
        elapsed = max(0.000001, time.perf_counter() - started)
        # Independent fresh read-only SQLite connection validates every job.
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
            count, distinct, bad_attempts, not_success = connection.execute(
                """SELECT COUNT(*), COUNT(DISTINCT task_id),
                   SUM(CASE WHEN attempt<>1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN state<>'SUCCEEDED' THEN 1 ELSE 0 END)
                   FROM jobs"""
            ).fetchone()
        if count != total or distinct != total or bad_attempts or not_success:
            raise RuntimeError("SOAK_PERSISTENCE_UNVERIFIED")
        return {
            "scope": "ISOLATED_FINITE_SYNTHETIC_SOAK_NOT_HOSTED",
            "status": "PASS", "seconds_requested": seconds,
            "elapsed_seconds": round(elapsed, 3), "waves": waves,
            "subprocess_batch_restarts": max(0, waves - 1),
            "total_jobs": total,
            "max_observed_processes": max_workers,
            "workload_profile_hints": profile_totals,
            "duplicate_or_retry_attempts": int(bad_attempts or 0),
            "persisted_successes": count,
            "neon_used": False, "network_used": False,
            "always_on_24h_verified": False,
            "machine_replacement_persistence_verified": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Finite offline repeated-process stress")
    parser.add_argument("--seconds", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    print("V839_SOAK_JSON=" + json.dumps(
        soak(seconds=args.seconds, jobs_per_wave=args.jobs), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
