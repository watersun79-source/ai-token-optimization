"""Fail-closed, test-only PostgreSQL executor for selected AI BOT memory.

The connection factory must already supply a restricted Neon TEST-branch role,
with TLS enforced by its owner. Never store or retrieve DSNs here.
The preflight is repeated on the SAME connection as each SQL operation.
No scheduling, transcript interception, background traffic, or production use.

A public fixture proves only that the expected test *data* are visible.
It cannot cryptographically prove a Neon branch ID; use branch-scoped
restricted credentials and external Neon metadata verification as well.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tools.isolated_selective_memory_v85 import (
    INSERT_SQL, READ_SQL, RESTORE_SQL,
    TEST_PROJECT_ID, TEST_BRANCH_ID, TEST_DB_NAME,
)

# The TEST branch alone received this fixture AFTER fork from protected main.
# It is intentionally public, not an authentication secret.
SCOPE_MARKER_ID = "synthetic-goal-v85-20261101-01"
SCOPE_MARKER_HASH = "957373978a872a179b386f312205e7983f97baf2c784e8f544fb23409dbf56e7"
TEST_ROLE = "aibot_v85_memory_test_rw"
IDENTITY_SQL = "SELECT current_database(), current_user"
MARKER_SQL = (
    "SELECT content_sha256 FROM public.isolated_project_memory_v85 "
    "WHERE record_id=%s AND project_key=%s AND kind='goal'"
)
ALLOWED_SQL = frozenset((INSERT_SQL, READ_SQL, RESTORE_SQL))

class VerifiedNeonTestExecutor:
    """A single-query transaction with a same-connection scope preflight.

    connect() is a trusted, zero-argument connection factory. A caller must
    configure TLS and least-privilege role credentials out-of-band.
    """
    bound_project_id = TEST_PROJECT_ID
    bound_branch_id = TEST_BRANCH_ID
    bound_database_name = TEST_DB_NAME

    def __init__(self, connect: Callable[[], Any]):
        if not callable(connect):
            raise ValueError("CONNECTION_FACTORY_REQUIRED")
        self._connect = connect

    @staticmethod
    def _probe(cursor: Any) -> None:
        cursor.execute(IDENTITY_SQL)
        identity = cursor.fetchone()
        if identity != (TEST_DB_NAME, TEST_ROLE):
            raise ValueError("DATABASE_IDENTITY_UNVERIFIED")
        cursor.execute(MARKER_SQL, (SCOPE_MARKER_ID, "project.ai-bot-v81"))
        marker = cursor.fetchone()
        if marker != (SCOPE_MARKER_HASH,):
            raise ValueError("BRANCH_SCOPE_UNVERIFIED")

    def verify_test_scope(self) -> bool:
        # Read-only preflight. Never accept a flag supplied by the chat event.
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._probe(cursor)
        return True

    def __call__(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        if sql not in ALLOWED_SQL or type(params) is not tuple:
            raise ValueError("UNAPPROVED_SQL")
        # Guard on the same connection/transaction as every query. A previous
        # successful probe is not a license to trust a later changed DSN.
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._probe(cursor)
                cursor.execute(sql, params)
                desc = cursor.description
                if desc is None:
                    raise RuntimeError("EXPECTED_RESULT_NOT_RETURNED")
                columns = tuple(getattr(col, "name") for col in desc)
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
