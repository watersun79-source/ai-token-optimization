"""v8.3.6 isolated multi-process SQLite test runner; never hosts or schedules.

Only v8.3.3's synthetic offline handler can be invoked. The durable SQLite
file must live on the same persistent local disk for all child processes.
This is *not* a Render Free persistence or 24-hour automation solution.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

from tools.durable_queue_v831 import DurableLeaseQueue

VERSION = "8.3.6"
MAX_PROCESSES = 4
MAX_PER_PROCESS = 16
ROOT = str(Path(__file__).resolve().parent.parent)


def _bounded_int(value: int, low: int, high: int, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(code)
    return value


def _run_child(path: str, index: int, limit: int) -> dict:
    command = [sys.executable, "-m", "tools.isolated_worker_v833",
               "--db", path, "--worker-id", f"standalone-v836-{index}",
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
        return {"ok": True, "claimed": values[0], "succeeded": values[1],
                "dead": values[2], "lease_conflicts": values[3]}
    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError, json.JSONDecodeError):
        # Never include stderr, payloads or exception strings in the public report.
        return {"ok": False, "reason": "CHILD_UNVERIFIED"}


def run_parallel(database_path: str, *, processes: int = 4, per_process: int = 4) -> dict:
    """Execute at most four independent child processes once; no polling.

    The shared existing SQLite lease queue serializes CLAIM transactions and
    fences completions by token. This launcher does not guarantee exactly-once
    effects or persistence if the filesystem itself is ephemeral.
    """
    _bounded_int(processes, 1, MAX_PROCESSES, "INVALID_PROCESS_COUNT")
    _bounded_int(per_process, 1, MAX_PER_PROCESS, "INVALID_BATCH_LIMIT")
    if not isinstance(database_path, str) or not database_path or database_path == ":memory:":
        raise ValueError("PERSISTENT_DB_PATH_REQUIRED")
    path = os.path.abspath(database_path)
    queue = DurableLeaseQueue(path)
    with ThreadPoolExecutor(max_workers=processes) as executor:
        workers = list(executor.map(lambda idx: _run_child(path, idx, per_process),
                                    range(processes)))
    failures = sum(not worker["ok"] for worker in workers)
    claimed = sum(worker.get("claimed", 0) for worker in workers)
    succeeded = sum(worker.get("succeeded", 0) for worker in workers)
    dead = sum(worker.get("dead", 0) for worker in workers)
    conflicts = sum(worker.get("lease_conflicts", 0) for worker in workers)
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
            "processes_started": processes, "processes_reported": processes - failures,
            "claimed": claimed, "succeeded": succeeded, "dead": dead,
            "lease_conflicts": conflicts, "child_failures": failures,
            "queue_state": states, "verdict": verdict,
            "neon_connected": False, "hosted_worker_deployed": False,
            "unattended_24h_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="One-shot offline SQLite parallel workers")
    parser.add_argument("--db", required=True)
    parser.add_argument("--processes", type=int, default=4)
    parser.add_argument("--per-process", type=int, default=4)
    args = parser.parse_args()
    report = run_parallel(args.db, processes=args.processes, per_process=args.per_process)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] in {"PASS", "IDLE", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
