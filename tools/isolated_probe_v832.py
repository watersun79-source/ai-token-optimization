"""AI BOT v8.3.2 isolated hosting probe.

Public read-only health endpoints ONLY. No job execution, database access,
secrets, webhook events, paid models, or persistence. A Render Free service
running this code does not prove 24/7 uptime or durable task recovery.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time
import uuid
from urllib.parse import urlsplit

from tools.durable_queue_v831 import VERSION as QUEUE_VERSION

PROBE_VERSION = "8.3.2"
BOOT_ID = uuid.uuid4().hex[:20]
STARTED_MONOTONIC = time.monotonic()


class ProbeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class ProbeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond(self, status, payload, head=False):
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def _route(self, head=False):
        path = urlsplit(self.path).path
        if path in ("/", "/healthz", "/readyz"):
            self._respond(200, {
                "status": "UP",
                "probe_version": PROBE_VERSION,
                "lease_code_version": QUEUE_VERSION,
                "boot_id": BOOT_ID,
                "uptime_seconds": int(time.monotonic() - STARTED_MONOTONIC),
                "read_only": True,
                "jobs_enabled": False,
                "persistent_database_connected": False,
                "native_execution_verified": False,
                "automatic_restart_verified": False,
            }, head=head)
        else:
            self._respond(404, {"status": "NOT_FOUND"}, head=head)

    def do_GET(self):
        self._route()

    def do_HEAD(self):
        self._route(head=True)

    def do_POST(self):
        self._respond(405, {"status": "METHOD_NOT_ALLOWED"})

    do_PUT = do_DELETE = do_PATCH = do_POST

    def log_message(self, _fmt, *_args):
        # Never log headers, cookies, query parameters or request bodies.
        return


def main():
    host = os.environ.get("PROBE_HOST", "0.0.0.0")
    raw_port = os.environ.get("PORT", "10000")
    port = int(raw_port)
    if not 0 <= port <= 65535:
        raise ValueError("INVALID_PORT")
    server = ProbeServer((host, port), ProbeHandler)
    print("PROBE_READY port=" + str(server.server_address[1]), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
