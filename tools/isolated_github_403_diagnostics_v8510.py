"""Isolated, no-network GitHub HTTP 403 / 429 evidence classifier.

This does not access GitHub, refresh tokens, modify authorization, or schedule
a retry. Only callers with an authorized, real response may supply sanitized
header metadata. Input bodies/credentials are never accepted or logged.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

VERSION = "8.5.10-isolated-github-403-diagnostics"


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("INVALID_OBSERVATION_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("INVALID_OBSERVATION_TIME") from exc
    if parsed.tzinfo is None:
        raise ValueError("NAIVE_OBSERVATION_TIME")
    return parsed.astimezone(timezone.utc)


def _nonnegative_int(value: object) -> int | None:
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        return None
    # Ignore absurdly large untrusted numbers rather than letting them
    # overflow or produce an early retry.
    if len(value) > 12:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def diagnose_github_http(
    status: int,
    headers: Mapping[str, str],
    observed_at: str,
    *,
    secondary_limit_signaled: bool = False,
    repeated_secondary_failures: int = 0,
) -> dict[str, object]:
    """Classify without leaking headers and without issuing network requests.

    If insufficient evidence is available, fail closed with a review verdict.
    The caller must still respect server-managed cooldowns and policy.
    """
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        raise ValueError("INVALID_STATUS")
    if not isinstance(headers, Mapping):
        raise ValueError("INVALID_HEADERS")
    if not isinstance(secondary_limit_signaled, bool):
        raise ValueError("INVALID_SECONDARY_SIGNAL")
    if (isinstance(repeated_secondary_failures, bool)
            or not isinstance(repeated_secondary_failures, int)
            or not 0 <= repeated_secondary_failures <= 8):
        raise ValueError("INVALID_FAILURE_COUNT")

    observed = _utc(observed_at)
    selected: dict[str, str] = {}
    allow = {"retry-after", "x-ratelimit-remaining", "x-ratelimit-reset"}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("INVALID_HEADERS")
        lower = key.lower()
        if lower in allow:
            if lower in selected:
                raise ValueError("DUPLICATE_HEADER")
            selected[lower] = value.strip()

    remaining = _nonnegative_int(selected.get("x-ratelimit-remaining"))
    reset_seconds = _nonnegative_int(selected.get("x-ratelimit-reset"))
    retry_seconds = _nonnegative_int(selected.get("retry-after"))
    has_bad_retry = "retry-after" in selected and retry_seconds is None
    has_bad_reset = "x-ratelimit-reset" in selected and reset_seconds is None
    has_bad_remaining = "x-ratelimit-remaining" in selected and remaining is None

    classification = "NOT_RATE_LIMIT_ERROR"
    required_review = False
    retry_at: datetime | None = None
    if status == 401:
        classification = "AUTHENTICATION_REVIEW"
        required_review = True
    elif status in (403, 429):
        if has_bad_retry or has_bad_reset or has_bad_remaining:
            classification = "INCOMPLETE_OR_INVALID_LIMIT_EVIDENCE"
            required_review = True
        elif remaining == 0:
            classification = "PRIMARY_RATE_LIMIT"
            # GitHub documents the UTC epoch reset and Retry-After as
            # minimum retry deadlines. Never prefer the earlier one.
            candidates = [observed + timedelta(seconds=60)]
            if reset_seconds is not None:
                try:
                    candidates.append(datetime.fromtimestamp(reset_seconds, timezone.utc))
                except (OverflowError, ValueError, OSError):
                    required_review = True
            else:
                required_review = True
            if retry_seconds is not None:
                candidates.append(observed + timedelta(seconds=min(retry_seconds, 604800)))
            retry_at = max(candidates)
        elif secondary_limit_signaled:
            classification = "SECONDARY_RATE_LIMIT"
            seconds = min(60 * 2 ** repeated_secondary_failures, 3600)
            if retry_seconds is not None:
                seconds = max(seconds, min(retry_seconds, 604800))
            retry_at = observed + timedelta(seconds=seconds)
        elif retry_seconds is not None:
            classification = "RATE_LIMIT_RETRY_AFTER"
            retry_at = observed + timedelta(seconds=max(60, min(retry_seconds, 604800)))
        else:
            classification = "PERMISSION_OR_UNKNOWN_LIMIT"
            required_review = True
    return {
        "schema": VERSION,
        "http_status": status,
        "classification": classification,
        "retry_not_before_utc": (retry_at.isoformat().replace("+00:00", "Z")
                                  if retry_at is not None else None),
        "requires_review": required_review,
        "automatic_request_performed": False,
        "original_access_restored": False,
        "native_run_verified": False,
    }
