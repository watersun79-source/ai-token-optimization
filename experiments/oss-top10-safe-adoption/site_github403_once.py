"""One-shot LOCAL adapter: a future official Site read export -> existing bridge.

Example (once a separate authorized official reader provides a local JSON export):
    python -B site_github403_once.py < site_read_export.json

This program DOES NOT call Site/GitHub, authenticate or fetch a URL. The
SITE_READ_RESULT_EXPORT_V1 contract is locally defined, NOT a published Site API.
All source claims remain UNVERIFIED, all operational changes stay BLOCKED.
Exit code is always 2 (fail-closed); no input, log, or credential is echoed.
"""
from __future__ import annotations

import json
import sys

from site_github403_evidence_bridge import (
    ID_PATTERN, MAX_BYTES, PROJECT_ID, SCHEMA as BRIDGE_SCHEMA,
    _base, _valid_utc, bridge,
)
from site_github403_intake import _distinct_pairs

SCHEMA = "SITE_READ_RESULT_EXPORT_V1"


def normalize(export: object) -> dict | None:
    """Convert one local, UNAUTHENTICATED export into the bridge's input shape."""
    if export is None:
        return None
    if not isinstance(export, dict) or export.get("schema") != SCHEMA:
        raise ValueError("INPUT_INVALID")
    if export.get("project_id") != PROJECT_ID:
        raise ValueError("PROJECT_ID_MISMATCH")

    source = export.get("source")
    request = export.get("github_request")
    if not isinstance(source, dict) or not isinstance(request, dict):
        raise ValueError("SOURCE_INCOMPLETE")

    ref = source.get("reference")
    if (source.get("reader") != "site_readonly_export" or
            not isinstance(ref, str) or not ID_PATTERN.fullmatch(ref) or
            not _valid_utc(source.get("observed_at_utc"))):
        raise ValueError("SOURCE_INCOMPLETE")

    execution_id = request.get("execution_id")
    if not isinstance(execution_id, str) or not ID_PATTERN.fullmatch(execution_id):
        raise ValueError("SOURCE_INCOMPLETE")
    if (type(request.get("http_status")) is not int or
            request.get("http_status") != 403 or
            request.get("error_code") not in ("GITHUB_HTTP_403", "HTTP_403")):
        raise ValueError("HTTP_EVIDENCE_MISMATCH")

    # Only bounded nonsecret metadata is forwarded. Never forward raw logs,
    # auth_status, tokens, signatures, headers, or a claimed PASS.
    return {
        "schema": BRIDGE_SCHEMA,
        "project_id": PROJECT_ID,
        "source": {
            "reader": source["reader"],
            "reference": ref,
            "observed_at_utc": source["observed_at_utc"],
        },
        "collector": {
            "execution_id": execution_id,
            "http_status": request["http_status"],
            "error_code": request["error_code"],
            "observed_at_utc": source["observed_at_utc"],
        },
    }


def once(input_stream: object = None, output_stream: object = None) -> int:
    src = input_stream if input_stream is not None else sys.stdin.buffer
    dst = output_stream if output_stream is not None else sys.stdout
    try:
        raw = src.read(MAX_BYTES + 1)
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
            raise ValueError("INPUT_INVALID")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_distinct_pairs)
        result = bridge(normalize(data))
    except (ValueError, TypeError, UnicodeError, KeyError, OverflowError, IndexError) as exc:
        code = str(exc)
        if code not in ("PROJECT_ID_MISMATCH", "SOURCE_INCOMPLETE", "HTTP_EVIDENCE_MISMATCH"):
            code = "INPUT_INVALID"
        result = _base(code)

    dst.write(json.dumps(result, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")) + "\n")
    return 2  # Never claim authenticated Site origin or authorize a write.


if __name__ == "__main__":
    raise SystemExit(once())
