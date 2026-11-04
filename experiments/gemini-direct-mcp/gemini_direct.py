"""Unconnected, default-denied preparation for one fixed Gemini REST request.

Importing this module and calling dry_request() perform no account, network,
or credential I/O. This module
does not discover credentials, verify an account, register an MCP tool, or
independently establish that operator assertions are true.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import http.client
import json
import os
import re
import ssl
import threading
from types import MappingProxyType
from typing import Any
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MODEL = "gemini-3.5-flash-lite"
_HOST = "generativelanguage.googleapis.com"
_PATH = "/v1beta/models/gemini-3.5-flash-lite:generateContent"
_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
_BODY_LIMIT = 64 * 1024
_TIMEOUT_SECONDS = 30
_MAX_EVIDENCE_AGE_SECONDS = 15 * 60
_KEY_ENVIRONMENT_NAME = "GEMINI_DIRECT_API_KEY"
_KEY_PATTERN = re.compile(r"(?:[A-Za-z0-9_-]{16,256}|AQ\.[A-Za-z0-9_-]{16,253})\Z")
_AQ_SECRET = re.compile(r"AQ\.[A-Za-z0-9_-]{16,}")
_GENERATION_CONFIG = {
    "candidateCount": 1,
    "maxOutputTokens": 256,
    "responseModalities": ["TEXT"],
}
_FACT_FIELDS = (
    "auth_verified",
    "key_project_binding_verified",
    "free_tier_verified",
    "quota_verified",
)
_REF_FIELDS = {"auth", "project_binding", "free_tier", "billing", "daily_quota"}
_EVIDENCE_FIELDS = {
    "schema_version", "status", "evidence_id", "api_key_sha256", "model",
    "observed_at", "quota_day_pacific", "billing_account_linked",
    "paid_billing_enabled", "remaining_requests", "evidence_refs", *_FACT_FIELDS,
}
_REPLAY_LOCK = threading.Lock()
_SPENT_EVIDENCE_IDS: set[str] = set()
_MAX_PROCESS_EVIDENCE_IDS = 1024


class CandidateError(Exception):
    """A static error code; never carries keys, prompts, or upstream errors."""


class Config:
    """Caller-only key configuration. Disabled unless explicitly enabled.

    The key has no public getter and is excluded from repr/str. Python memory
    is not a secret vault: privileged debuggers and caller introspection are
    outside this module's protection boundary.
    """

    __slots__ = ("__api_key", "enabled")

    def __init__(self, *, api_key: str, enabled: bool = False):
        if type(api_key) is not str or _KEY_PATTERN.fullmatch(api_key) is None:
            raise CandidateError("KEY_INVALID")
        if type(enabled) is not bool:
            raise CandidateError("ENABLE_FLAG_INVALID")
        self.__api_key = api_key
        self.enabled = enabled

    def __repr__(self) -> str:
        return f"Config(api_key=<redacted>, enabled={self.enabled!r})"

    __str__ = __repr__

    @classmethod
    def from_environment(cls, *, environ: Mapping[str, str] | None = None, enabled: bool = False) -> Config:
        """Read only the dedicated variable, and only when called by the owner.

        This method is never called during import, dry_request(), or ordinary
        explicit-config requests. It does not inspect other environment keys.
        """
        source = os.environ if environ is None else environ
        return cls(api_key=source.get(_KEY_ENVIRONMENT_NAME), enabled=enabled)

    @property
    def api_key_sha256(self) -> str:
        """Non-secret binding for independently collected operator evidence."""
        return hashlib.sha256(self.__api_key.encode("ascii")).hexdigest()

    def _header_value(self) -> str:
        return self.__api_key


@dataclass(frozen=True, slots=True, repr=False)
class OperatorEvidence:
    """Untrusted operator observations; this class does not authenticate them."""

    _data: Mapping[str, Any]

    def __repr__(self) -> str:
        return "OperatorEvidence(<untrusted operator assertions>)"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> OperatorEvidence:
        if not isinstance(data, Mapping) or set(data) - _EVIDENCE_FIELDS:
            raise CandidateError("EVIDENCE_SCHEMA_INVALID")
        snapshot = dict(data)
        if isinstance(snapshot.get("evidence_refs"), Mapping):
            snapshot["evidence_refs"] = MappingProxyType(dict(snapshot["evidence_refs"]))
        return cls(MappingProxyType(snapshot))

    def _validate(self, config: Config, now: datetime) -> str:
        data = self._data
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise CandidateError("EVIDENCE_SCHEMA_INVALID")
        if data.get("status") != "VERIFIED_BY_OPERATOR":
            raise CandidateError("EVIDENCE_UNVERIFIED")
        if data.get("model") != MODEL:
            raise CandidateError("EVIDENCE_MODEL_MISMATCH")
        digest = data.get("api_key_sha256")
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise CandidateError("EVIDENCE_KEY_BINDING_INVALID")
        if not hmac.compare_digest(digest, config.api_key_sha256):
            raise CandidateError("EVIDENCE_KEY_MISMATCH")
        if any(data.get(field) is not True for field in _FACT_FIELDS):
            raise CandidateError("EVIDENCE_FACT_UNVERIFIED")
        if data.get("billing_account_linked") is not False or data.get("paid_billing_enabled") is not False:
            raise CandidateError("EVIDENCE_BILLING_NOT_UNLINKED")
        remaining = data.get("remaining_requests")
        if type(remaining) is not int or remaining < 1:
            raise CandidateError("EVIDENCE_NO_VERIFIED_REQUEST")
        refs = data.get("evidence_refs")
        if not isinstance(refs, Mapping) or set(refs) != _REF_FIELDS:
            raise CandidateError("EVIDENCE_REFERENCES_MISSING")
        if any(type(value) is not str or re.fullmatch(r"[A-Za-z0-9:._/-]{1,256}", value) is None or _AQ_SECRET.search(value)
               for value in refs.values()):
            raise CandidateError("EVIDENCE_REFERENCES_INVALID")
        observed_at = data.get("observed_at")
        observed = None
        if type(observed_at) is str and len(observed_at) <= 64:
            try:
                observed = datetime.fromisoformat(observed_at)
            except ValueError:
                pass
        if observed is None or observed.tzinfo is None or observed.utcoffset() is None:
            raise CandidateError("EVIDENCE_TIMESTAMP_INVALID")
        age = (now - observed.astimezone(timezone.utc)).total_seconds()
        if age < 0 or age > _MAX_EVIDENCE_AGE_SECONDS:
            raise CandidateError("EVIDENCE_NOT_FRESH")
        pacific_day = None
        try:
            pacific_day = now.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        except ZoneInfoNotFoundError:
            pass
        if pacific_day is None:
            raise CandidateError("PACIFIC_TIMEZONE_UNAVAILABLE")
        if data.get("quota_day_pacific") != pacific_day:
            raise CandidateError("EVIDENCE_WRONG_QUOTA_DAY")
        evidence_id = data.get("evidence_id")
        parsed_id = None
        if type(evidence_id) is str and len(evidence_id) == 36:
            try:
                parsed_id = uuid.UUID(evidence_id)
            except ValueError:
                pass
        if parsed_id is None or str(parsed_id) != evidence_id:
            raise CandidateError("EVIDENCE_ID_INVALID")
        return evidence_id


@dataclass(frozen=True, slots=True)
class TextResult:
    """Only whitelisted text and counts; model is the fixed requested model."""

    model: str
    text: str
    finish_reason: str
    usage: dict[str, int]

    @property
    def complete(self) -> bool:
        return self.finish_reason == "STOP"


def dry_request() -> dict[str, Any]:
    """A constant schema preview, without a key, headers, or prompt values."""
    return {
        "endpoint": _ENDPOINT,
        "body_shape": {
            "contents": [{"role": "user", "parts": [{"text": "<string; value omitted>"}]}],
            "generationConfig": {
                **_GENERATION_CONFIG,
                "responseModalities": ["TEXT"],
            },
            "tools": [],
        },
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _tls_context() -> ssl.SSLContext:
    # Do not use ssl.create_default_context(): its SSLKEYLOGFILE environment
    # support can create a TLS-key log. This context never enables key logging.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    return context


def _request_body(prompt: str, config: Config) -> bytes:
    if type(prompt) is not str or not prompt.strip():
        raise CandidateError("PROMPT_INVALID")
    if config._header_value() in prompt or _AQ_SECRET.search(prompt):
        raise CandidateError("SECRET_IN_PROMPT")
    if len(prompt) > _BODY_LIMIT:
        raise CandidateError("REQUEST_TOO_LARGE")
    body = None
    try:
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": _GENERATION_CONFIG,
            "tools": [],
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError):
        pass
    if body is None:
        raise CandidateError("PROMPT_ENCODING_INVALID")
    if len(body) > _BODY_LIMIT:
        raise CandidateError("REQUEST_TOO_LARGE")
    return body


def _send_once(body: bytes, config: Config) -> bytes:
    """Exactly one direct HTTPS request; no proxy, redirect, retry, or logging.

    http.client does not implement environment-proxy discovery. No tunnel is
    configured. The timeout is the stdlib socket-operation timeout, not a
    guarantee about DNS resolution or total wall-clock process duration.
    """
    connection = None
    failure = None
    raw = b""
    try:
        connection = http.client.HTTPSConnection(
            _HOST, port=443, timeout=_TIMEOUT_SECONDS, context=_tls_context()
        )
        connection.set_debuglevel(0)
        connection.request("POST", _PATH, body=body, headers={
            "x-goog-api-key": config._header_value(),
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        })
        response = connection.getresponse()
        if 300 <= response.status <= 399:
            failure = "REDIRECT_FORBIDDEN"
        elif response.status != 200:
            failure = "UPSTREAM_HTTP_FAILURE"
        elif response.getheader("content-encoding", "identity").lower() != "identity":
            failure = "RESPONSE_ENCODING_FORBIDDEN"
        else:
            content_length = response.getheader("content-length")
            if content_length is not None and (
                not content_length.isdecimal() or int(content_length) > _BODY_LIMIT
            ):
                failure = "RESPONSE_TOO_LARGE"
            else:
                raw = response.read(_BODY_LIMIT + 1)
                if len(raw) > _BODY_LIMIT:
                    failure = "RESPONSE_TOO_LARGE"
    except Exception:
        # Never retain, stringify, chain, log, or return transport exceptions.
        failure = "NETWORK_FAILED"
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                failure = failure or "NETWORK_CLEANUP_FAILED"
    # Raise outside the except suite so __context__ cannot retain a leaky error.
    if failure is not None:
        raise CandidateError(failure)
    return raw


def _parse_response(raw: bytes, config: Config) -> TextResult:
    payload = None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        pass
    if not isinstance(payload, dict):
        raise CandidateError("RESPONSE_JSON_INVALID")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
        raise CandidateError("RESPONSE_NO_SINGLE_CANDIDATE")
    candidate = candidates[0]
    finish = candidate.get("finishReason")
    if finish not in ("STOP", "MAX_TOKENS"):
        raise CandidateError("RESPONSE_NOT_TEXT_COMPLETION")
    if candidate.get("groundingMetadata") or candidate.get("groundingAttributions"):
        raise CandidateError("RESPONSE_UNEXPECTED_GROUNDING")
    content = candidate.get("content")
    if not isinstance(content, dict) or content.get("role", "model") != "model":
        raise CandidateError("RESPONSE_CONTENT_INVALID")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise CandidateError("RESPONSE_CONTENT_INVALID")
    text_parts = []
    for part in parts:
        if not isinstance(part, dict) or set(part) - {"text", "thought", "thoughtSignature"}:
            raise CandidateError("RESPONSE_TOOL_OR_NON_TEXT")
        if type(part.get("text")) is not str or type(part.get("thought", False)) is not bool:
            raise CandidateError("RESPONSE_CONTENT_INVALID")
        if not part.get("thought", False):
            text_parts.append(part["text"])
    text = "".join(text_parts)
    if not text:
        raise CandidateError("RESPONSE_TEXT_EMPTY")
    if config._header_value() in text or _AQ_SECRET.search(text):
        raise CandidateError("RESPONSE_SECRET_REDACTED")
    usage = {}
    metadata = payload.get("usageMetadata", {})
    if not isinstance(metadata, dict):
        raise CandidateError("RESPONSE_USAGE_INVALID")
    if metadata.get("toolUsePromptTokenCount", 0) != 0:
        raise CandidateError("RESPONSE_UNEXPECTED_TOOL_USAGE")
    for field in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount",
                  "thoughtsTokenCount", "cachedContentTokenCount"):
        if field in metadata:
            count = metadata[field]
            if type(count) is not int or count < 0:
                raise CandidateError("RESPONSE_USAGE_INVALID")
            usage[field] = count
    return TextResult(model=MODEL, text=text, finish_reason=finish, usage=usage)


class GeminiDirectClient:
    """At most one HTTP attempt per client; evidence replay blocked per process."""

    __slots__ = ("_config", "_attempted", "_lock")

    def __init__(self, config: Config):
        if not isinstance(config, Config):
            raise CandidateError("CONFIG_INVALID")
        self._config = config
        self._attempted = False
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"GeminiDirectClient(enabled={self._config.enabled!r}, attempted={self._attempted!r})"

    def generate_once(self, prompt: str, *, evidence: OperatorEvidence | None) -> TextResult:
        """No key/model/tools/endpoint arguments are accepted at this boundary."""
        if self._config.enabled is not True:
            raise CandidateError("CLIENT_DISABLED")
        if not isinstance(evidence, OperatorEvidence):
            raise CandidateError("EVIDENCE_REQUIRED")
        evidence_id = evidence._validate(self._config, _utc_now())
        body = _request_body(prompt, self._config)
        with self._lock:
            with _REPLAY_LOCK:
                if self._attempted or evidence_id in _SPENT_EVIDENCE_IDS:
                    raise CandidateError("ATTEMPT_ALREADY_CONSUMED")
                if len(_SPENT_EVIDENCE_IDS) >= _MAX_PROCESS_EVIDENCE_IDS:
                    raise CandidateError("PROCESS_ATTEMPT_LIMIT_REACHED")
                self._attempted = True
                _SPENT_EVIDENCE_IDS.add(evidence_id)
        raw = _send_once(body, self._config)
        return _parse_response(raw, self._config)
