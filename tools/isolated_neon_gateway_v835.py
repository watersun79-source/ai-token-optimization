"""AI BOT v8.3.5 isolated HTTPS ingress with Neon transactional work queue.

Only synthetic local CPU checks. No polling, long-running background work,
external AI calls, secrets in URLs, or production task execution.
This is not an always-on service on Render Free.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import secrets
import time
import uuid

from tools import neon_pg_worker_v835 as worker

VERSION = "8.3.5"
BOOT_ID = uuid.uuid4().hex[:20]
STARTED = time.monotonic()
SAFE_ID = re.compile(r"^synthetic-v83-[a-z0-9-]{1,52}$")


class App(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host, port, *, database_url, api_key):
        super().__init__((host, port), Handler)
        self.database_url = database_url
        self.api_key = api_key
        self.enabled = (
            isinstance(database_url, str)
            and database_url.startswith(("postgresql://", "postgres://"))
            and isinstance(api_key, str)
            and len(api_key) >= 32
        )
        self.last_db_ok = False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args):
        return  # Never log authentication headers, SQL, URI params or payload.

    def send(self, status, payload):
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        provided = self.headers.get("X-Queue-Key", "")
        return bool(
            self.server.enabled
            and 1 <= len(provided) <= 256
            and secrets.compare_digest(provided, self.server.api_key)
        )

    def do_GET(self):
        if self.path == "/healthz":
            return self.send(200, {
                "status": "UP", "version": VERSION, "boot_id": BOOT_ID,
                "uptime_seconds": int(time.monotonic() - STARTED),
                "synthetic_only": True, "backend": "neon_postgres",
                "intake_enabled": self.server.enabled,
                "database_connection_verified": self.server.last_db_ok,
                "always_on_verified": False,
                "automatic_recovery_verified": False,
                "production_connected": False,
            })
        if self.path != "/private/state":
            return self.send(404, {"error": "NOT_FOUND"})
        if not self.authorized():
            return self.send(401, {"error": "UNAUTHORIZED"})
        try:
            counts = worker.summary(self.server.database_url)
            self.server.last_db_ok = True
        except Exception:
            return self.send(503, {"error": "BACKEND_UNAVAILABLE"})
        return self.send(200, {"version": VERSION, "state_counts": counts,
                               "production_connected": False})

    def do_POST(self):
        if self.path not in ("/private/submit", "/private/recover"):
            return self.send(404, {"error": "NOT_FOUND"})
        if not self.authorized():
            return self.send(401, {"error": "UNAUTHORIZED"})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.send(400, {"error": "INVALID_LENGTH"})
        if not 2 <= length <= 256:
            return self.send(413, {"error": "INVALID_LENGTH"})
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self.send(400, {"error": "INVALID_JSON"})
        if not isinstance(data, dict):
            return self.send(400, {"error": "INVALID_BODY"})
        if self.path == "/private/recover" and data != {}:
            return self.send(400, {"error": "UNEXPECTED_FIELDS"})
        if self.path == "/private/submit":
            if set(data) != {"task_id", "kind"} or data["kind"] != "offline_check":
                return self.send(400, {"error": "UNSAFE_JOB"})
            if not isinstance(data["task_id"], str) or not SAFE_ID.fullmatch(data["task_id"]):
                return self.send(400, {"error": "UNSAFE_JOB"})
        try:
            new = worker.enqueue(self.server.database_url, data["task_id"]) if (
                self.path == "/private/submit") else None
            # Deliberately bounded; no timer, no recurring queue scan.
            outcome = worker.run_once(self.server.database_url, limit=2, concurrency=2)
            self.server.last_db_ok = True
        except Exception:
            return self.send(503, {"error": "BACKEND_UNAVAILABLE"})
        return self.send(200, {"accepted": True, "new": new,
                               "batch": outcome, "production_connected": False})

    def do_PUT(self):
        return self.send(405, {"error": "METHOD_NOT_ALLOWED"})
    do_PATCH = do_DELETE = do_PUT


def main():
    port = int(os.environ.get("PORT", "10000"))
    app = App(os.environ.get("PROBE_HOST", "0.0.0.0"), port,
              database_url=os.environ.get("NEON_QUEUE_DATABASE_URL", ""),
              api_key=os.environ.get("ISOLATED_JOB_KEY", ""))
    print("V835_GATEWAY_READY port=" + str(app.server_address[1]) +
          " intake_enabled=" + str(app.enabled).lower(), flush=True)
    try:
        app.serve_forever(poll_interval=.1)
    finally:
        app.server_close()


if __name__ == "__main__":
    main()
