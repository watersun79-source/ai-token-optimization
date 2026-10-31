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
VERSION = "8.5.0-isolated-candidate"
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
    if not isinstance(test_branch_id, str) or not test_branch_id.startswith("br-"):
        raise ValueError("EXPLICIT_TEST_BRANCH_REQUIRED")
    if test_branch_id == "br-solitary-firefly-azge9w3x":
        raise ValueError("MAIN_BRANCH_BLOCKED")
    selected = select_event(event)
    if selected is None:
        return {"status": "SKIPPED", "reason": "NOT_SELECTED"}
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
    if not isinstance(test_branch_id, str) or not test_branch_id.startswith("br-") or test_branch_id == "br-solitary-firefly-azge9w3x":
        raise ValueError("EXPLICIT_TEST_BRANCH_REQUIRED")
    project_key = _clean(project_key, limit=120)
    if not PROJECT.fullmatch(project_key) or type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("INVALID_RESTORE_REQUEST")
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
