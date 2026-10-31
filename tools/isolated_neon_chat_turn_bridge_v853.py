"""Chat-turn-only, test-branch Neon connector plan for selected AI BOT memory.

Generates a pair of SQL statements for *authorized explicit Neon connector calls*.
Does not invoke MCP, catch all ChatGPT messages, run in the background,
expose connection credentials, or switch any operating service.
The connected host must send BOTH statements only to the pinned test branch.
"""
from __future__ import annotations

import hashlib

from collections.abc import Mapping
from typing import Any

from tools.isolated_selective_memory_v85 import (
    TEST_PROJECT_ID, TEST_BRANCH_ID, TEST_DB_NAME, select_event,
)

VERSION = "8.5.3-isolated-connector-plan"
TABLE = "public.isolated_project_memory_v85"


def _utf8_literal(value: str) -> str:
    """Return a SQL expression built only from hexadecimal UTF-8 bytes.

    Avoids interpolating raw user-controlled text into SQL literals.
    This is for the text-only Neon connector; ordinary PostgreSQL clients
    must still use actual bound parameters.
    """
    return "convert_from(decode('" + value.encode("utf-8").hex() + "','hex'),'UTF8')"


def prepare_selected_neon_commands(event: Mapping[str, Any]) -> dict[str, Any]:
    """Produce a narrow, opt-in two-step connector plan; never execute it."""
    record = select_event(event)
    if record is None:
        return {"status": "SKIPPED", "reason": "NOT_SELECTED"}
    fields = (
        record.record_id, record.project_key, record.kind,
        record.title, record.body, record.digest,
    )
    encoded = ",".join(_utf8_literal(v) for v in fields)
    insert_sql = (
        "INSERT INTO " + TABLE +
        " (record_id,project_key,kind,title,body,content_sha256) "
        "VALUES (" + encoded + ") "
        "ON CONFLICT (record_id) DO NOTHING "
        "RETURNING record_id,kind,content_sha256"
    )
    read_sql = (
        "SELECT record_id,project_key,kind,title,body,content_sha256 "
        "FROM " + TABLE +
        " WHERE record_id=" + _utf8_literal(record.record_id) +
        " AND project_key=" + _utf8_literal(record.project_key) +
        " LIMIT 2"
    )
    return {
        "status": "REQUIRES_EXPLICIT_HOST_NEON_TOOL_CALL",
        "version": VERSION,
        "project_id": TEST_PROJECT_ID,
        "branch_id": TEST_BRANCH_ID,
        "database_name": TEST_DB_NAME,
        "insert_sql": insert_sql,
        "read_sql": read_sql,
        "expected": {
            "record_id": record.record_id, "project_key": record.project_key,
            "kind": record.kind, "title": record.title, "body": record.body,
            "content_sha256": record.digest,
        },
        "automatic_global_chat_capture": False,
        "production_connected": False,
    }


def validate_neon_connector_results(
    plan: Mapping[str, Any],
    inserted: Any,
    readback: Any,
) -> dict[str, Any]:
    """Validate connector results after trusted host has made exact scoped calls.

    Does not prove that the host used the supplied target identifiers;
    that must be verified from actual Neon tool call arguments.
    """
    if plan.get("status") != "REQUIRES_EXPLICIT_HOST_NEON_TOOL_CALL":
        raise ValueError("PLAN_NOT_SELECTED")
    if (
        plan.get("project_id") != TEST_PROJECT_ID
        or plan.get("branch_id") != TEST_BRANCH_ID
        or plan.get("database_name") != TEST_DB_NAME
    ):
        raise ValueError("WRONG_NEON_TARGET")
    if not isinstance(inserted, list) or not isinstance(readback, list):
        raise ValueError("INVALID_CONNECTOR_RESPONSE")
    if len(inserted) > 1 or len(readback) != 1:
        raise RuntimeError("READBACK_MISMATCH")
    expected = plan.get("expected")
    if not isinstance(expected, Mapping):
        raise ValueError("INVALID_EXPECTED_RECORD")
    body = expected.get("body")
    claimed_sha = expected.get("content_sha256")
    if not isinstance(body, str) or not isinstance(claimed_sha, str):
        raise ValueError("INVALID_EXPECTED_RECORD")
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != claimed_sha:
        raise RuntimeError("READBACK_HASH_MISMATCH")
    row = readback[0]
    if not isinstance(row, dict) or any(row.get(k) != v for k, v in expected.items()):
        raise RuntimeError("READBACK_MISMATCH")
    if inserted:
        i = inserted[0]
        if not isinstance(i, dict) or any(i.get(k) != expected[k] for k in (
            "record_id", "kind", "content_sha256"
        )):
            raise RuntimeError("INSERT_ACK_MISMATCH")
    return {
        "status": "INSERTED" if inserted else "ALREADY_EXISTS",
        "record_id": expected["record_id"],
        "kind": expected["kind"],
        "sha256": expected["content_sha256"],
        "readback_verified": True,
        "branch_id": TEST_BRANCH_ID,
        "production_connected": False,
        "native_chat_automation_verified": False,
    }
