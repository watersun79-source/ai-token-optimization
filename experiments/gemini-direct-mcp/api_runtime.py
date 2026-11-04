"""Owner-bound fixed Gemini REST bridge. Import/status perform no network I/O.

Operator evidence is an assertion with private references, not an independent
verification of billing, quota or the API key's Google project. Registration
only verifies access to the fixed model metadata; it never creates free evidence.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import ssl
import stat
import subprocess
import sys
import threading
import time
import uuid

MODEL = "gemini-3.5-flash-lite"
LIMIT = 65536
DEADLINE_SECONDS = 35
HOST = "generativelanguage.googleapis.com"
MODEL_PATH = "/v1beta/models/" + MODEL
REF_FIELDS = {"auth", "project_binding", "free_tier", "billing", "daily_quota"}
PREPARE_FIELDS = {"project_id", "observed_at", "quota_day_pacific", "remaining_requests", "evidence_refs"}
KEY_PATTERN = re.compile(r"(?:[A-Za-z0-9_-]{16,256}|AQ\.[A-Za-z0-9_-]{16,253})\Z")
AQ_SECRET = re.compile(r"AQ\.[A-Za-z0-9_-]{16,}")
PROJECT_PATTERN = re.compile(r"[a-z][a-z0-9-]{4,61}[a-z0-9]\Z")
REF_PATTERN = re.compile(r"private:[A-Za-z0-9._/-]{1,200}\Z")
PASS = "PASS_REAL_GEMINI_API_RESPONSE"
UNVERIFIED = "UNVERIFIED_GEMINI_API_RESULT"
METADATA_AUTHENTICATED = "API_METADATA_AUTHENTICATED"
METADATA_FAILURE_CODES = frozenset("API_METADATA_" + suffix for suffix in (
    "HTTP_UNAUTHENTICATED", "HTTP_FORBIDDEN", "MODEL_NOT_FOUND", "RATE_LIMITED",
    "PROVIDER_UNAVAILABLE", "AUTH_TYPE_UNSUPPORTED", "KEY_INVALID", "SERVICE_DISABLED",
    "KEY_RESTRICTED", "REDIRECT_REJECTED", "TIMEOUT", "TLS_ERROR", "NETWORK_ERROR",
    "INVALID_RESPONSE", "MODEL_MISMATCH", "METHOD_UNAVAILABLE", "WORKER_UNVERIFIED",
))
_ERROR_INFO_REASONS = {
    "ACCESS_TOKEN_TYPE_UNSUPPORTED": "API_METADATA_AUTH_TYPE_UNSUPPORTED",
    "API_KEY_INVALID": "API_METADATA_KEY_INVALID",
    "SERVICE_DISABLED": "API_METADATA_SERVICE_DISABLED",
    **{reason: "API_METADATA_KEY_RESTRICTED" for reason in (
        "API_KEY_SERVICE_BLOCKED", "HTTP_REFERRER_BLOCKED", "IP_ADDRESS_BLOCKED",
        "ANDROID_APP_BLOCKED", "IOS_APP_BLOCKED",
        "API_KEY_HTTP_REFERRER_BLOCKED", "API_KEY_IP_ADDRESS_BLOCKED",
        "API_KEY_ANDROID_APP_BLOCKED", "API_KEY_IOS_APP_BLOCKED",
    )},
}
_CHILDREN = set()
_CHILDREN_LOCK = threading.Lock()
_CANDIDATE = None


class ApiError(Exception):
    """Static public code only. Never pass an upstream exception here."""
    def __init__(self, code, http_status=409, provider_http_status=None):
        self.code, self.http_status = code, http_status
        self.provider_http_status = _public_http_status(provider_http_status)
        super().__init__(code)


class _SavedDigestBinding:
    """Hash-only interface used by the pinned evidence metadata validator.

    This compares two stored registration/evidence digests. It neither reads a
    credential nor proves that the current key-file contents remain unchanged.
    Actual review rechecks the saved registration against the real private key.
    """
    __slots__ = ("api_key_sha256",)
    def __init__(self, digest):
        self.api_key_sha256 = digest


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _public_http_status(value):
    return value if type(value) is int and 100 <= value <= 599 else None


def metadata_failure(code="API_METADATA_WORKER_UNVERIFIED", provider_http_status=None):
    if type(code) is not str or code not in METADATA_FAILURE_CODES:
        code = "API_METADATA_WORKER_UNVERIFIED"
    return {"status": code, "provider_http_status": _public_http_status(provider_http_status)}


def sanitize_metadata_result(value):
    if value == {"status": METADATA_AUTHENTICATED}:
        return {"status": METADATA_AUTHENTICATED}
    if not isinstance(value, dict): return metadata_failure()
    return metadata_failure(value.get("status"), value.get("provider_http_status"))


def candidate_module():
    global _CANDIDATE
    if _CANDIDATE is None:
        paths = [Path(__file__).resolve().with_name("gemini_direct.py"),
                 Path(__file__).resolve().parent.parent / "gemini-api-candidate" / "gemini_direct.py"]
        path = next((p for p in paths if p.is_file() and not p.is_symlink()), None)
        if path is None:
            raise ApiError("BLOCKED_API_CANDIDATE_UNAVAILABLE", 503)
        spec = importlib.util.spec_from_file_location("_fixed_gemini_direct_candidate", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        if module.MODEL != MODEL:
            raise ApiError("BLOCKED_API_MODEL_MISMATCH", 503)
        _CANDIDATE = module
    return _CANDIDATE


def _kill(process):
    if os.name == "posix" or process.poll() is None:
        try:
            if os.name == "posix": os.killpg(process.pid, signal.SIGKILL)
            else: process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try: process.kill()
        except OSError: pass
        process.wait(timeout=1)


def stop_children():
    with _CHILDREN_LOCK:
        children = tuple(_CHILDREN)
    for process in children:
        _kill(process)


def run_child(payload, *, command=None, deadline=DEADLINE_SECONDS):
    """One private-pipe process; a hard host deadline also bounds slow DNS/TLS.

    command/deadline are internal process-double seams, never HTTP/MCP arguments.
    No key, prompt or evidence is placed in argv, environment or a temporary file.
    """
    is_metadata = isinstance(payload, dict) and payload.get("operation") == "metadata"
    def unavailable(code="API_METADATA_WORKER_UNVERIFIED"):
        return metadata_failure(code) if is_metadata else {"status": UNVERIFIED}
    if not 0 < deadline <= DEADLINE_SECONDS:
        return unavailable()
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    if len(data) > LIMIT:
        return unavailable()
    env = {k: os.environ[k] for k in ("LANG", "LC_ALL", "TZ") if k in os.environ}
    process = None
    reader = writer = None
    collected = bytearray()
    overflow = threading.Event()
    expires = time.monotonic() + deadline
    try:
        process = subprocess.Popen(command or [sys.executable, "-I", str(Path(__file__).resolve()), "--worker"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   env=env, shell=False, start_new_session=(os.name == "posix"),
                                   cwd=Path(__file__).resolve().parent, close_fds=True)
        with _CHILDREN_LOCK:
            _CHILDREN.add(process)
        def read():
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk: return
                    if len(collected) + len(chunk) > LIMIT:
                        overflow.set()
                        return
                    collected.extend(chunk)
            except (OSError, ValueError):
                overflow.set()
        def write():
            try:
                process.stdin.write(data)
                process.stdin.close()
            except (OSError, ValueError):
                pass
        reader = threading.Thread(target=read, daemon=True)
        writer = threading.Thread(target=write, daemon=True)
        reader.start()
        writer.start()
        while process.poll() is None:
            remaining = expires - time.monotonic()
            if remaining <= 0:
                return unavailable("API_METADATA_TIMEOUT")
            if overflow.wait(min(0.01, max(0, remaining))):
                return unavailable()
        reader.join(timeout=max(0, expires - time.monotonic()))
        if time.monotonic() > expires:
            return unavailable("API_METADATA_TIMEOUT")
        if reader.is_alive() or overflow.is_set() or process.returncode != 0:
            return unavailable()
        value = json.loads(collected)
        return value if isinstance(value, dict) else unavailable()
    except Exception:
        return unavailable()
    finally:
        if process is not None:
            _kill(process)
            with _CHILDREN_LOCK:
                _CHILDREN.discard(process)
            for pipe in (process.stdin, process.stdout):
                try: pipe.close()
                except (OSError, ValueError): pass
        for thread in (reader, writer):
            if thread is not None: thread.join(timeout=0.1)


def _tls_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    return context


def metadata_once(api_key):
    """One fixed model GET; no generation, redirects, proxies, retries or logs."""
    connection = None
    result = metadata_failure("API_METADATA_INVALID_RESPONSE")
    provider_status = None
    try:
        if type(api_key) is not str or not KEY_PATTERN.fullmatch(api_key):
            return result
        connection = http.client.HTTPSConnection(HOST, port=443, timeout=30, context=_tls_context())
        connection.set_debuglevel(0)
        connection.request("GET", MODEL_PATH, headers={"x-goog-api-key": api_key,
                           "Accept": "application/json", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        provider_status = _public_http_status(response.status)
        code = {401: "API_METADATA_HTTP_UNAUTHENTICATED", 403: "API_METADATA_HTTP_FORBIDDEN",
                404: "API_METADATA_MODEL_NOT_FOUND", 429: "API_METADATA_RATE_LIMITED"}.get(provider_status)
        if provider_status is not None and 300 <= provider_status <= 399:
            code = "API_METADATA_REDIRECT_REJECTED"
        elif provider_status is not None and 500 <= provider_status <= 599:
            code = "API_METADATA_PROVIDER_UNAVAILABLE"
        result = metadata_failure(code or "API_METADATA_INVALID_RESPONSE", provider_status)
        if response.getheader("content-encoding", "identity").lower() != "identity":
            return result
        length = response.getheader("content-length")
        if length is not None and (not length.isdecimal() or int(length) > LIMIT):
            return result
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            return result
        try: body = json.loads(raw)
        except (ValueError, UnicodeError): return result
        if provider_status != 200:
            # Only the fixed ErrorInfo type/reason is selected. Never copy its
            # message, metadata, account/project values, raw body or headers.
            if code != "API_METADATA_REDIRECT_REJECTED" and isinstance(body, dict):
                error = body.get("error")
                details = error.get("details") if isinstance(error, dict) else None
                if isinstance(details, list):
                    for detail in details:
                        if (isinstance(detail, dict) and detail.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo"
                                and detail.get("domain") in {"googleapis.com", "generativelanguage.googleapis.com"}
                                and type(detail.get("reason")) is str and detail["reason"] in _ERROR_INFO_REASONS):
                            result = metadata_failure(_ERROR_INFO_REASONS[detail["reason"]], provider_status)
                            break
            return result
        if not isinstance(body, dict) or not isinstance(body.get("name"), str):
            return result
        if body["name"] != "models/" + MODEL:
            return metadata_failure("API_METADATA_MODEL_MISMATCH", provider_status)
        methods = body.get("supportedGenerationMethods")
        if not isinstance(methods, list) or "generateContent" not in methods:
            return metadata_failure("API_METADATA_METHOD_UNAVAILABLE", provider_status)
        result = {"status": METADATA_AUTHENTICATED}
    except TimeoutError:
        result = metadata_failure("API_METADATA_TIMEOUT", provider_status)
    except ssl.SSLError:
        result = metadata_failure("API_METADATA_TLS_ERROR", provider_status)
    except OSError:
        result = metadata_failure("API_METADATA_NETWORK_ERROR", provider_status)
    except Exception:
        pass
    finally:
        if connection is not None:
            try: connection.close()
            except Exception: result = metadata_failure("API_METADATA_NETWORK_ERROR", provider_status)
    return result


def worker_dispatch(payload):
    if not isinstance(payload, dict):
        return {"status": UNVERIFIED}
    if payload.get("operation") == "metadata" and set(payload) == {"operation", "api_key"}:
        return metadata_once(payload["api_key"])
    if payload.get("operation") != "generate" or set(payload) != {"operation", "api_key", "prompt", "evidence"}:
        return {"status": UNVERIFIED}
    candidate = candidate_module()
    # Only the host sends this payload after its owner/evidence/durable claim.
    config = candidate.Config(api_key=payload["api_key"], enabled=True)
    evidence = candidate.OperatorEvidence.from_mapping(payload["evidence"])
    result = candidate.GeminiDirectClient(config).generate_once(payload["prompt"], evidence=evidence)
    if not isinstance(result, candidate.TextResult) or not result.complete:
        return {"status": UNVERIFIED}
    return {"status": PASS, "response": result.text, "model": result.model,
            "finish_reason": result.finish_reason, "usage": result.usage}


class ApiRuntime:
    def __init__(self, adapter, owner, *, allowed_project_id=None, runner=run_child):
        self.adapter, self.owner, self.runner = adapter, owner, runner
        project = allowed_project_id if allowed_project_id is not None else os.environ.get("GEMINI_API_ALLOWED_PROJECT_ID")
        self.allowed_project_id = project if isinstance(project, str) and PROJECT_PATTERN.fullmatch(project) else None
        self.lock = threading.RLock()
        self.root = adapter.config.state_dir / "free-api"
        if self.root.is_symlink(): raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        self.key_path = self.root / "api-key"
        self.db_path = adapter.config.state_dir / "requests.sqlite3"
        if self.db_path.is_symlink(): raise ApiError("BLOCKED_UNSAFE_API_LEDGER", 503)
        if self.db_path.exists():
            info = self.db_path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ApiError("BLOCKED_UNSAFE_API_LEDGER", 503)
        else:
            fd = os.open(self.db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        with self._db() as db:
            # Existing adapter tables and columns, shared atomic concurrency budget.
            db.execute("CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, prompt_sha TEXT NOT NULL, state TEXT NOT NULL, result_json TEXT, created_at REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS consumed_gates (gate_id TEXT PRIMARY KEY, request_id TEXT NOT NULL)")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db: yield db
        finally:
            db.close()

    def _dirfd(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            os.close(fd)
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        return fd

    def _read(self, name):
        directory = self._dirfd()
        try:
            try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError: return None
            with os.fdopen(fd, "rb") as file:
                info = os.fstat(file.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size > LIMIT):
                    raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
                value = file.read(LIMIT + 1)
                if len(value) > LIMIT: raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
                return value
        except OSError:
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503) from None
        finally:
            os.close(directory)

    def _write(self, name, value, *, replace=True):
        if len(value) > LIMIT: raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        if replace: self._read(name)  # Reject an existing symlink/unsafe file.
        directory = self._dirfd()
        temporary = "pending-" + secrets.token_hex(16)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(fd, "wb") as file:
                file.write(value)
                file.flush()
                os.fsync(file.fileno())
            if replace:
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            else:
                os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
                os.unlink(temporary, dir_fd=directory)
            os.fsync(directory)
        except OSError:
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503) from None
        finally:
            try: os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError: pass
            os.close(directory)

    def _json(self, name):
        value = self._read(name)
        if value is None: return None
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict): return parsed
        except (ValueError, UnicodeError): pass
        raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)

    def _save_json(self, name, value):
        self._write(name, json.dumps(value, separators=(",", ":")).encode())

    def _project(self):
        if self.allowed_project_id is None:
            raise ApiError("BLOCKED_API_PROJECT_NOT_CONFIGURED", 503)
        return self.allowed_project_id

    def _key(self):
        value = self._read("api-key")
        if value is None: raise ApiError("BLOCKED_API_KEY_MISSING", 409)
        try: key = value.decode("ascii")
        except UnicodeError: raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503) from None
        if not KEY_PATTERN.fullmatch(key): raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        return key

    def _key_present(self):
        # Open+fstat only: do not read any byte from the private key file.
        directory = self._dirfd()
        fd = None
        try:
            try: fd = os.open("api-key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError: return False
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or not 16 <= info.st_size <= 256):
                raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
            return True
        except OSError:
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503) from None
        finally:
            if fd is not None: os.close(fd)
            os.close(directory)

    def _auth_metadata(self, expected_digest=None):
        value = self._json("api-auth.json")
        if (not value or set(value) != {"owner", "project_id", "api_key_sha256", "auth_verified_at"}
                or value.get("owner") != self.owner.actor or value.get("project_id") != self._project()
                or type(value.get("api_key_sha256")) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", value["api_key_sha256"])
                or (expected_digest is not None and not hmac.compare_digest(value["api_key_sha256"], expected_digest))
                or not isinstance(value.get("auth_verified_at"), str) or len(value["auth_verified_at"]) > 40):
            raise ApiError("BLOCKED_API_KEY_AUTH_UNVERIFIED", 409)
        try:
            stamp = datetime.fromisoformat(value["auth_verified_at"])
            if stamp.tzinfo is None: raise ValueError()
            value["auth_verified_at"] = stamp.astimezone(timezone.utc).isoformat()
        except ValueError:
            raise ApiError("BLOCKED_API_KEY_AUTH_UNVERIFIED", 409) from None
        return value

    def _auth(self, key):
        return self._auth_metadata(hashlib.sha256(key.encode()).hexdigest())

    def register(self, actor, api_key):
        self._project()
        if type(api_key) is not str or not KEY_PATTERN.fullmatch(api_key):
            raise ApiError("INVALID_API_KEY_FORMAT", 400)
        self.owner.require(actor, bind=True)
        with self.lock:
            existing = self._read("api-key")
            auth = None
            if existing is not None:
                if not hmac.compare_digest(existing, api_key.encode("ascii")):
                    raise ApiError("API_KEY_REPLACEMENT_REQUIRES_EXPLICIT_APPROVAL", 409)
                if self._json("api-auth.json") is not None:
                    auth = self._auth(api_key)
            if auth is None:
                try: result = sanitize_metadata_result(self.runner({"operation": "metadata", "api_key": api_key}))
                except Exception: result = metadata_failure()
                if result != {"status": METADATA_AUTHENTICATED}:
                    self._save_json("api-registration.json", {"result": "FAILED", "code": result["status"],
                                    "provider_http_status": result["provider_http_status"], "observed_at": utc_now()})
                    raise ApiError(result["status"], 502, result["provider_http_status"])
                auth = {"owner": actor, "project_id": self._project(),
                        "api_key_sha256": hashlib.sha256(api_key.encode()).hexdigest(), "auth_verified_at": utc_now()}
                if existing is None:
                    self._write("api-key", api_key.encode("ascii"), replace=False)
                self._save_json("api-auth.json", auth)
                self._save_json("api-registration.json", {"result": "SUCCEEDED", "code": METADATA_AUTHENTICATED,
                                "provider_http_status": 200, "observed_at": utc_now()})
            return {"status": "API_KEY_AUTHENTICATED_FREE_EVIDENCE_REQUIRED", "configured": True,
                    "auth_verified_at": auth["auth_verified_at"], "model": MODEL, "model_called": False}

    def _last_registration(self):
        record = self._json("api-registration.json")
        if record is None: return None
        valid = (set(record) == {"result", "code", "provider_http_status", "observed_at"}
                 and type(record.get("observed_at")) is str and len(record["observed_at"]) <= 40
                 and type(record.get("code")) is str
                 and (record.get("provider_http_status") is None or _public_http_status(record["provider_http_status"]) is not None))
        success = (record.get("result") == "SUCCEEDED" and record.get("code") == METADATA_AUTHENTICATED
                   and type(record.get("provider_http_status")) is int and record["provider_http_status"] == 200)
        failure = record.get("result") == "FAILED" and type(record.get("code")) is str and record["code"] in METADATA_FAILURE_CODES
        if not valid or not (success or failure): raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503)
        try:
            stamp = datetime.fromisoformat(record["observed_at"])
            if stamp.tzinfo is None: raise ValueError()
            stamp = stamp.astimezone(timezone.utc).isoformat()
        except (ValueError, OverflowError):
            raise ApiError("BLOCKED_UNSAFE_API_STORAGE", 503) from None
        return {"result": record["result"], "code": record["code"],
                "provider_http_status": record["provider_http_status"], "observed_at": stamp}

    def _evidence(self, key):
        return self._evidence_for_digest(hashlib.sha256(key.encode()).hexdigest())

    def _evidence_for_digest(self, digest):
        record = self._json("operator-evidence.json")
        if record is None: raise ApiError("BLOCKED_API_FREE_EVIDENCE_MISSING")
        if record.get("owner") != self.owner.actor or record.get("project_id") != self._project():
            raise ApiError("BLOCKED_API_FREE_EVIDENCE_INVALID")
        candidate = candidate_module()
        try:
            evidence = candidate.OperatorEvidence.from_mapping(record["candidate"])
            evidence._validate(_SavedDigestBinding(digest), datetime.now(timezone.utc))
        except Exception:
            raise ApiError("BLOCKED_API_FREE_EVIDENCE_EXPIRED") from None
        return record["candidate"]

    @staticmethod
    def _gate_id(evidence): return "api:" + evidence["evidence_id"]

    def _consumed(self, evidence):
        with self._db() as db:
            return bool(db.execute("SELECT 1 FROM consumed_gates WHERE gate_id=?", (self._gate_id(evidence),)).fetchone())

    def prepare(self, actor, args):
        self.owner.require(actor)
        if not isinstance(args, dict) or set(args) != PREPARE_FIELDS:
            raise ApiError("INVALID_API_EVIDENCE_FIELDS", 400)
        if args["project_id"] != self._project(): raise ApiError("BLOCKED_API_PROJECT_MISMATCH", 403)
        remaining = args["remaining_requests"]
        refs = args["evidence_refs"]
        if type(remaining) is not int or not 1 <= remaining <= 1000000:
            raise ApiError("INVALID_API_REMAINING_REQUESTS", 400)
        if (not isinstance(refs, dict) or set(refs) != REF_FIELDS
                or any(type(v) is not str or not REF_PATTERN.fullmatch(v) or AQ_SECRET.search(v) for v in refs.values())):
            raise ApiError("INVALID_PRIVATE_API_EVIDENCE_REFS", 400)
        with self.lock:
            key = self._key()
            self._auth(key)
            digest = hashlib.sha256(key.encode()).hexdigest()
            # The same private source revisions cannot mint another budget by
            # changing a timestamp or claimed remaining-count value.
            canonical = json.dumps({"actor": actor, "api_key_sha256": digest, "project_id": self._project(),
                                    "model": MODEL, "quota_day_pacific": args["quota_day_pacific"],
                                    "evidence_refs": refs}, sort_keys=True, separators=(",", ":"))
            evidence = {"schema_version": 1, "status": "VERIFIED_BY_OPERATOR",
                        "evidence_id": str(uuid.uuid5(uuid.NAMESPACE_URL, canonical)),
                        "api_key_sha256": digest, "model": MODEL, "observed_at": args["observed_at"],
                        "quota_day_pacific": args["quota_day_pacific"], "remaining_requests": remaining,
                        "evidence_refs": dict(refs), "billing_account_linked": False, "paid_billing_enabled": False,
                        "auth_verified": True, "key_project_binding_verified": True,
                        "free_tier_verified": True, "quota_verified": True}
            candidate = candidate_module()
            try:
                candidate.OperatorEvidence.from_mapping(evidence)._validate(candidate.Config(api_key=key), datetime.now(timezone.utc))
            except Exception:
                raise ApiError("BLOCKED_API_FREE_EVIDENCE_INVALID", 400) from None
            if self._consumed(evidence): raise ApiError("BLOCKED_API_EVIDENCE_BUDGET_CONSUMED")
            with self._db() as db:
                if db.execute("SELECT 1 FROM requests WHERE state='running' LIMIT 1").fetchone():
                    raise ApiError("BLOCKED_API_REQUEST_PENDING_OR_UNCERTAIN")
            self._save_json("operator-evidence.json", {"owner": actor, "project_id": self._project(), "candidate": evidence})
            return {"status": "OPERATOR_EVIDENCE_PRESENT", "model": MODEL, "generation_ready": True,
                    "independently_verified_by_tool": False, "automatic_retry": False}

    def _existing(self, request_id, prompt_sha):
        with self._db() as db:
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if row is None: return None
        if row["prompt_sha"] != prompt_sha: raise ApiError("BLOCKED_REQUEST_ID_CONFLICT")
        if row["state"] != "done": raise ApiError("BLOCKED_API_REQUEST_PENDING_OR_UNCERTAIN")
        try:
            result = json.loads(row["result_json"])
            if result.get("status") in {PASS, UNVERIFIED}: return result
        except (ValueError, TypeError, AttributeError): pass
        raise ApiError("BLOCKED_API_LEDGER_RESULT_INVALID")

    def _claim(self, request_id, prompt_sha, evidence):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row is not None:
                raise ApiError("BLOCKED_API_REQUEST_PENDING_OR_UNCERTAIN")
            if db.execute("SELECT 1 FROM requests WHERE state='running' LIMIT 1").fetchone():
                raise ApiError("BLOCKED_API_REQUEST_PENDING_OR_UNCERTAIN")
            if db.execute("SELECT 1 FROM consumed_gates WHERE gate_id=?", (self._gate_id(evidence),)).fetchone():
                raise ApiError("BLOCKED_API_EVIDENCE_BUDGET_CONSUMED")
            db.execute("INSERT INTO consumed_gates VALUES (?,?)", (self._gate_id(evidence), request_id))
            db.execute("INSERT INTO requests VALUES (?,?,'running',NULL,?)", (request_id, prompt_sha, time.time()))

    def review(self, actor, request_id, prompt):
        self.owner.require(actor)
        from adapter import Adapter, Blocked, SECRET
        try: Adapter._validate(request_id, prompt)
        except Blocked as error: raise ApiError(error.code, 400) from None
        request_id = hashlib.sha256(("gemini-api-v1\0" + actor + "\0" + request_id).encode()).hexdigest()
        prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
        previous = self._existing(request_id, prompt_sha)
        if previous is not None: return previous
        with self.lock:
            self._project()
            key = self._key()
            self._auth(key)
            evidence = self._evidence(key)
            self._claim(request_id, prompt_sha, evidence)
        result = {"status": UNVERIFIED, "request_id": request_id, "response": None,
                  "model": MODEL, "provider_completion": "UNVERIFIED", "automatic_retry": False}
        try:
            output = self.runner({"operation": "generate", "api_key": key, "prompt": prompt, "evidence": evidence})
            response = output.get("response")
            usage = output.get("usage")
            if (set(output) == {"status", "response", "model", "finish_reason", "usage"}
                    and output["status"] == PASS and output["model"] == MODEL and output["finish_reason"] == "STOP"
                    and isinstance(response, str) and response and len(response.encode()) <= 12000
                    and not any(ord(char) < 32 and char not in "\n\t" for char in response)
                    and key not in response and not SECRET.search(response) and isinstance(usage, dict)
                    and set(usage) <= {"promptTokenCount", "candidatesTokenCount", "totalTokenCount", "thoughtsTokenCount", "cachedContentTokenCount"}
                    and all(type(count) is int and count >= 0 for count in usage.values())):
                result.update(status=PASS, response=response, provider_completion="VERIFIED", finish_reason="STOP", usage=usage)
        except Exception:
            pass
        with self._db() as db:
            db.execute("UPDATE requests SET state='done',result_json=? WHERE request_id=?", (json.dumps(result), request_id))
        with self.lock:
            last = self._json("api-last-result.json") or {}
            self._save_json("api-last-result.json", {"last_result_status": result["status"],
                            "last_response_at": utc_now() if result["status"] == PASS else last.get("last_response_at")})
        return result

    def status(self):
        result = {"status": "API_KEY_NOT_CONFIGURED", "configured": False, "auth_verified_at": None,
                  "model": MODEL, "project_id": None, "free_evidence_status": "MISSING", "generation_ready": False,
                  "last_response_at": None, "last_result_status": None, "last_registration": None}
        # Only local private metadata/ledger reads; no worker, auth, GET or model call.
        with self.lock:
            try:
                result["last_registration"] = self._last_registration()
                last = self._json("api-last-result.json")
                if last and last.get("last_result_status") in {PASS, UNVERIFIED}:
                    result["last_result_status"] = last["last_result_status"]
                    result["last_response_at"] = last.get("last_response_at")
                result["configured"] = self._key_present()
                result["project_id"] = self._project()
                if not result["configured"]:
                    raise ApiError("BLOCKED_API_KEY_MISSING")
                auth = self._auth_metadata()
                result["auth_verified_at"] = auth["auth_verified_at"]
                evidence = self._evidence_for_digest(auth["api_key_sha256"])
                if self._consumed(evidence):
                    result.update(status="API_FREE_EVIDENCE_CONSUMED", free_evidence_status="CONSUMED")
                else:
                    with self._db() as db:
                        pending = bool(db.execute("SELECT 1 FROM requests WHERE state='running' LIMIT 1").fetchone())
                    result.update(status="API_REQUEST_PENDING_OR_UNCERTAIN" if pending else "READY_FOR_ONE_VERIFIED_FREE_API_ATTEMPT",
                                  free_evidence_status="OPERATOR_EVIDENCE_PRESENT", generation_ready=not pending)
            except ApiError as error:
                states = {"BLOCKED_API_KEY_MISSING": "API_KEY_NOT_CONFIGURED",
                          "BLOCKED_API_KEY_AUTH_UNVERIFIED": "API_KEY_AUTH_UNVERIFIED",
                          "BLOCKED_API_FREE_EVIDENCE_MISSING": "API_FREE_EVIDENCE_MISSING",
                          "BLOCKED_API_FREE_EVIDENCE_INVALID": "API_FREE_EVIDENCE_EXPIRED",
                          "BLOCKED_API_FREE_EVIDENCE_EXPIRED": "API_FREE_EVIDENCE_EXPIRED"}
                result["status"] = states.get(error.code, "BLOCKED_API_PROJECT_NOT_CONFIGURED" if error.code == "BLOCKED_API_PROJECT_NOT_CONFIGURED" else "BLOCKED_API_STORAGE")
                if result["status"] == "BLOCKED_API_STORAGE":
                    result.update(auth_verified_at=None, last_response_at=None, last_result_status=None, generation_ready=False)
                if error.code in {"BLOCKED_API_FREE_EVIDENCE_EXPIRED", "BLOCKED_API_FREE_EVIDENCE_INVALID"}:
                    result["free_evidence_status"] = "EXPIRED"
        return result


def _worker_main():
    # Linux parent-death protection supplements the host deadline/SIGTERM cleanup.
    try:
        import ctypes
        if not sys.platform.startswith("linux") or ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() == 1:
            return {"status": UNVERIFIED}
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT: return {"status": UNVERIFIED}
        return worker_dispatch(json.loads(raw))
    except BaseException:
        return {"status": UNVERIFIED}


if __name__ == "__main__":
    value = _worker_main() if sys.argv == [__file__, "--worker"] else {"status": UNVERIFIED}
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
