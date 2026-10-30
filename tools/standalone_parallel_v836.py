"""v8.3.9 workload-aware, resource-bounded SQLite process runner; no hosting.

Only v8.3.3's synthetic offline handler can be invoked. The durable SQLite
file must live on the same persistent local disk for all child processes.
This is *not* a Render Free persistence or 24-hour automation solution.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import math
import time
from pathlib import Path
import subprocess
import sys

from tools.durable_queue_v831 import DurableLeaseQueue

VERSION = "8.3.9"
MAX_PROCESSES = 256  # Architectural hard bound; resource quota is normally lower.
MAX_PER_PROCESS = 16
MEMORY_PER_CHILD_MIB = 96
MEMORY_RESERVE_MIB = 256


def _read_cgroup_number(path: str) -> int | None:
    try:
        raw = Path(path).read_text(encoding="ascii").strip()
        if raw == "max":
            return None
        num = int(raw)
        return num if num > 0 else None
    except (OSError, ValueError):
        return None


def _cpu_capacity() -> int:
    cpus = max(1, os.cpu_count() or 1)
    if hasattr(os, "sched_getaffinity"):
        try:
            cpus = min(cpus, len(os.sched_getaffinity(0)))
        except (OSError, ValueError):
            pass
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text(
            encoding="ascii").split()[:2]
        if quota != "max":
            cpus = min(cpus, max(1, math.ceil(int(quota) / int(period))))
    except (OSError, ValueError, ZeroDivisionError):
        pass
    return max(1, cpus)


def _memory_capacity() -> int:
    """Estimate available (not merely total) RAM under cgroup v2."""
    limit = _read_cgroup_number("/sys/fs/cgroup/memory.max")
    if limit is not None:
        used = _read_cgroup_number("/sys/fs/cgroup/memory.current")
        # No usage evidence must fail small, not treat a quota as free RAM.
        if used is None:
            return 1
        available = max(0, limit - used)
    else:
        try:
            info = Path("/proc/meminfo").read_text(encoding="ascii")
            line = next(row for row in info.splitlines()
                        if row.startswith("MemAvailable:"))
            available = int(line.split()[1]) * 1024
        except (OSError, ValueError, StopIteration, IndexError):
            return 1
    mib = available // (1024 * 1024)
    return max(1, (mib - MEMORY_RESERVE_MIB) // MEMORY_PER_CHILD_MIB)


PROFILES = {"cpu": 1, "mixed": 2, "waiting": 4}


def _checked_profile(profile: str) -> str:
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("INVALID_WORKLOAD_PROFILE")
    return profile


def runtime_process_ceiling(profile: str = "mixed") -> int:
    """CPU / mixed / waiting are *hints*; always respect free RAM and 256 cap."""
    return max(1, min(MAX_PROCESSES, _cpu_capacity() * PROFILES[_checked_profile(profile)],
                      _memory_capacity()))


def choose_processes(requested: int | str, backlog: int, per_process: int,
                     *, resource_cap: int | None = None,
                     profile: str = "mixed") -> int:
    """Deterministic hardware/memory/backlog limit, not a performance guarantee."""
    _checked_profile(profile)
    _bounded_int(backlog, 0, 10**9, "INVALID_BACKLOG")
    _bounded_int(per_process, 1, MAX_PER_PROCESS, "INVALID_BATCH_LIMIT")
    if requested != "auto":
        _bounded_int(requested, 1, MAX_PROCESSES, "INVALID_PROCESS_COUNT")
    cap = runtime_process_ceiling(profile) if resource_cap is None else _bounded_int(
        resource_cap, 1, MAX_PROCESSES, "INVALID_RESOURCE_LIMIT")
    useful = max(1, math.ceil(backlog / per_process))
    return min(cap, useful, cap if requested == "auto" else requested)
ROOT = str(Path(__file__).resolve().parent.parent)


def _bounded_int(value: int, low: int, high: int, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(code)
    return value


def _run_child(path: str, index: int, limit: int) -> dict:
    command = [sys.executable, "-m", "tools.isolated_worker_v833",
               "--db", path, "--worker-id", f"standalone-v837-{index}",
               "--limit", str(limit), "--concurrency", "1"]
    try:
        child = subprocess.run(command, cwd=ROOT, capture_output=True,
                               text=True, check=False, timeout=30)
        if child.returncode != 0 or len(child.stdout) > 8192:
            return {"ok": False, "reason": "CHILD_EXIT_OR_OVERSIZE"}
        report = json.loads(child.stdout)
        values = [report.get(key) for key in ("claimed", "succeeded", "dead", "lease_conflicts")]
        if report.get("scope") != "LOCAL_SYNTHETIC_ONLY" or any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values
        ) or values[0] > limit or sum(values[1:]) != values[0]:
            return {"ok": False, "reason": "CHILD_REPORT_INVALID"}
        recovered = report.get("recovered")
        if not isinstance(recovered, dict) or any(
            type(recovered.get(key)) is not int or recovered[key] < 0
            for key in ("requeued", "dead")
        ):
            return {"ok": False, "reason": "RECOVERY_REPORT_INVALID"}
        return {"ok": True, "claimed": values[0], "succeeded": values[1],
                "dead": values[2], "lease_conflicts": values[3],
                "recovered_requeued": recovered["requeued"],
                "recovered_dead": recovered["dead"]}
    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError, json.JSONDecodeError):
        # Never include stderr, payloads or exception strings in the public report.
        return {"ok": False, "reason": "CHILD_UNVERIFIED"}


def run_parallel(database_path: str, *, processes: int | str = "auto",
                 per_process: int = 4, profile: str = "mixed") -> dict:
    """One finite batch; adaptive process count is an upper bound, not a target.

    SQLite serializes its writes. Increasing processes is not evidence of
    increasing throughput; use the separate isolated benchmark to measure.
    """
    _checked_profile(profile)
    if processes != "auto":
        _bounded_int(processes, 1, MAX_PROCESSES, "INVALID_PROCESS_COUNT")
    _bounded_int(per_process, 1, MAX_PER_PROCESS, "INVALID_BATCH_LIMIT")
    if not isinstance(database_path, str) or not database_path or database_path == ":memory:":
        raise ValueError("PERSISTENT_DB_PATH_REQUIRED")
    path = os.path.abspath(database_path)
    queue = DurableLeaseQueue(path)
    backlog = queue.summary().get("QUEUED", 0)
    selected = choose_processes(processes, backlog, per_process, profile=profile)
    began = time.perf_counter()
    with ThreadPoolExecutor(max_workers=selected) as executor:
        workers = list(executor.map(lambda idx: _run_child(path, idx, per_process),
                                    range(selected)))
    elapsed = max(time.perf_counter() - began, 0.000001)
    failures = sum(not worker["ok"] for worker in workers)
    claimed = sum(worker.get("claimed", 0) for worker in workers)
    succeeded = sum(worker.get("succeeded", 0) for worker in workers)
    dead = sum(worker.get("dead", 0) for worker in workers)
    conflicts = sum(worker.get("lease_conflicts", 0) for worker in workers)
    recovered_requeued = sum(worker.get("recovered_requeued", 0) for worker in workers)
    recovered_dead = sum(worker.get("recovered_dead", 0) for worker in workers)
    states = queue.summary()  # independent persisted readback, not a child claim
    if failures or conflicts:
        verdict = "UNVERIFIED"
    elif dead:
        verdict = "FAILED"
    elif states.get("QUEUED", 0) or states.get("CLAIMED", 0):
        verdict = "PARTIAL"
    else:
        verdict = "PASS" if succeeded else "IDLE"
    return {"version": VERSION, "scope": "ISOLATED_LOCAL_SYNTHETIC_ONLY",
            "processes_requested": processes, "processes_started": selected,
            "processes_reported": selected - failures,
            "workload_profile_hint": profile,
            "runtime_process_cap": runtime_process_ceiling(profile),
            "elapsed_ms": round(elapsed * 1000, 2),
            "throughput_jobs_per_sec": round(succeeded / elapsed, 2),
            "claimed": claimed, "succeeded": succeeded, "dead": dead,
            "lease_conflicts": conflicts, "child_failures": failures,
            "recovered_requeued": recovered_requeued,
            "recovered_dead": recovered_dead,
            "queue_state": states, "verdict": verdict,
            "neon_connected": False, "hosted_worker_deployed": False,
            "unattended_24h_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="One-shot offline SQLite parallel workers")
    parser.add_argument("--db", required=True)
    parser.add_argument("--processes", default="auto",
                        help="auto or integer 1..256; real count is resource-bound")
    parser.add_argument("--per-process", type=int, default=4)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="mixed",
                        help="cpu | mixed | waiting; this is only a scheduling hint")
    args = parser.parse_args()
    requested = args.processes if args.processes == "auto" else int(args.processes)
    report = run_parallel(args.db, processes=requested, per_process=args.per_process,
                          profile=args.profile)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] in {"PASS", "IDLE", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
