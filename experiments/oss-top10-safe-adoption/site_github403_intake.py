"""Offline Site 403 evidence intake: stdin JSON -> sanitized no-write verdict.

A runnable bridge for PR #31's existing native-run/cooldown guard.
It is NOT deployed into the Site, does NOT authenticate Site or GitHub,
and never authorizes retry, a write, a deployment, or a PASS claim.

Usage: python -B site_github403_intake.py < site_event.json
Exit 0 = confirmed read-only SAME_HEAD/NO_UPDATE classification, NOT authorization.
Exit 2 = BLOCKED or UNVERIFIED input / parse error. No raw input is echoed.
"""
from __future__ import annotations

import json
import sys

from native_run_cooldown_guard import audit

MAX_BYTES = 65_536
SCHEMA = "SITE_GITHUB403_READONLY_INTAKE_V1"


def _distinct_pairs(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def classify(payload: object) -> dict:
    """Classify provided data only; source provenance remains unverified."""
    if not isinstance(payload, dict):
        raise ValueError("input root must be object")
    evaluated = audit(payload)
    verdict = evaluated["overall"]
    if verdict not in {"BLOCKED", "UNVERIFIED", "NO_UPDATE", "FAIL"}:
        verdict = "UNVERIFIED"  # No success/authorization path.
    return {
        "schema": SCHEMA,
        "classification": verdict,
        "native_status": evaluated["native"]["status"],
        "cycle_status": evaluated["cycle"]["status"],
        "reason_code": (
            "SITE_GITHUB_DENIED" if evaluated["cycle"]["status"] == "BLOCKED"
            else "SOURCE_NOT_AUTHENTICATED"
        ),
        "site_source_authentication": "UNVERIFIED",
        "site_runtime_integration": "UNVERIFIED",
        "operational_clearance": "BLOCKED",
        "external_requests": 0,
        "external_mutations": 0,
        "allow_retry": False,
        "allow_write": False,
    }


def run(input_stream: object = None, output_stream: object = None) -> int:
    src = input_stream if input_stream is not None else sys.stdin.buffer
    dst = output_stream if output_stream is not None else sys.stdout
    try:
        raw = src.read(MAX_BYTES + 1)
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
            raise ValueError("input size invalid")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_distinct_pairs)
        result = classify(payload)
    except (ValueError, TypeError, UnicodeError, KeyError, IndexError, OverflowError):
        result = {
            "schema": SCHEMA,
            "classification": "BLOCKED",
            "reason_code": "INPUT_INVALID",
            "site_source_authentication": "UNVERIFIED",
            "site_runtime_integration": "UNVERIFIED",
            "operational_clearance": "BLOCKED",
            "external_requests": 0,
            "external_mutations": 0,
            "allow_retry": False,
            "allow_write": False,
        }
    dst.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0 if result["classification"] == "NO_UPDATE" else 2


if __name__ == "__main__":
    raise SystemExit(run())
