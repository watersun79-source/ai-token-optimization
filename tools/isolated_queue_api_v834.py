"""AI BOT v8.3.4: authenticated, synthetic-only HTTP intake + SQLite worker.

LOCAL/ISOLATED TEST ONLY. No user jobs, network egress, AI models, or
production service integrations. Same durable SQLite file shared by intake
and worker; restarts recover leases ONLY if underlying disk persists.
Render Free local files are ephemeral and cannot satisfy that guarantee.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
import re
import secrets
import sys
import time
import uuid

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.isolated_worker_v833 import run_batch

VERSION = "8.3.4"
STARTED = time.monotonic()
BOOT_ID = uuid.uuid4().hex[:20]
SYNTHETIC = re.compile(r"^synthetic-v83-[a-z0-9-]{1,52}$")


class QueueServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, *, database_path: str, auth_key: str):
        super().__init__(address, handler)
        self.db_path = database_path
        self.auth_key = auth_key
        self.ready = isinstance(database_path, str) and bool(database_path) and (
            isinstance(auth_key, str) and len(auth_key) >= 32)
        if self.ready:
            self.store = DurableLeaseQueue(database_path)
        else:
            self.store = None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        # No request parameters, authentication headers, or job identifiers logged.
        return

    def answer(self, status: int, payload: dict, *, head: bool = False):
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def authorized(self) -> bool:
        key = self.headers.get("X-Queue-Key", "")
        expected = self.server.auth_key
        return bool(self.server.ready and key and len(key) <= 256 and
                    secrets.compare_digest(key, expected))

    def do_GET(self):
        if self.path == "/healthz":
            return self.answer(200, {
                "status": "UP", "version": VERSION, "boot_id": BOOT_ID,
                "uptime_seconds": int(time.monotonic() - STARTED),
                "synthetic_only": True,
                "ingress_configured": bool(self.server.ready),
                "persistent_disk_verified": False,
                "production_connected": False,
                "always_on_verified": False,
            })
        if self.path == "/private/state":
            if not self.authorized():
                return self.answer(401, {"error": "UNAUTHORIZED"})
            return self.answer(200, {
                "version": VERSION, "queue": self.server.store.summary(),
                "production_connected": False,
            })
        return self.answer(404, {"error": "NOT_FOUND"})

    def do_HEAD(self):
        if self.path == "/healthz":
            return self.answer(200, {"status": "UP", "version": VERSION}, head=True)
        return self.answer(404, {"error": "NOT_FOUND"}, head=True)

    def do_POST(self):
        if self.path not in ("/private/submit", "/private/recover"):
            return self.answer(404, {"error": "NOT_FOUND"})
        if not self.authorized():
            return self.answer(401, {"error": "UNAUTHORIZED"})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.answer(400, {"error": "INVALID_LENGTH"})
        if length < 2 or length > 256:
            return self.answer(413, {"error": "INVALID_BODY_SIZE"})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return self.answer(400, {"error": "INVALID_JSON"})
        if not isinstance(body, dict):
            return self.answer(400, {"error": "INVALID_OBJECT"})
        if self.path == "/private/recover":
            if body != {}:
                return self.answer(400, {"error": "UNEXPECTED_FIELDS"})
            return self.answer(200, {"operation": "RECOVER_AND_RUN_ONCE",
                **run_batch(self.server.db_path, limit=2, concurrency=2)})
        if set(body) != {"task_id", "kind"} or body.get("kind") != "offline_check":
            return self.answer(400, {"error": "UNSAFE_JOB"})
        task_id = body.get("task_id")
        if not isinstance(task_id, str) or not SYNTHETIC.fullmatch(task_id):
            return self.answer(400, {"error": "UNSAFE_JOB"})
        digest = hashlib.sha256(task_id.encode("ascii")).hexdigest()
        try:
            queued = self.server.store.enqueue(task_id, "offline_check", digest)
            report = run_batch(self.server.db_path, limit=2, concurrency=2)
            observed = self.server.store.get(task_id)
        except (ValueError, OSError):
            return self.answer(500, {"error": "INTERNAL_QUEUE_ERROR"})
        return self.answer(200, {
            "accepted": True, "new": queued["created"],
            "state": observed["state"] if observed else "UNKNOWN",
            "batch": {k: report[k] for k in ("claimed", "succeeded", "dead", "lease_conflicts")},
            "production_connected": False, "synthetic_only": True,
        })

    do_PUT = do_PATCH = do_DELETE = lambda self: self.answer(
        405, {"error": "METHOD_NOT_ALLOWED"})


def main():
    port = int(os.environ.get("PORT", "10000"))
    if not 0 <= port <= 65535:
        raise ValueError("INVALID_PORT")
    db = os.environ.get("ISOLATED_DB_PATH", "")
    key = os.environ.get("ISOLATED_JOB_KEY", "")
    server = QueueServer((os.environ.get("PROBE_HOST", "0.0.0.0"), port),
                         Handler, database_path=db, auth_key=key)
    # Never include secrets, database paths or synthetic IDs in logs.
    print("ISOLATED_GATEWAY_READY port=" + str(server.server_address[1])
          + " ingress_configured=" + str(server.ready).lower(), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
