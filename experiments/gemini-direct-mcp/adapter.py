"""Real, bounded Gemini CLI execution. No credential parsing or model mocks."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import signal
import shutil
import sqlite3
import stat
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent
EXPECTED_VERSION = "0.66.0"
PROVIDER_ENV = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA",
    "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION",
)
SECRET = re.compile(
    r"AIza[\w-]{20,}|sk-[\w-]{20,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|"
    r"(?:access_token|refresh_token|authorization_code)\s*[=:]\s*[\"']?[A-Za-z0-9_./+\-]{16,}", re.I
)
DENY_POLICY = '[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n'
# Public, noncredential controls. Install this exact object as a root-owned
# system settings file during image build, before switching to the runtime user.
CLI_SYSTEM_SETTINGS = {
    "model": {"maxSessionTurns": 1},
    "experimental": {"autoMemory": False},
    "security": {"auth": {"selectedType": "oauth-personal"}},
    "hooksConfig": {"enabled": False},
    "telemetry": {"enabled": False},
}


class Blocked(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Config:
    cli: Path | None
    state_dir: Path
    cli_home: Path
    gate_file: Path | None = None
    timeout_seconds: float = 60.0
    max_output_bytes: int = 1_048_576
    system_settings_file: Path = Path("/etc/gemini-cli/settings.json")

    @classmethod
    def from_env(cls):
        state = Path(os.environ.get("GEMINI_MCP_STATE_DIR", str(ROOT / "state"))).resolve()
        cli = os.environ.get("GEMINI_CLI_PATH") or shutil.which("gemini")
        return cls(
            cli=Path(cli).absolute() if cli else None,
            state_dir=state,
            cli_home=Path(os.environ.get("GEMINI_CLI_HOME", str(state / "cli-home"))).resolve(),
            gate_file=Path(os.environ["GEMINI_MCP_VERIFIED_GATE"]).absolute()
            if os.environ.get("GEMINI_MCP_VERIFIED_GATE") else None,
        )


def utc_seconds(value):
    if not isinstance(value, str):
        raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError()
        return d.timestamp()
    except (ValueError, OverflowError):
        raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE") from None


def private_dir(path: Path):
    if path.is_symlink():
        raise Blocked("BLOCKED_UNSAFE_STATE_DIRECTORY")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        st = path.stat()
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise Blocked("BLOCKED_UNSAFE_STATE_DIRECTORY")


class Adapter:
    def __init__(self, config: Config):
        self.config = config
        if (config.cli is not None and not config.cli.is_absolute()) or not (0 < config.timeout_seconds <= 120):
            raise Blocked("BLOCKED_INVALID_CONFIGURATION")
        private_dir(config.state_dir)
        private_dir(config.cli_home)
        self.work = config.state_dir / "empty-work"
        private_dir(self.work)
        self.policy = config.state_dir / "deny-all-tools.toml"
        if self.policy.is_symlink():
            raise Blocked("BLOCKED_UNSAFE_POLICY_FILE")
        if self.policy.exists() and self.policy.read_text() != DENY_POLICY:
            raise Blocked("BLOCKED_POLICY_CHANGED")
        if not self.policy.exists():
            fd = os.open(self.policy, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(DENY_POLICY)
        self.db_path = config.state_dir / "requests.sqlite3"
        if self.db_path.is_symlink():
            raise Blocked("BLOCKED_UNSAFE_LEDGER")
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, prompt_sha TEXT NOT NULL, state TEXT NOT NULL, result_json TEXT, created_at REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS consumed_gates (gate_id TEXT PRIMARY KEY, request_id TEXT NOT NULL)")
        if os.name == "posix":
            os.chmod(self.db_path, 0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _env(self):
        if any(os.environ.get(k) for k in PROVIDER_ENV):
            raise Blocked("BLOCKED_PROVIDER_KEY_OR_VERTEX_ENV")
        # No arbitrary application credentials, Node injection or proxy secrets.
        keep = ("PATH", "HOME", "USERPROFILE", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "LANG", "LC_ALL", "TZ")
        env = {k: os.environ[k] for k in keep if k in os.environ}
        env.update({"GEMINI_CLI_HOME": str(self.config.cli_home), "GEMINI_TELEMETRY_ENABLED": "false", "NO_BROWSER": "true", "CI": "true", "TERM": "dumb",
                    "GEMINI_CLI_SYSTEM_SETTINGS_PATH": str(self.config.system_settings_file)})
        return env

    @staticmethod
    def _root_control_path_is_secure(path):
        # Gemini CLI 0.66.0 skips system settings unless the file and every
        # ancestor are root-owned and cannot be changed by group/other users.
        if os.name != "posix" or not path.is_absolute():
            return False
        try:
            for item in (path, *path.parents):
                st = item.lstat()
                if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
                    return False
                if item == path and not stat.S_ISREG(st.st_mode):
                    return False
                if item != path and not stat.S_ISDIR(st.st_mode):
                    return False
            return True
        except OSError:
            return False

    def _system_controls(self):
        path = self.config.system_settings_file
        if not path.is_file():
            raise Blocked("BLOCKED_SYSTEM_CONTROLS_MISSING")
        if not self._root_control_path_is_secure(path):
            raise Blocked("BLOCKED_UNSAFE_SYSTEM_CONTROLS")
        try:
            if path.stat().st_size > 16_384 or json.loads(path.read_text()) != CLI_SYSTEM_SETTINGS:
                raise Blocked("BLOCKED_SYSTEM_CONTROLS_CHANGED")
        except (OSError, ValueError, UnicodeError):
            raise Blocked("BLOCKED_SYSTEM_CONTROLS_CHANGED") from None
        return {"status": "PASS", "max_session_turns": 1,
                "settings_path": str(path), "provider_request_count": "UNVERIFIED"}

    @staticmethod
    def _stop(process):
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            try:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, shell=False)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def _run(self, args, payload=b"", timeout=None, output_limit=None):
        env = self._env()
        if self.config.cli is None or not self.config.cli.is_file() or not os.access(self.config.cli, os.X_OK):
            raise Blocked("BLOCKED_CLI_UNAVAILABLE")
        limit = output_limit or self.config.max_output_bytes
        try:
            p = subprocess.Popen([str(self.config.cli), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=self.work, env=env, shell=False, start_new_session=(os.name == "posix"))
        except OSError:
            raise Blocked("BLOCKED_CLI_START_FAILED") from None
        collected = bytearray()
        overflow = threading.Event()

        def read():
            try:
                while True:
                    chunk = p.stdout.read(8192)
                    if not chunk:
                        return
                    if len(collected) + len(chunk) > limit:
                        overflow.set()
                        return
                    collected.extend(chunk)
            except (OSError, ValueError):
                return

        def write():
            try:
                p.stdin.write(payload)
                p.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                return

        reader = threading.Thread(target=read, daemon=True)
        writer = threading.Thread(target=write, daemon=True)
        reader.start()
        writer.start()
        deadline = time.monotonic() + (timeout or self.config.timeout_seconds)
        try:
            while p.poll() is None:
                if overflow.is_set():
                    self._stop(p)
                    raise Blocked("BLOCKED_CLI_OUTPUT_LIMIT")
                left = deadline - time.monotonic()
                if left <= 0:
                    self._stop(p)
                    raise Blocked("BLOCKED_CLI_TIMEOUT")
                try:
                    p.wait(timeout=min(0.05, left))
                except subprocess.TimeoutExpired:
                    pass
            reader.join(timeout=2)
            writer.join(timeout=2)
            if reader.is_alive():
                self._stop(p)
                raise Blocked("BLOCKED_CLI_OUTPUT_PIPE_NOT_CLOSED")
            if overflow.is_set():
                raise Blocked("BLOCKED_CLI_OUTPUT_LIMIT")
            if p.returncode != 0:
                raise Blocked("BLOCKED_CLI_EXIT_NONZERO")
            try:
                return bytes(collected).decode("utf-8")
            except UnicodeDecodeError:
                raise Blocked("BLOCKED_CLI_INVALID_UTF8") from None
        finally:
            if p.poll() is None:
                self._stop(p)
            for pipe in (p.stdin, p.stdout):
                try:
                    pipe.close()
                except (OSError, ValueError):
                    pass

    def version(self):
        value = self._run(["--version"], timeout=15, output_limit=4096).strip()
        if value != EXPECTED_VERSION:
            raise Blocked("BLOCKED_CLI_VERSION_MISMATCH")
        return value

    def help(self):
        value = self._run(["--help"], timeout=15, output_limit=32768)
        for option in ("--prompt", "--output-format", "--policy", "--approval-mode"):
            if option not in value:
                raise Blocked("BLOCKED_CLI_OPTIONS_UNVERIFIED")
        return {"status": "PASS_HELP_FLAGS", "unsupported_status_flag": "--status" not in value}

    def _gate(self):
        path = self.config.gate_file
        if path is None or not path.is_file():
            raise Blocked("BLOCKED_VERIFICATION_GATE_MISSING")
        if path.is_symlink():
            raise Blocked("BLOCKED_UNSAFE_VERIFICATION_GATE")
        st = path.stat()
        if st.st_size > 16384 or (os.name == "posix" and (st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077)):
            raise Blocked("BLOCKED_UNSAFE_VERIFICATION_GATE")
        try:
            gate = json.loads(path.read_text())
        except (OSError, ValueError, UnicodeError):
            raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE") from None
        if not isinstance(gate, dict):
            raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE")
        auth, quota = gate.get("auth"), gate.get("quota")
        if not isinstance(auth, dict) or not isinstance(quota, dict):
            raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE")
        if (gate.get("schema") != "GEMINI_CLI_VERIFIED_GATE_V2" or gate.get("cli_version") != EXPECTED_VERSION
                or self.config.cli is None or gate.get("cli_realpath") != str(self.config.cli.resolve())
                or gate.get("cli_home") != str(self.config.cli_home)
                or gate.get("isolated_cli_configuration_reviewed") is not True
                or "max_model_calls" in gate
                or type(gate.get("max_cli_invocations")) is not int or gate.get("max_cli_invocations") != 1
                or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", str(gate.get("gate_id", "")))):
            raise Blocked("BLOCKED_INVALID_VERIFICATION_GATE")
        if auth.get("status") != "PASS" or auth.get("method") != "oauth-personal" or auth.get("source_kind") != "official-cli-runtime-verification" or not auth.get("evidence_ref"):
            raise Blocked("BLOCKED_CLI_AUTH_UNVERIFIED")
        if (quota.get("status") != "PASS" or quota.get("source_kind") != "gemini-cli-provider-quota"
                or quota.get("route") != "code-assist-personal" or quota.get("free") is not True
                or quota.get("paid_billing_enabled") is not False or not quota.get("evidence_ref")
                or type(quota.get("remaining_requests")) is not int or quota["remaining_requests"] < 1):
            raise Blocked("BLOCKED_CLI_FREE_QUOTA_UNVERIFIED")
        now = time.time()
        stamps = [utc_seconds(auth.get("verified_at")), utc_seconds(quota.get("verified_at"))]
        expires = utc_seconds(gate.get("expires_at"))
        if any(t > now + 5 or now - t > 900 for t in stamps) or not (now < expires <= min(stamps) + 900):
            raise Blocked("BLOCKED_VERIFICATION_GATE_EXPIRED")
        return gate

    def status(self):
        try:
            runtime = {"status": "PASS", "version": self.version()}
        except Blocked as exc:
            runtime = {"status": exc.code, "version": None}
        try:
            gate = self._gate()
            gate_state = {"status": "LOCAL_OPERATOR_EVIDENCE_PRESENT", "gate_id": gate["gate_id"]}
        except Blocked as exc:
            gate_state = {"status": exc.code}
        try:
            controls = self._system_controls()
        except Blocked as exc:
            controls = {"status": exc.code}
        with self._db() as db:
            in_flight = db.execute("SELECT COUNT(*) FROM requests WHERE state='running'").fetchone()[0]
            consumed = bool(db.execute("SELECT 1 FROM consumed_gates WHERE gate_id=?", (gate_state.get("gate_id"),)).fetchone())
        return {"adapter": "gemini-real-cli-mcp", "version": "0.1.0", "cli_path": str(self.config.cli) if self.config.cli else None, "runtime": runtime,
                "cli_home": str(self.config.cli_home), "credential_cache_location": str(self.config.cli_home / ".gemini" / "oauth_creds.json"),
                "credential_contents_read": False, "credential_validity": "UNVERIFIED_BY_STATUS",
                "verification_gate": gate_state, "in_flight_or_uncertain_requests": in_flight,
                "one_cli_invocation_budget_consumed": consumed, "provider_request_count": "UNVERIFIED",
                "system_controls": controls,
                "generation_ready": runtime["status"] == "PASS" and controls["status"] == "PASS" and gate_state["status"] == "LOCAL_OPERATOR_EVIDENCE_PRESENT" and not consumed and not in_flight,
                "generation_readiness_semantics": "Local externally verified evidence gate, not independent provider authentication proof.",
                "chatgpt_native_connection": "UNVERIFIED", "scheduled_delegation": "UNVERIFIED"}

    @staticmethod
    def _validate(request_id, prompt):
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", request_id):
            raise Blocked("BLOCKED_INVALID_REQUEST_ID")
        if not isinstance(prompt, str) or not (1 <= len(prompt.strip()) <= 6000) or len(prompt.encode("utf-8")) > 24000:
            raise Blocked("BLOCKED_INVALID_PROMPT")
        if any(ord(c) < 32 and c not in "\n\t" for c in prompt) or SECRET.search(prompt):
            raise Blocked("BLOCKED_SECRET_LIKE_OR_CONTROL_INPUT")

    def _claim(self, request_id, prompt_sha, gate):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["prompt_sha"] != prompt_sha:
                    raise Blocked("BLOCKED_REQUEST_ID_CONFLICT")
                if old["state"] == "done":
                    return json.loads(old["result_json"])
                raise Blocked("BLOCKED_REQUEST_PENDING_OR_UNCERTAIN")
            if db.execute("SELECT 1 FROM requests WHERE state='running' LIMIT 1").fetchone():
                raise Blocked("BLOCKED_CONCURRENCY_LIMIT")
            if db.execute("SELECT 1 FROM consumed_gates WHERE gate_id=?", (gate["gate_id"],)).fetchone():
                raise Blocked("BLOCKED_VERIFIED_ONE_CLI_INVOCATION_BUDGET_CONSUMED")
            db.execute("INSERT INTO consumed_gates VALUES (?,?)", (gate["gate_id"], request_id))
            db.execute("INSERT INTO requests VALUES (?,?, 'running',NULL,?)", (request_id, prompt_sha, time.time()))
            return None

    def _existing(self, request_id, prompt_sha):
        with self._db() as db:
            old = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if old is None:
            return None
        if old["prompt_sha"] != prompt_sha:
            raise Blocked("BLOCKED_REQUEST_ID_CONFLICT")
        if old["state"] != "done":
            raise Blocked("BLOCKED_REQUEST_PENDING_OR_UNCERTAIN")
        return json.loads(old["result_json"])

    def review(self, request_id, prompt):
        self._validate(request_id, prompt)
        digest = hashlib.sha256(prompt.encode()).hexdigest()
        old = self._existing(request_id, digest)
        if old is not None:
            return old
        self._env()  # Detect forbidden paid-provider environment before any call.
        gate = self._gate()
        self._system_controls()
        self.version()
        if self.policy.read_text() != DENY_POLICY or self.policy.is_symlink():
            raise Blocked("BLOCKED_POLICY_CHANGED")
        if any(self.work.iterdir()):
            raise Blocked("BLOCKED_NONEMPTY_WORKSPACE")
        # Central admin policies can suppress supplemental policy flags. Do not
        # bypass them or run without independently known deny-all enforcement.
        central = [Path('/etc/gemini-cli/policies'), Path('/Library/Application Support/GeminiCli/policies')]
        if os.environ.get('ProgramData'):
            central.append(Path(os.environ['ProgramData']) / 'gemini-cli' / 'policies')
        if any(p.exists() and any(p.glob('*.toml')) for p in central):
            raise Blocked("BLOCKED_CENTRAL_POLICY_REQUIRES_REVIEW")
        old = self._claim(request_id, digest, gate)
        if old is not None:
            return old
        try:
            raw = self._run(["--prompt", "Review only the text provided on standard input. Do not use tools or access files.", "--output-format", "json", "--approval-mode", "plan", "--policy", str(self.policy), "--admin-policy", str(self.policy)], payload=prompt.encode())
            try:
                body = json.loads(raw)
            except (ValueError, TypeError):
                raise Blocked("BLOCKED_CLI_INVALID_JSON") from None
            if not isinstance(body, dict) or body.get("error") or not isinstance(body.get("response"), str) or not (1 <= len(body["response"].strip()) <= 16000):
                raise Blocked("BLOCKED_CLI_INVALID_RESPONSE")
            if SECRET.search(body["response"]):
                raise Blocked("BLOCKED_SECRET_LIKE_OUTPUT")
            result = {"status": "PASS_REAL_CLI_JSON_RESPONSE", "request_id": request_id, "response": body["response"], "cli_version": EXPECTED_VERSION,
                      "provider_call_id": None, "provider_call_id_status": "NOT_PROVIDED_BY_CLI_OUTPUT", "provider_request_count": "UNVERIFIED", "native_scheduled_run": "UNVERIFIED"}
        except Blocked as exc:
            result = {"status": exc.code, "request_id": request_id, "response": None, "provider_completion": "UNVERIFIED", "provider_request_count": "UNVERIFIED", "automatic_retry": False}
        except Exception:
            result = {"status": "BLOCKED_UNEXPECTED_EXECUTION_ERROR", "request_id": request_id, "response": None, "provider_completion": "UNVERIFIED", "provider_request_count": "UNVERIFIED", "automatic_retry": False}
        with self._db() as db:
            db.execute("UPDATE requests SET state='done',result_json=? WHERE request_id=?", (json.dumps(result), request_id))
        return result
