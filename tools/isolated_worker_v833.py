"""AI BOT v8.3.3 -- a fail-closed *local* worker for durable SQLite leases.

This program executes only deterministic synthetic offline checks. No API calls,
no AI models, no webhook intake, no user data or mutable external side effects.
Persistent database must be on durable disk. This is NOT the deployed Render
health-only server, nor a 24-hour worker by itself.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from typing import Callable

from tools.durable_queue_v831 import DurableLeaseQueue

VERSION = "8.3.3"
SAFE_TEST_ID = re.compile(r"^synthetic-v83-[a-z0-9-]{1,52}$")


def _synthetic_check(job: dict) -> bool:
    """Real deterministic CPU-only check, never external execution."""
    task_id = job.get("task_id", "")
    if job.get("kind") != "offline_check" or not SAFE_TEST_ID.fullmatch(task_id):
        return False
    digest = hashlib.sha256(task_id.encode("ascii")).digest()
    return len(digest) == 32 and hashlib.sha256(task_id.encode("ascii")).digest() == digest


def run_batch(
    database_path: str,
    *,
    worker_id: str = "isolated-v833",
    limit: int = 4,
    concurrency: int = 2,
    check: Callable[[dict], bool] | None = None,
) -> dict:
    """Process one finite batch and exit. Every call reopens the persistent DB.

    Records remain on disk between invocations. The queue itself uses BEGIN
    IMMEDIATE transactions, per-job lease tokens, expiration and dead letters.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 16:
        raise ValueError("INVALID_BATCH_LIMIT")
    if isinstance(concurrency, bool) or not isinstance(concurrency, int) or not 1 <= concurrency <= 4:
        raise ValueError("INVALID_WORKER_CONCURRENCY")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}", worker_id or ""):
        raise ValueError("INVALID_WORKER_ID")
    queue = DurableLeaseQueue(database_path)
    recovery = queue.recover()
    handler = check or _synthetic_check
    claims = []
    for _ in range(limit):
        lease = queue.claim(worker_id, lease_seconds=60)
        if lease is None:
            break
        claims.append(lease)

    def execute(lease: dict) -> dict:
        # Never print errors, private job data or provided payloads.
        ok = False
        try:
            # Enforcement is independent of the injected deterministic test
            # handler, so a caller cannot authorize non-synthetic work here.
            if lease["kind"] == "offline_check" and SAFE_TEST_ID.fullmatch(lease["task_id"]):
                ok = handler(lease) is True
        except Exception:
            ok = False
        committed = queue.complete(
            lease["task_id"], lease["worker"], lease["lease_token"],
            success=ok, retryable=False, result_code="OK" if ok else "FAILED",
        )
        return {
            "task_id": lease["task_id"],
            "status": "SUCCEEDED" if ok and committed else "DEAD" if committed else "LEASE_CONFLICT",
            "attempt": lease["attempt"],
        }

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(execute, claims))

    return {
        "version": VERSION, "scope": "LOCAL_SYNTHETIC_ONLY",
        "recovered": recovery, "claimed": len(claims),
        "succeeded": sum(r["status"] == "SUCCEEDED" for r in results),
        "dead": sum(r["status"] == "DEAD" for r in results),
        "lease_conflicts": sum(r["status"] == "LEASE_CONFLICT" for r in results),
        "queue_state": queue.summary(),
        "production_connected": False,
        "render_worker_deployed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-shot, synthetic-only v8.3.3 local worker")
    parser.add_argument("--db", required=True, help="existing durable SQLite job database path")
    parser.add_argument("--worker-id", default="isolated-v833")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()
    result = run_batch(args.db, worker_id=args.worker_id, limit=args.limit,
                       concurrency=args.concurrency)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["lease_conflicts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
