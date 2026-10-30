"""Isolated v8.3.8 throughput benchmark: identical local synthetic SQLite jobs.

No internet, API credentials, paid models or real user jobs. Results are
machine/runner specific: CPU quotas, process startup and file contention vary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
import time
from pathlib import Path

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.standalone_parallel_v836 import run_parallel

DEFAULT_CANDIDATES = (1, 2, 4, 8, 16)


def benchmark(*, jobs: int = 48, repeats: int = 2,
              candidates: tuple[int, ...] = DEFAULT_CANDIDATES,
              per_process: int = 4) -> dict:
    if type(jobs) is not int or not 8 <= jobs <= 128:
        raise ValueError("INVALID_JOB_COUNT")
    if type(repeats) is not int or not 1 <= repeats <= 3:
        raise ValueError("INVALID_REPEAT_COUNT")
    if type(per_process) is not int or not 1 <= per_process <= 16:
        raise ValueError("INVALID_BATCH_LIMIT")
    if not candidates or len(candidates) > 8 or any(
        type(p) is not int or p < 1 or p > 256 for p in candidates
    ):
        raise ValueError("INVALID_CANDIDATES")
    records = []
    for wanted in candidates:
        measurements = []
        observed = []
        for trial in range(repeats):
            with tempfile.TemporaryDirectory(prefix="v838-bench-") as folder:
                db = str(Path(folder) / "isolated.sqlite3")
                queue = DurableLeaseQueue(db)
                for k in range(jobs):
                    task = f"synthetic-v83-v838-bench-{k}"
                    queue.enqueue(task, "offline_check", hashlib.sha256(
                        task.encode("ascii")).hexdigest())
                start = time.perf_counter()
                total = 0
                round_count = 0
                while total < jobs:
                    result = run_parallel(db, processes=wanted, per_process=per_process)
                    if result["verdict"] not in {"PASS", "PARTIAL"} or result["dead"] or \
                       result["child_failures"] or result["lease_conflicts"] or not result["succeeded"]:
                        raise RuntimeError("BENCHMARK_NOT_VERIFIED")
                    total += result["succeeded"]
                    observed.append(result["processes_started"])
                    round_count += 1
                    if round_count > jobs:
                        raise RuntimeError("BENCHMARK_STALLED")
                elapsed = time.perf_counter() - start
                if queue.summary() != {"SUCCEEDED": jobs}:
                    raise RuntimeError("BENCHMARK_READBACK_FAILED")
                measurements.append(round(elapsed, 4))
        median = statistics.median(measurements)
        records.append({
            "requested": wanted,
            "max_observed_processes": max(observed),
            "jobs": jobs,
            "repeats": repeats,
            "seconds_trials": measurements,
            "seconds_median": round(median, 4),
            "jobs_per_second": round(jobs / median, 2),
            "status": "PASS",
        })
    best = min(records, key=lambda x: x["seconds_median"])
    return {
        "scope": "LOCAL_SYNTHETIC_SINGLE_RUNNER_ONLY",
        "result": "PASS",
        "method": "full_queue_drain_same_synthetic_jobs",
        "best_requested": best["requested"],
        "best_max_observed_processes": best["max_observed_processes"],
        "comparisons": records,
        "not_proven": ["production AI task speedup", "24h hosting",
                       "host-replacement SQLite persistence", "native unattended"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=48)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    print("V838_PERFORMANCE_JSON=" + json.dumps(benchmark(jobs=args.jobs, repeats=args.repeats),
                                                sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
