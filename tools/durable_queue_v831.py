"""AI BOT v8.3.1: offline SQLite lease queue with atomic crash recovery.

This library does NOT start a service, authenticate requests, or perform jobs.
It requires a persistent filesystem; Render Free ephemeral disk is unsuitable.
At-least-once work: callers must implement idempotent external effects.
"""
from __future__ import annotations

from contextlib import contextmanager
import re
import secrets
import sqlite3
import time

VERSION = "8.3.1"
_IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_TYPES = frozenset(("offline_check", "read_only"))
_RESULTS = frozenset(("OK", "RETRYABLE", "NOT_APPLICABLE", "FAILED"))


def _identifier(value: str) -> str:
    if not isinstance(value, str) or _IDENT.fullmatch(value) is None:
        raise ValueError("INVALID_ID")
    return value


class DurableLeaseQueue:
    def __init__(self, path: str, clock=None, *, max_attempts: int = 3):
        if not isinstance(path, str) or not path or path == ":memory:":
            raise ValueError("PERSISTENT_DB_PATH_REQUIRED")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
            raise ValueError("INVALID_ATTEMPT_BOUND")
        self.path, self.clock, self.max_attempts = path, clock or time.time, max_attempts
        with self._connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
                task_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('offline_check', 'read_only')),
                payload_digest TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('QUEUED','CLAIMED','SUCCEEDED','DEAD')),
                attempt INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT,
                lease_token TEXT,
                lease_until REAL,
                result_code TEXT NOT NULL DEFAULT 'NOT_STARTED',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS jobs_recovery ON jobs(state, lease_until)")
            conn.commit()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=10000")
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _write(self):
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _lease_seconds(seconds):
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 1 <= seconds <= 900:
            raise ValueError("INVALID_LEASE_SECONDS")
        return float(seconds)

    def enqueue(self, task_id: str, kind: str, payload_digest: str):
        _identifier(task_id)
        if kind not in _TYPES or not isinstance(payload_digest, str) or not _DIGEST.fullmatch(payload_digest):
            raise ValueError("UNSAFE_OR_INVALID_TASK")
        now = float(self.clock())
        with self._write() as conn:
            old = conn.execute("SELECT kind,payload_digest,state FROM jobs WHERE task_id=?", (task_id,)).fetchone()
            if old is not None:
                if old["kind"] != kind or old["payload_digest"] != payload_digest:
                    raise ValueError("IDEMPOTENCY_PAYLOAD_CONFLICT")
                return {"created": False, "task_id": task_id, "state": old["state"]}
            conn.execute("""INSERT INTO jobs
                (task_id,kind,payload_digest,state,created_at,updated_at)
                VALUES (?,?,?,'QUEUED',?,?)""", (task_id,kind,payload_digest,now,now))
            return {"created": True, "task_id": task_id, "state": "QUEUED"}

    def _recover_locked(self, conn, now):
        # Expired final attempts become terminal, preventing retry loops.
        dead = conn.execute("""UPDATE jobs SET state='DEAD', lease_owner=NULL,
            lease_token=NULL, lease_until=NULL, result_code='MAX_ATTEMPTS',
            updated_at=? WHERE state='CLAIMED' AND lease_until<=? AND attempt>=?""",
            (now,now,self.max_attempts)).rowcount
        ready = conn.execute("""UPDATE jobs SET state='QUEUED', lease_owner=NULL,
            lease_token=NULL, lease_until=NULL, result_code='LEASE_EXPIRED',
            updated_at=? WHERE state='CLAIMED' AND lease_until<=? AND attempt<?""",
            (now,now,self.max_attempts)).rowcount
        return {"requeued": ready, "dead": dead}

    def recover(self):
        with self._write() as conn:
            return self._recover_locked(conn, float(self.clock()))

    def claim(self, worker: str, lease_seconds: float = 60):
        _identifier(worker)
        lease_seconds = self._lease_seconds(lease_seconds)
        with self._write() as conn:
            now = float(self.clock())
            self._recover_locked(conn, now)
            row = conn.execute("""SELECT task_id,kind,attempt FROM jobs
                WHERE state='QUEUED' AND attempt<? ORDER BY created_at,task_id LIMIT 1""",
                (self.max_attempts,)).fetchone()
            if row is None:
                return None
            token = secrets.token_hex(24)
            changed = conn.execute("""UPDATE jobs SET state='CLAIMED', attempt=attempt+1,
                lease_owner=?, lease_token=?, lease_until=?, updated_at=?
                WHERE task_id=? AND state='QUEUED'""",
                (worker,token,now+lease_seconds,now,row["task_id"])).rowcount
            if changed != 1:
                raise RuntimeError("CLAIM_TRANSACTION_CONFLICT")
            return {"task_id": row["task_id"], "kind": row["kind"], "worker": worker,
                    "lease_token": token, "attempt": row["attempt"]+1,
                    "lease_until": now+lease_seconds}

    def heartbeat(self, task_id: str, worker: str, lease_token: str, lease_seconds: float = 60):
        _identifier(task_id); _identifier(worker)
        lease_seconds = self._lease_seconds(lease_seconds)
        if not isinstance(lease_token, str):
            return False
        now = float(self.clock())
        with self._write() as conn:
            n = conn.execute("""UPDATE jobs SET lease_until=?, updated_at=?
                WHERE task_id=? AND state='CLAIMED' AND lease_owner=?
                AND lease_token=? AND lease_until>?""",
                (now+lease_seconds,now,task_id,worker,lease_token,now)).rowcount
            return n == 1

    def complete(self, task_id: str, worker: str, lease_token: str, *,
                 success: bool, retryable: bool = False, result_code: str = "OK"):
        _identifier(task_id); _identifier(worker)
        if not isinstance(lease_token, str) or not isinstance(success, bool) or            not isinstance(retryable, bool) or result_code not in _RESULTS:
            raise ValueError("INVALID_COMPLETION")
        now = float(self.clock())
        with self._write() as conn:
            row = conn.execute("""SELECT attempt FROM jobs WHERE task_id=? AND
                state='CLAIMED' AND lease_owner=? AND lease_token=? AND lease_until>?""",
                (task_id,worker,lease_token,now)).fetchone()
            if row is None:
                return False
            state = "SUCCEEDED" if success else (
                "QUEUED" if retryable and row["attempt"] < self.max_attempts else "DEAD")
            code = "OK" if success else ("RETRYABLE" if state=="QUEUED" else "FAILED")
            conn.execute("""UPDATE jobs SET state=?, lease_owner=NULL, lease_token=NULL,
                lease_until=NULL, result_code=?, updated_at=? WHERE task_id=?""",
                (state,code,now,task_id))
            return True

    def get(self, task_id: str):
        _identifier(task_id)
        with self._connection() as conn:
            row=conn.execute("""SELECT task_id,kind,state,attempt,lease_owner,
                lease_until,result_code FROM jobs WHERE task_id=?""",(task_id,)).fetchone()
            return dict(row) if row else None

    def summary(self):
        with self._connection() as conn:
            return {r["state"]:r["n"] for r in conn.execute(
                "SELECT state,COUNT(*) AS n FROM jobs GROUP BY state").fetchall()}
