#!/usr/bin/env python3
"""Free, local-first Markdown memory and evidence audit.

Design adapted from tigerless-labs/agent-memory (Markdown truth + disposable
SQLite FTS cache) and langchain-ai/langgraph (run-bound checkpoint provenance).
No API calls, no access to ChatGPT's internal scheduled task logs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 512000
SHA_RE = re.compile(r"^[a-fA-F0-9]{40}$")
TS_RE = re.compile(r"^\d{10}\.\d{6}$")
TOKENS = re.compile(r"[^\W_]+", re.UNICODE)
SECRET_RE = re.compile(r"\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{15,}|gh[pousr]_[A-Za-z0-9]{15,})\b")
KINDS = ("memory_index", "memory_protocol", "latest_report", "slack_thread")


def clean(text):
    return SECRET_RE.sub("[REDACTED_SECRET]", text)


def connect(db_file):
    db_file.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(db_file))
    db.execute("CREATE TABLE IF NOT EXISTS versions(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(path UNINDEXED, content, sha256 UNINDEXED, tokenize='unicode61')")
    db.commit()
    return db


def sync(db_file, files):
    if not files:
        raise ValueError("At least one local Markdown source is required")
    changed = 0
    untouched = 0
    entries = []
    with connect(db_file) as db:
        for filename in files:
            source = filename.resolve(strict=True)
            if not source.is_file() or source.suffix.lower() not in (".md", ".txt"):
                raise ValueError("Markdown/text source required")
            if source.stat().st_size > MAX_BYTES:
                raise ValueError("Source exceeds size limit")
            body = clean(source.read_text(encoding="utf-8"))
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            path = str(source)
            previous = db.execute("SELECT sha256 FROM versions WHERE path=?", (path,)).fetchone()
            if previous and previous[0] == digest:
                untouched += 1
            else:
                db.execute("DELETE FROM memories WHERE path=?", (path,))
                db.execute("INSERT INTO memories(path,content,sha256) VALUES(?,?,?)", (path, body, digest))
                db.execute("INSERT INTO versions(path,sha256) VALUES(?,?) ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256", (path, digest))
                changed += 1
            entries.append({"path": path, "sha256": digest})
        db.commit()
    return {"changed": changed, "unchanged": untouched, "sources": entries}


def recall(db_file, query, limit=3):
    if not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    words = TOKENS.findall(query)[:12]
    if not words or not db_file.exists():
        return []
    expression = " OR ".join('"' + x + '"' for x in words)
    with connect(db_file) as db:
        rows = db.execute("SELECT path,sha256,snippet(memories,1,'','','…',12),bm25(memories) FROM memories WHERE memories MATCH ? ORDER BY bm25(memories) LIMIT ?", (expression, limit)).fetchall()
        if not rows:
            rows = db.execute("SELECT path,sha256,substr(content,1,360),0 FROM memories WHERE content LIKE ? LIMIT ?", ("%" + words[0] + "%", limit)).fetchall()
    return [{"path": p, "sha256": h, "excerpt": clean(snippet)[:360], "rank": round(float(score), 6)} for p, h, snippet, score in rows]


def audit(payload):
    """Validate claims, not authenticity of the supplied evidence manifest."""
    errors = []
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    rid = run.get("official_run_id")
    if run.get("source") != "scheduled":
        errors.append("run_source_not_scheduled")
    if not isinstance(rid, str) or not rid.strip():
        errors.append("official_run_id_missing")
    if not run.get("automation_id"):
        errors.append("automation_id_missing")
    try:
        begin = datetime.fromisoformat(str(run["started_at"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(run["ended_at"]).replace("Z", "+00:00"))
        if begin.tzinfo is None or end.tzinfo is None or begin > end:
            raise ValueError("bad window")
    except (KeyError, TypeError, ValueError):
        begin = end = None
        errors.append("invalid_run_window")
    seen = set()
    for ev in events:
        if not isinstance(ev, dict):
            errors.append("malformed_event")
            continue
        kind = ev.get("kind")
        if kind not in KINDS or kind in seen:
            errors.append("unexpected_or_duplicate_kind")
            continue
        seen.add(kind)
        if ev.get("run_id") != rid or not rid:
            errors.append(kind + ":run_id_mismatch")
        if ev.get("ok") is not True or not ev.get("tool") or not ev.get("resource"):
            errors.append(kind + ":tool_or_resource_missing")
        if kind == "slack_thread":
            if not TS_RE.fullmatch(str(ev.get("message_ts", ""))):
                errors.append(kind + ":invalid_message_ts")
        elif not SHA_RE.fullmatch(str(ev.get("blob_sha", ""))):
            errors.append(kind + ":invalid_blob_sha")
        try:
            observed = datetime.fromisoformat(str(ev["observed_at"]).replace("Z", "+00:00"))
            if begin is None or end is None or observed.tzinfo is None or not begin <= observed <= end:
                raise ValueError("not same run window")
        except (KeyError, TypeError, ValueError):
            errors.append(kind + ":invalid_event_time")
    for kind in KINDS:
        if kind not in seen:
            errors.append(kind + ":missing")
    if payload.get("official_log_origin") != "platform_original_run_log":
        errors.append("original_platform_log_missing")
    return {"status": "PASS_SCHEMA_ONLY" if not errors else "UNVERIFIED", "errors": list(dict.fromkeys(errors)), "note": "Schema validation cannot authenticate claimed platform origin."}


def main():
    parser = argparse.ArgumentParser(description="Local-only Markdown recall and execution evidence guard")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sync")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("sources", nargs="+", type=Path)
    p = sub.add_parser("recall")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=3)
    p = sub.add_parser("audit")
    p.add_argument("manifest", type=Path)
    args = parser.parse_args()
    result = sync(args.db, args.sources) if args.cmd == "sync" else recall(args.db, args.query, args.limit) if args.cmd == "recall" else audit(json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
