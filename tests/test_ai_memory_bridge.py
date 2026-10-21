"""Regression tests for the local-first memory bridge; no network or paid API."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "ai_memory_bridge.py"
spec = importlib.util.spec_from_file_location("memory_bridge", SOURCE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class MemoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.db = self.path / "cache.sqlite"
        self.doc = self.path / "MEMORY.md"
        self.doc.write_text("AI 예약 기억 복원 우선, 매시간 정각 유지.\n비밀 sk-proj-12345678901234567890", encoding="utf-8")

    def test_incremental_index_and_recall(self):
        self.assertEqual(bridge.sync(self.db, [self.doc])["changed"], 1)
        self.assertEqual(bridge.sync(self.db, [self.doc])["unchanged"], 1)
        self.assertTrue(bridge.recall(self.db, "예약"))

    def test_no_plain_secret_in_cache(self):
        import sqlite3
        bridge.sync(self.db, [self.doc])
        with sqlite3.connect(self.db) as db:
            text = db.execute("SELECT content FROM memories").fetchone()[0]
        self.assertNotIn("sk-proj-12345678901234567890", text)

    def test_update_replaces_index(self):
        bridge.sync(self.db, [self.doc])
        self.doc.write_text("메모리 검색 새기능", encoding="utf-8")
        self.assertEqual(bridge.sync(self.db, [self.doc])["changed"], 1)
        self.assertTrue(bridge.recall(self.db, "새기능"))

    def test_missing_original_log_rejected(self):
        self.assertIn("original_platform_log_missing", bridge.audit({})["errors"])

    def test_direct_execution_not_scheduled(self):
        self.assertIn("run_source_not_scheduled", bridge.audit({"run": {"source": "direct_user_requested"}})["errors"])

    def test_valid_example_only_schema_passes(self):
        rid = "example-only"
        run = {"source": "scheduled", "official_run_id": rid, "automation_id": "sample", "started_at": "2026-10-21T10:00:00+00:00", "ended_at": "2026-10-21T10:05:00+00:00"}
        events = []
        for kind in bridge.KINDS:
            ev = {"kind": kind, "run_id": rid, "ok": True, "tool": "test-tool", "resource": kind, "observed_at": "2026-10-21T10:01:00+00:00"}
            if kind == "slack_thread":
                ev["message_ts"] = "1792416391.631669"
            else:
                ev["blob_sha"] = "a" * 40
            events.append(ev)
        payload = {"run": run, "events": events, "official_log_origin": "platform_original_run_log"}
        self.assertEqual(bridge.audit(payload)["status"], "PASS_SCHEMA_ONLY")
        events[0]["run_id"] = "previous-run"
        self.assertIn("memory_index:run_id_mismatch", bridge.audit(payload)["errors"])


if __name__ == "__main__":
    unittest.main()
