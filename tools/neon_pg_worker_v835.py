"""AI BOT v8.3.5 — isolated synthetic-only Neon Postgres queue worker.

No production tasks, external model calls or credentials in source/logs.
Must be paired with the v8.3.5 Neon SQL functions. Postgres is the sole
transactional source; this does not make Render Free always-on.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import re
from typing import Callable

VERSION = "8.3.5"
SAFE_ID = re.compile(r"^synthetic-v83-[a-z0-9-]{1,52}$")
SAFE_WORKER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


def is_synthetic_job(job_id: str) -> bool:
    return isinstance(job_id, str) and bool(SAFE_ID.fullmatch(job_id))


def _connection(database_url: str):
    if not isinstance(database_url, str) or not database_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_NOT_CONFIGURED")
    import psycopg  # Optional when backend not configured; pin binary wheel at deploy.
    return psycopg.connect(database_url, connect_timeout=10, autocommit=False)


def _query(database_url: str, sql: str, params: tuple = (), *, factory=None) -> list:
    # All callers use bound placeholders, never format SQL or credentials.
    factory = factory or _connection
    with factory(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else []


def enqueue(database_url: str, job_id: str, *, factory=None) -> bool:
    if not is_synthetic_job(job_id):
        raise ValueError("UNSAFE_JOB_ID")
    rows = _query(database_url,
        "INSERT INTO public.isolated_synthetic_jobs_v834(task_id,kind) "
        "VALUES (%s,'offline_check') ON CONFLICT (task_id) DO NOTHING RETURNING task_id",
        (job_id,), factory=factory)
    return len(rows) == 1


def summary(database_url: str, *, factory=None) -> dict:
    rows = _query(database_url,
        "SELECT state,count(*)::integer FROM public.isolated_synthetic_jobs_v834 GROUP BY state",
        factory=factory)
    return {str(k): int(v) for k, v in rows}


def run_once(database_url: str, *, worker: str = "v835-isolated", limit: int = 2,
             concurrency: int = 2, factory: Callable | None = None) -> dict:
    if not isinstance(worker, str) or not SAFE_WORKER.fullmatch(worker):
        raise ValueError("INVALID_WORKER")
    if type(limit) is not int or not 1 <= limit <= 4:
        raise ValueError("INVALID_LIMIT")
    if type(concurrency) is not int or not 1 <= concurrency <= 2:
        raise ValueError("INVALID_CONCURRENCY")
    if not database_url:
        raise ValueError("DATABASE_NOT_CONFIGURED")
    # Atomic SKIP LOCKED claim and token fencing both live on Neon Postgres.
    claims = []
    for _ in range(limit):
        row = _query(database_url,
            "SELECT task_id,attempt,lease_owner,lease_token,lease_until "
            "FROM public.ai_v835_claim_synthetic(%s,90)",
            (worker,), factory=factory)
        if not row:
            break
        claims.append(row[0])

    def work(claim):
        task_id, attempt, owner, token, _until = claim
        ok = is_synthetic_job(task_id) and owner == worker and type(attempt) is int and attempt <= 5
        if ok:
            # CPU-only deterministic verification, no outbound operations.
            digest = hashlib.sha256(task_id.encode("ascii")).digest()
            ok = len(digest) == 32
        rows = _query(database_url,
            "SELECT task_id,state,attempt,result_code "
            "FROM public.ai_v835_complete_synthetic(%s,%s,%s,%s)",
            (task_id, owner, token, ok), factory=factory)
        if not rows:
            return "LEASE_CONFLICT"
        return "SUCCEEDED" if rows[0][1] == "SUCCEEDED" and ok else "DEAD"

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        statuses = list(pool.map(work, claims))
    return {
        "version": VERSION, "synthetic_only": True, "production_connected": False,
        "claimed": len(claims),
        "succeeded": statuses.count("SUCCEEDED"),
        "dead": statuses.count("DEAD"),
        "lease_conflicts": statuses.count("LEASE_CONFLICT"),
        "durable_backend": "NEON_POSTGRES_TRANSACTIONAL",
        "always_on_verified": False,
    }
