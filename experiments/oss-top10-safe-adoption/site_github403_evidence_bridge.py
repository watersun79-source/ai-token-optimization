"""Read-only bridge for a future explicitly supplied Site collector observation.

This is a LOCAL INPUT CONTRACT, not an official Site API or deployed connector.
No official raw Site 403 read endpoint was available during implementation.
A supplied claim, even with PASS metadata, is never treated as authenticated.
No network, secrets, subprocess, persistent state, retries or remote writes.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime

from site_github403_intake import MAX_BYTES, _distinct_pairs, classify

SCHEMA = "SITE_GITHUB403_OBSERVATION_INPUT_V1"
RESULT_SCHEMA = "SITE_GITHUB403_OFFLINE_BRIDGE_V1"
PROJECT_ID = "appgprj_6ae20fb4b2b08191b0f4b44438fc0237"
ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


def _base(reason: str) -> dict:
    return {
        "schema": RESULT_SCHEMA,
        "classification": "UNVERIFIED",
        "observed_cycle_status": "UNVERIFIED",
        "reason_code": reason,
        "source_authentication": "UNVERIFIED",
        "github_authentication": "UNVERIFIED",
        "site_runtime_integration": "UNVERIFIED",
        "root_cause": "UNVERIFIED",
        "operational_clearance": "BLOCKED",
        "allow_retry": False,
        "allow_write": False,
        "external_requests": 0,
        "external_mutations": 0,
    }


def _valid_utc(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except (ValueError, OverflowError):
        return False


def bridge(observation: object) -> dict:
    """Map a locally normalized 403 observation onto existing intake; NEVER verify its provenance."""
    if observation is None:
        return _base("MISSING_OFFICIAL_SOURCE")
    if not isinstance(observation, dict) or observation.get("schema") != SCHEMA:
        return _base("INPUT_INVALID")
    if observation.get("project_id") != PROJECT_ID:
        return _base("PROJECT_ID_MISMATCH")
    collector = observation.get("collector")
    if not isinstance(collector, dict):
        return _base("SOURCE_INCOMPLETE")
    if (type(collector.get("http_status")) is not int or collector["http_status"] != 403 or
            collector.get("error_code") not in ("GITHUB_HTTP_403", "HTTP_403")):
        return _base("HTTP_EVIDENCE_MISMATCH")
    if not (isinstance(collector.get("execution_id"), str) and
            ID_PATTERN.fullmatch(collector["execution_id"]) and
            _valid_utc(collector.get("observed_at_utc"))):
        return _base("SOURCE_INCOMPLETE")

    native = observation.get("native")
    if native is None:
        native = {}
    elif not isinstance(native, dict):
        return _base("INPUT_INVALID")
    last, latest = native.get("last_run"), native.get("latest_result")
    if (last is None) != (latest is None):
        return _base("NATIVE_EVIDENCE_PARTIAL")
    if last is not None and (not isinstance(last, dict) or not isinstance(latest, dict)):
        return _base("INPUT_INVALID")
    # A 403 observation maps to a blocked *cycle*, not a verified Site root cause.
    cycle = {"status": "BLOCKED", "debug": {"status": "BLOCKED", "reason": "GITHUB_HTTP_403"},
             "fix": {"status": "SKIP"}, "update": {"status": "SKIP"}}
    supplied = {"evolution_cycle": cycle}
    if last is not None:
        supplied.update(last_run=last, latest_result=latest)
    evaluated = classify(supplied)
    result = _base("UNAUTHENTICATED_SITE_OBSERVATION")
    result["observed_cycle_status"] = evaluated["cycle_status"]
    result["reported_native_status"] = evaluated["native_status"]
    # Never convert user-supplied/persisted claims into a live Site success proof.
    return result


def run(src: object = None, dst: object = None) -> int:
    stream = src if src is not None else sys.stdin.buffer
    sink = dst if dst is not None else sys.stdout
    try:
        raw = stream.read(MAX_BYTES + 1)
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
            raise ValueError("size invalid")
        observation = json.loads(raw.decode("utf-8"), object_pairs_hook=_distinct_pairs)
        out = bridge(observation)
    except (ValueError, TypeError, UnicodeError, OverflowError, KeyError, IndexError):
        out = _base("INPUT_INVALID")
    sink.write(json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 2  # No authenticated Site reader or promotion path exists here.


if __name__ == "__main__":
    raise SystemExit(run())
