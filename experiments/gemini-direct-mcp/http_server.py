"""Authenticated HTTP transport for the real Gemini CLI MCP adapter.

Only /healthz is public. Authentication codes are accepted only by the protected
HTTP auth route, never as MCP arguments. This module never reads CLI credentials.
"""
from __future__ import annotations

import dataclasses
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY = 65_536
ACTOR = re.compile(r"[A-Za-z0-9:_.-]{1,200}\Z")
SESSION_ID = re.compile(r"[a-f0-9]{48}\Z")
AUTH_CODE = re.compile(r"[A-Za-z0-9_./+%=-]{16,4096}\Z")
ANSI = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")
AUTH_URL = re.compile(rb"https://accounts\.google\.com/o/oauth2/v2/auth\?[^\s\x1b]+")
OFFICIAL_CLI_OAUTH_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
ACTIVE_STATES = {"STARTING", "WAITING_FOR_AUTH_CODE", "VERIFYING"}
PROVIDER_ENV = {
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA", "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION",
}


class RequestError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def valid_initial_auth_url(value):
    try:
        u = urlsplit(value)
        q = parse_qs(u.query, strict_parsing=True)
        return (
            len(value) <= 8192 and u.scheme == "https" and
            u.netloc == "accounts.google.com" and u.path == "/o/oauth2/v2/auth" and
            not u.fragment and q.get("response_type") == ["code"] and
            q.get("client_id") == [OFFICIAL_CLI_OAUTH_CLIENT_ID] and
            q.get("redirect_uri") == ["https://codeassist.google.com/authcode"] and
            q.get("code_challenge_method") == ["S256"] and
            len(q.get("code_challenge", [""])[0]) >= 43 and
            len(q.get("state", [""])[0]) >= 32 and
            "code" not in q and "access_token" not in q and "refresh_token" not in q
        )
    except (ValueError, TypeError):
        return False


class ManualAuthSession:
    """Bounded Linux PTY flow using the unmodified official CLI."""
    def __init__(self, actor, cli, auth_root, on_success, ttl=300):
        self.actor = actor
        self.id = secrets.token_hex(24)
        self.deadline = time.monotonic() + ttl
        self.state = "STARTING"
        self.url = None
        self.submitted = False
        self._buffer = bytearray()
        self._trust_handled = False
        self._google_handled = False
        self._success_match = 0
        self._output_count = 0
        self._lock = threading.RLock()
        self._stopped = threading.Event()
        self._on_success = on_success
        self.home = Path(tempfile.mkdtemp(prefix="google-auth-", dir=auth_root))
        self.home.chmod(0o700)
        work = self.home / "empty-work"
        work.mkdir(mode=0o700)
        settings = self.home / ".gemini"
        settings.mkdir(mode=0o700)
        # Public CLI configuration only. No token is read or written by us.
        (settings / "settings.json").write_text(json.dumps({
            "security": {"auth": {"selectedType": "oauth-personal"}},
            "telemetry": {"enabled": False},
            "ui": {"accessibility": {"screenReader": True}},
        }))
        if os.name != "posix" or any(os.environ.get(k) for k in PROVIDER_ENV):
            self.state = "BLOCKED_AUTH_RUNTIME"
            return
        import pty
        import termios
        master, slave = pty.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        self.master = master
        keep = ("PATH", "HOME", "USERPROFILE", "LANG", "LC_ALL", "TZ")
        env = {k: os.environ[k] for k in keep if k in os.environ}
        env.update({"GEMINI_CLI_HOME": str(self.home), "GEMINI_TELEMETRY_ENABLED": "false",
                    "NO_BROWSER": "true", "TERM": "xterm-256color"})
        try:
            self.process = subprocess.Popen(
                [str(cli), "--screen-reader", "--approval-mode", "plan"],
                stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env,
                shell=False, start_new_session=True, close_fds=True,
            )
        except OSError:
            os.close(master)
            self.state = "BLOCKED_AUTH_START"
            return
        finally:
            os.close(slave)
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._expire, daemon=True).start()

    def _write_control(self, value):
        os.write(self.master, value)

    def _observe(self, chunk):
        """Never retain the CLI output after a credential was submitted."""
        with self._lock:
            clean = ANSI.sub(b"", chunk)
            self._output_count += len(chunk)
            if self._output_count > MAX_BODY:
                self.state = "BLOCKED_AUTH_OUTPUT_LIMIT"
                self.stop()
                return
            if self.submitted:
                # A fixed public success marker only; no retained output or account data.
                marker = b"Authentication succeeded"
                for byte in clean:
                    if byte == marker[self._success_match]:
                        self._success_match += 1
                    else:
                        self._success_match = 1 if byte == marker[0] else 0
                    if self._success_match == len(marker):
                        self.state = "CLI_AUTHENTICATED_QUOTA_UNVERIFIED"
                        self._on_success(self.home)
                        self.stop()
                        break
                return
            if len(self._buffer) + len(clean) > MAX_BODY:
                self.state = "BLOCKED_AUTH_OUTPUT_LIMIT"
                self.stop()
                return
            self._buffer.extend(clean)
            data = bytes(self._buffer)
            if not self._trust_handled and b"Do you trust the files in this folder?" in data and b"Don't trust" in data:
                self._trust_handled = True
                self._buffer.clear()
                self._write_control(b"\x1b[B\x1b[B\r")
                return
            if not self._google_handled and b"How would you like to authenticate" in data and b"Sign in with Google" in data:
                self._google_handled = True
                self._buffer.clear()
                self._write_control(b"\r")
                return
            match = AUTH_URL.search(data)
            if match:
                url = match.group().decode("ascii", errors="strict")
                if not valid_initial_auth_url(url):
                    self.state = "BLOCKED_UNEXPECTED_AUTH_URL"
                    self.stop()
                    return
                self.url = url
            if self.url and b"Enter the authorization code:" in data:
                self.state = "WAITING_FOR_AUTH_CODE"
                self._buffer.clear()

    def _read(self):
        descriptor = self.master
        try:
            while self.state in ACTIVE_STATES:
                chunk = os.read(descriptor, 8192)
                if not chunk:
                    break
                self._observe(chunk)
        except (OSError, ValueError, UnicodeError):
            pass
        finally:
            with self._lock:
                if self.state in ACTIVE_STATES:
                    self.state = "CLI_AUTH_RESULT_UNVERIFIED"
                self._buffer.clear()
                self.stop()

    def _expire(self):
        # Event wait returns promptly when the flow is stopped.
        delay = max(0.0, self.deadline - time.monotonic())
        if not getattr(self, "_stopped", threading.Event()).wait(delay):
            with self._lock:
                if self.state in ACTIVE_STATES:
                    self.state = "AUTH_SESSION_EXPIRED"
                    self.stop()

    def finish(self, code):
        import termios
        with self._lock:
            if time.monotonic() >= self.deadline:
                self.state = "AUTH_SESSION_EXPIRED"
                self.stop()
                raise RequestError(409, "AUTH_SESSION_EXPIRED")
            if self.submitted or self.state != "WAITING_FOR_AUTH_CODE":
                raise RequestError(409, "AUTH_NOT_WAITING")
            if not isinstance(code, str) or not AUTH_CODE.fullmatch(code):
                raise RequestError(400, "INVALID_AUTH_CODE_FORMAT")
            # Reapply echo-off after the CLI may have changed terminal settings.
            attrs = termios.tcgetattr(self.master)
            attrs[3] &= ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(self.master, termios.TCSANOW, attrs)
            self.submitted = True
            self.state = "VERIFYING"
            self.url = None
            self._buffer.clear()
            try:
                os.write(self.master, code.encode("ascii") + b"\r")
            except OSError:
                self.state = "CLI_AUTH_RESULT_UNVERIFIED"
                self.stop()
                raise RequestError(502, "AUTH_INPUT_FAILED") from None
            return self.public()

    def public(self):
        with self._lock:
            result = {"session_id": self.id, "status": self.state,
                      "expires_in_seconds": max(0, int(self.deadline - time.monotonic())),
                      "quota": "UNVERIFIED", "model_called": False,
                      "authenticated": self.state == "CLI_AUTHENTICATED_QUOTA_UNVERIFIED"}
            if self.state == "WAITING_FOR_AUTH_CODE" and self.url:
                result["authorization_url"] = self.url
            return result

    def stop(self):
        if not hasattr(self, "_stopped"):
            self._stopped = threading.Event()
        with self._lock:
            if self._stopped.is_set():
                return
            self._stopped.set()
            process = getattr(self, "process", None)
            descriptor = getattr(self, "master", None)
            self.master = None
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


class AuthManager:
    def __init__(self, cli, auth_root, on_success, factory=ManualAuthSession):
        self.cli, self.root, self.callback = cli, auth_root, on_success
        self.factory = factory
        self.session = None
        self.lock = threading.RLock()

    def _actor(self, value):
        if not isinstance(value, str) or not ACTOR.fullmatch(value):
            raise RequestError(400, "INVALID_ACTOR")

    def start(self, actor):
        self._actor(actor)
        with self.lock:
            if self.session and self.session.state in ACTIVE_STATES:
                if hmac.compare_digest(self.session.actor, actor):
                    return self.session.public()
                raise RequestError(409, "AUTH_SESSION_BUSY")
            if self.cli is None:
                raise RequestError(503, "CLI_UNAVAILABLE")
            self.session = self.factory(actor, self.cli, self.root, self.callback)
            return self.session.public()

    def get(self, actor, session_id):
        self._actor(actor)
        if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
            raise RequestError(400, "INVALID_SESSION_ID")
        with self.lock:
            s = self.session
            if not s or not hmac.compare_digest(s.id, session_id) or not hmac.compare_digest(s.actor, actor):
                raise RequestError(404, "AUTH_SESSION_NOT_FOUND")
            return s


class Runtime:
    def __init__(self, adapter, server_class, key, auth_factory=ManualAuthSession):
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", key):
            raise ValueError("GEMINI_BRIDGE_KEY must be a secret of 32 to 256 URL-safe characters")
        self.adapter, self.server_class, self.key = adapter, server_class, key
        auth_root = adapter.config.state_dir / "auth-attempts"
        if auth_root.is_symlink():
            raise ValueError("Unsafe authentication state directory")
        auth_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.auth = AuthManager(adapter.config.cli, auth_root, self.activate_home, auth_factory)

    def activate_home(self, home):
        # Change a path only; credentials remain opaque and owned by the CLI.
        self.adapter.config = dataclasses.replace(self.adapter.config, cli_home=home)

    def mcp(self, req):
        if isinstance(req, dict) and req.get("jsonrpc") == "2.0" and req.get("method") == "server/discover":
            if "id" not in req:
                return None
            return {"jsonrpc": "2.0", "id": req["id"], "result": {"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}}}
        server = self.server_class(self.adapter)
        server.initialized = True  # This HTTP transport is deliberately stateless.
        reply = server.handle(req)
        if isinstance(req, dict) and req.get("method") == "initialize" and reply and "result" in reply:
            requested = req.get("params", {}).get("protocolVersion")
            if requested == "2026-07-28":
                reply["result"]["protocolVersion"] = requested
        return reply


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "GeminiBridge"
    sys_version = ""

    def log_message(self, *args):
        pass

    def _reply(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def _authorized(self):
        try:
            value = self.headers.get("Authorization", "")
            expected = "Bearer " + self.server.runtime.key
            if len(self.headers.get_all("Authorization", [])) != 1 or len(value) > 512 or not hmac.compare_digest(value, expected):
                self._reply(401, {"error": "UNAUTHORIZED"})
                return False
            return True
        except (TypeError, ValueError):
            self._reply(401, {"error": "UNAUTHORIZED"})
            return False

    def do_GET(self):
        if self.path == "/healthz":
            self._reply(200, {"status": "ok", "service": "gemini-cli-bridge", "model_called": False})
        elif self._authorized():
            self._reply(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        if not self._authorized():
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise RequestError(400, "TRANSFER_ENCODING_UNSUPPORTED")
            length = self.headers.get("Content-Length", "")
            if len(self.headers.get_all("Content-Length", [])) != 1 or not re.fullmatch(r"[0-9]{1,6}", length) or not 0 < int(length) <= MAX_BODY:
                raise RequestError(413, "BODY_SIZE_INVALID")
            if self.headers.get_content_type() != "application/json":
                raise RequestError(415, "JSON_REQUIRED")
            self.connection.settimeout(5)
            payload = json.loads(self.rfile.read(int(length)))
            if not isinstance(payload, dict):
                raise RequestError(400, "OBJECT_REQUIRED")
            rt = self.server.runtime
            if self.path == "/mcp":
                if payload.get("method") == "tools/call" and isinstance(payload.get("params"), dict) and payload["params"].get("name") == "gemini_review":
                    rt.auth._actor(self.headers.get("X-Bridge-Actor"))
                reply = rt.mcp(payload)
                self._reply(200 if reply is not None else 202, reply or {})
                return
            actor = self.headers.get("X-Bridge-Actor")
            if self.path == "/auth/start" and not payload:
                self._reply(200, rt.auth.start(actor))
                return
            if self.path in {"/auth/status", "/auth/finish"}:
                expected = {"session_id"} | ({"authorization_code"} if self.path == "/auth/finish" else set())
                if set(payload) != expected:
                    raise RequestError(400, "INVALID_FIELDS")
                session = rt.auth.get(actor, payload["session_id"])
                result = session.finish(payload["authorization_code"]) if self.path == "/auth/finish" else session.public()
                self._reply(200, result)
                return
            raise RequestError(404, "NOT_FOUND")
        except RequestError as exc:
            self._reply(exc.status, {"error": exc.code})
        except (ValueError, UnicodeError, TimeoutError, OSError):
            self._reply(400, {"error": "INVALID_REQUEST"})
        except Exception:
            self._reply(500, {"error": "INTERNAL_ERROR"})

    def _unsupported(self):
        if self._authorized():
            self._reply(405, {"error": "METHOD_NOT_ALLOWED"})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _unsupported


class HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, *args, **kwargs):
        self._request_slots = threading.BoundedSemaphore(16)
        super().__init__(*args, **kwargs)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address

    def process_request(self, request, client_address):
        if not self._request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


def make_runtime():
    from adapter import Adapter, Config
    from server import Server
    key = os.environ.get("GEMINI_BRIDGE_KEY")
    # Validate before creating state or starting the official CLI.
    if not key or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", key):
        raise ValueError("GEMINI_BRIDGE_KEY is required")
    return Runtime(Adapter(Config.from_env()), Server, key)


def main():
    try:
        runtime = make_runtime()
        port = int(os.environ.get("PORT", "8080"))
        if not 1 <= port <= 65535:
            raise ValueError()
        address = os.environ.get("BIND_HOST", "127.0.0.1")
        server = HTTPServer((address, port), Handler)
        server.runtime = runtime
        def terminate(signum, frame):
            if runtime.auth.session is not None:
                with runtime.auth.session._lock:
                    if runtime.auth.session.state in ACTIVE_STATES:
                        runtime.auth.session.state = "AUTH_SESSION_CANCELLED"
                    runtime.auth.session.stop()
            threading.Thread(target=server.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, terminate)
        signal.signal(signal.SIGINT, terminate)
        try:
            server.serve_forever(poll_interval=0.5)
        finally:
            server.server_close()
    except (ValueError, OSError):
        raise SystemExit("BLOCKED_HTTP_CONFIGURATION") from None


if __name__ == "__main__":
    main()
