"""AI BOT v8.4.0 -- 256 cooperative async slots on a *single* local process.

Runs only deterministic synthetic offline jobs. The overlap barrier is a
synthetic wait, not 256 OS processes, independent CPU cores, real external I/O,
hosted 24-hour service, or production task execution.

The shared SQLite lease queue guarantees atomic task ownership and fencing on
one persistent filesystem, not persistent storage across machine replacement.
No network, remote models, webhooks, private data or mutable remote effects.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.isolated_worker_v833 import SAFE_TEST_ID, _synthetic_check

VERSION = "8.4.0"
MAX_ASYNC_SLOTS = 256
MAX_SIMULATED_WAIT_MS = 500


async def run_async_slots(database_path: str, *, slots: int = 256,
                          simulated_wait_ms: int = 30) -> dict:
    """One bounded batch: claim serially, overlap isolated waits, commit serially.

    The barrier proves that N coroutines reached an await concurrently. The
    measured elapsed time includes SQLite claims and commits, and is *not*
    a benchmark of any real network or model workload.
    """
    if type(slots) is not int or not 1 <= slots <= MAX_ASYNC_SLOTS:
        raise ValueError("INVALID_ASYNC_SLOT_COUNT")
    if type(simulated_wait_ms) is not int or not 0 <= simulated_wait_ms <= MAX_SIMULATED_WAIT_MS:
        raise ValueError("INVALID_SIMULATED_WAIT")
    if not isinstance(database_path, str) or not database_path or database_path == ":memory:":
        raise ValueError("PERSISTENT_DB_PATH_REQUIRED")

    queue = DurableLeaseQueue(os.path.abspath(database_path))
    started_at = time.perf_counter()
    recovery = queue.recover()
    claims = []
    for index in range(slots):
        lease = queue.claim(f"async-v840-{index}", lease_seconds=60)
        if lease is None:
            break
        claims.append(lease)

    active = peak = started = 0
    gate = asyncio.Event()

    async def execute(lease: dict) -> str:
        nonlocal active, peak, started
        active += 1
        peak = max(active, peak)
        started += 1
        if started == len(claims):
            gate.set()
        try:
            await gate.wait()  # guarantees measured coroutine overlap in test
            await asyncio.sleep(simulated_wait_ms / 1000)
            valid = (lease["kind"] == "offline_check" and
                     SAFE_TEST_ID.fullmatch(lease["task_id"]) is not None and
                     _synthetic_check(lease))
            committed = queue.complete(
                lease["task_id"], lease["worker"], lease["lease_token"],
                success=bool(valid), retryable=False,
                result_code="OK" if valid else "FAILED"
            )
            return ("SUCCEEDED" if valid and committed else
                    "DEAD" if committed else "LEASE_CONFLICT")
        except Exception:
            # Never print exception detail, job payload or credentials.
            try:
                queue.complete(lease["task_id"], lease["worker"],
                               lease["lease_token"], success=False,
                               retryable=False, result_code="FAILED")
            except Exception:
                pass
            return "FAILED_UNVERIFIED"
        finally:
            active -= 1

    results = await asyncio.gather(*(execute(item) for item in claims))
    elapsed = max(1e-6, time.perf_counter() - started_at)
    states = queue.summary()
    succeeded = results.count("SUCCEEDED")
    dead = results.count("DEAD")
    conflict = results.count("LEASE_CONFLICT")
    failures = results.count("FAILED_UNVERIFIED")
    verdict = ("UNVERIFIED" if failures or conflict else
               "FAILED" if dead else
               "PARTIAL" if states.get("QUEUED", 0) or states.get("CLAIMED", 0) else
               "PASS" if succeeded else "IDLE")
    return {
        "version": VERSION, "scope": "SINGLE_PROCESS_SYNTHETIC_ASYNC_WAIT_ONLY",
        "configured_slots": slots, "created_coroutines": len(claims),
        "peak_in_flight_coroutines": peak,
        "actual_os_processes": 1,
        "claimed": len(claims), "succeeded": succeeded,
        "dead": dead, "lease_conflicts": conflict,
        "failed_unverified": failures,
        "recovered": recovery, "queue_state": states,
        "elapsed_ms": round(elapsed * 1000, 2),
        "measured_jobs_per_second": round(succeeded / elapsed, 2),
        "verdict": verdict, "neon_used": False,
        "hosted_worker_deployed": False, "unattended_24h_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic 256 async slots, local only")
    parser.add_argument("--db", required=True)
    parser.add_argument("--slots", type=int, default=256)
    parser.add_argument("--wait-ms", type=int, default=30)
    opts = parser.parse_args()
    report = asyncio.run(run_async_slots(
        opts.db, slots=opts.slots, simulated_wait_ms=opts.wait_ms))
    print("V840_ASYNC_RESULT=" + json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] in ("PASS", "PARTIAL", "IDLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
