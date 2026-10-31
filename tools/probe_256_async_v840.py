"""A single honest 256-coroutine concurrency probe with independent SQLite readback."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from tools.async_slots_v840 import run_async_slots
from tools.durable_queue_v831 import DurableLeaseQueue


def probe() -> dict:
    with tempfile.TemporaryDirectory(prefix="v840-256-") as folder:
        path = str(Path(folder) / "synthetic.sqlite3")
        queue = DurableLeaseQueue(path)
        for i in range(256):
            job_id = f"synthetic-v83-v840-probe-{i:03d}"
            queue.enqueue(job_id, "offline_check", hashlib.sha256(
                job_id.encode("ascii")).hexdigest())
        first = asyncio.run(run_async_slots(path, slots=256, simulated_wait_ms=100))
        second = asyncio.run(run_async_slots(path, slots=256, simulated_wait_ms=0))
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            count, retry, incomplete = conn.execute(
                """SELECT COUNT(*), SUM(CASE WHEN attempt<>1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN state<>'SUCCEEDED' THEN 1 ELSE 0 END) FROM jobs"""
            ).fetchone()
        if (first["verdict"] != "PASS" or
            first["peak_in_flight_coroutines"] != 256 or
            first["succeeded"] != 256 or
            second["claimed"] != 0 or count != 256 or retry or incomplete):
            raise RuntimeError("V840_256_SYNTHETIC_PROBE_FAILED")
        return {
            "status": "PASS",
            "scope": "ONE_PROCESS_256_COOPERATIVE_COROUTINES_SYNTHETIC_WAIT",
            "configured_async_slots": first["configured_slots"],
            "peak_in_flight_coroutines": first["peak_in_flight_coroutines"],
            "os_process_count": first["actual_os_processes"],
            "completed_jobs": count,
            "duplicate_or_retry_attempts": int(retry or 0),
            "second_run_claimed": second["claimed"],
            "elapsed_ms": first["elapsed_ms"],
            "jobs_per_second": first["measured_jobs_per_second"],
            "physical_cpu_workers": "NOT_MEASURED",
            "hosted_24h": False,
            "real_model_calls": 0,
        }


if __name__ == "__main__":
    print("V840_256_PROBE_JSON=" + json.dumps(probe(), sort_keys=True))
