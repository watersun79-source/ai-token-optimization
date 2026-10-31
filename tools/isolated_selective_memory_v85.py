"""Isolated AI BOT project memory adapter for an explicit, authorized event.

No ChatGPT transcript capture, no background listener, no paid model calls.
Runs only when an existing caller explicitly passes an opted-in goal/result event.
Never point the executor at Neon main: use a dedicated disposable test branch.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Callable, Mapping, Any

TABLE = "public.isolated_project_memory_v85"
VERSION = "8.5.2-isolated-candidate"
# Hardcoded, disposable test deployment only. These are not user-selected at runtime.
TEST_PROJECT_ID = "autumn-frog-53985417"
TEST_BRANCH_ID = "br-billowing-union-azaxxi5p"
TEST_DB_NAME = "aibot_isolated"
PROTECTED_MAIN_BRANCH = "br-solitary-firefly-azge9w3x"
KINDS = frozenset(("goal", "task_result"))
ID = re.compile(r"^[a-z0-9][a-z0-9._-]{4,95}$")
PROJECT = re.compile(r"^project\.ai-bot-[a-z0-9._-]{2,99}$")
# Fail closed on common credential markers in *any* user supplied field.
SECRET = re.compile(
    r"(?i)(?:password|passwd|api[_ -]?key|secret|bearer\s+|"
    r"authorization\s*:|sk-[a-z0-9_-]{8}|postgres(?:ql)?://|"
    r"private[_ -]?key|token\s*[:=])"
)

CREATE_TABLE_TEST_BRANCH_ONLY = """
CREATE TABLE IF NOT EXISTS public.isolated_project_memory_v85 (
    record_id text PRIMARY KEY,
    project_key text NOT NULL CHECK (char_length(project_key) BETWEEN 3 AND 120),
    kind text NOT NULL CHECK (kind IN ('goal','task_result')),
    title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120),
    body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 1200),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now()
)
"""
INSERT_SQL = (
    "INSERT INTO public.isolated_project_memory_v85 "
    "(record_id,project_key,kind,title,body,content_sha256) "
    "VALUES (%s,%s,%s,%s,%s,%s) "
    "ON CONFLICT (record_id) DO NOTHING "
    "RETURNING record_id"
)
READ_SQL = (
    "SELECT record_id,project_key,kind,title,body,content_sha256 "
    "FROM public.isolated_project_memory_v85 "
    "WHERE record_id=%s AND project_key=%s"
)
RESTORE_SQL = (
    "SELECT record_id,project_key,kind,title,body,content_sha256 "
    "FROM public.isolated_project_memory_v85 "
    "WHERE project_key=%s AND kind IN ('goal','task_result') "
    "ORDER BY created_at DESC,record_id LIMIT %s"
)

@dataclass(frozen=True)
class SelectedRecord:
    record_id: str
    project_key: str
    kind: str
    title: str
    body: str
    digest: str

def _clean(value: Any, *, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise ValueError("INVALID_FIELD")
    if value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError("INVALID_FIELD")
    if SECRET.search(value):
        raise ValueError("POSSIBLE_SECRET")
    return value

def select_event(event: Mapping[str, Any]) -> SelectedRecord | None:
    """A deliberate caller-supplied opt-in, never a raw ChatGPT message."""
    if not isinstance(event, Mapping):
        raise ValueError("INVALID_EVENT")
    if event.get("selected") is not True or event.get("kind") not in KINDS:
        return None
    if set(event) != {"selected", "record_id", "project_key", "kind", "title", "body"}:
        raise ValueError("UNEXPECTED_FIELDS")
    record_id = _clean(event["record_id"], limit=96)
    project_key = _clean(event["project_key"], limit=120)
    title = _clean(event["title"], limit=120)
    body = _clean(event["body"], limit=1200)
    if not ID.fullmatch(record_id) or not PROJECT.fullmatch(project_key):
        raise ValueError("INVALID_IDENTIFIER")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return SelectedRecord(record_id, project_key, event["kind"], title, body, digest)

def _match(row: Mapping[str, Any], selected: SelectedRecord) -> bool:
    return all(
        row.get(k) == v for k, v in (
            ("record_id", selected.record_id),
            ("project_key", selected.project_key),
            ("kind", selected.kind),
            ("title", selected.title),
            ("body", selected.body),
            ("content_sha256", selected.digest),
        )
    )

def _require_test_executor(execute: Callable, test_branch_id: str, *, restore: bool = False) -> None:
    """Fail closed when a caller's test-branch claim and executor scope diverge.

    Executor scope metadata must be supplied by the trusted database adapter
    after verifying its own connection configuration, never by user input.
    This guard does not replace least-privilege SQL credentials or transport
    verification. In particular, it must not be confused with real DB auth.
    """
    if test_branch_id == PROTECTED_MAIN_BRANCH:
        raise ValueError("EXPLICIT_TEST_BRANCH_REQUIRED" if restore else "MAIN_BRANCH_BLOCKED")
    if type(test_branch_id) is not str or test_branch_id != TEST_BRANCH_ID:
        raise ValueError("EXPLICIT_TEST_BRANCH_REQUIRED")
    if (getattr(execute, "bound_project_id", None) != TEST_PROJECT_ID
        or getattr(execute, "bound_branch_id", None) != TEST_BRANCH_ID
        or getattr(execute, "bound_database_name", None) != TEST_DB_NAME):
        raise ValueError("EXECUTOR_SCOPE_MISMATCH")

def _verify_test_scope(execute: Callable) -> None:
    """Require a fresh read-only DB scope proof, not merely bound name fields.

    The trusted executor separately re-probes on the same connection as each
    permitted SQL operation. This is a test-only safety defense, not Neon
    authentication or a guarantee of the branch identity.
    """
    probe = getattr(execute, "verify_test_scope", None)
    if not callable(probe) or probe() is not True:
        raise ValueError("BRANCH_PROOF_UNVERIFIED")

def save_selected_event(
    execute: Callable[[str, tuple], list[Mapping[str, Any]]],
    event: Mapping[str, Any],
    *,
    test_branch_id: str,
) -> dict[str, Any]:
    """Store and read back one selected event using a test-branch executor.

    'execute' must be a trusted parameterized PostgreSQL executor scoped to
    test_branch_id. Never pass an executor connected to production/main.
    """
    _require_test_executor(execute, test_branch_id)
    selected = select_event(event)
    if selected is None:
        return {"status": "SKIPPED", "reason": "NOT_SELECTED"}
    _verify_test_scope(execute)
    inserted = execute(INSERT_SQL, (
        selected.record_id, selected.project_key, selected.kind,
        selected.title, selected.body, selected.digest,
    ))
    if len(inserted) > 1:
        raise RuntimeError("INVALID_INSERT_RESULT")
    rows = execute(READ_SQL, (selected.record_id, selected.project_key))
    if len(rows) != 1 or not _match(rows[0], selected):
        raise RuntimeError("READBACK_MISMATCH")
    return {
        "status": "INSERTED" if inserted else "ALREADY_EXISTS",
        "record_id": selected.record_id,
        "kind": selected.kind,
        "sha256": selected.digest,
        "readback_verified": True,
        "branch_id": test_branch_id,
        "production_connected": False,
    }

def restore_project_records(
    execute: Callable[[str, tuple], list[Mapping[str, Any]]],
    project_key: str,
    *,
    test_branch_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    _require_test_executor(execute, test_branch_id, restore=True)
    project_key = _clean(project_key, limit=120)
    if not PROJECT.fullmatch(project_key) or type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("INVALID_RESTORE_REQUEST")
    _verify_test_scope(execute)
    rows = execute(RESTORE_SQL, (project_key, limit))
    restored: list[dict[str, Any]] = []
    for row in rows:
        if row.get("project_key") != project_key or row.get("kind") not in KINDS:
            raise RuntimeError("RESTORE_SCOPE_MISMATCH")
        body = _clean(row.get("body"), limit=1200)
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != row.get("content_sha256"):
            raise RuntimeError("RESTORE_HASH_MISMATCH")
        restored.append({
            "record_id": row["record_id"],
            "kind": row["kind"],
            "title": row["title"],
            "body": body,
            "sha256": row["content_sha256"],
        })
    return restored
