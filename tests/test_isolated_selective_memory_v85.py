"""Offline, secret-free verification of explicit selective Neon project memory."""
import hashlib
import unittest

from tools.isolated_selective_memory_v85 import (
    CREATE_TABLE_TEST_BRANCH_ONLY, INSERT_SQL, READ_SQL, RESTORE_SQL,
    restore_project_records, save_selected_event, select_event
)

TEST_BRANCH = "br-billowing-union-azaxxi5p"
MAIN = "br-solitary-firefly-azge9w3x"

def event(kind="goal", **overrides):
    v = {
        "selected": True,
        "record_id": "synthetic-goal-v85-20261101-01",
        "project_key": "project.ai-bot-v81",
        "kind": kind,
        "title": "Synthetic goal",
        "body": "Verify explicit memory save in an isolated branch.",
    }
    v.update(overrides)
    return v

class FakePostgres:
    """Small in-memory executor matching only the three static SQL statements."""
    def __init__(self):
        self.rows = {}
        self.calls = []

    def __call__(self, sql, params):
        self.calls.append((sql, params))
        if sql == INSERT_SQL:
            record_id, project_key, kind, title, body, digest = params
            if record_id in self.rows:
                return []
            self.rows[record_id] = {
                "record_id": record_id, "project_key": project_key,
                "kind": kind, "title": title, "body": body,
                "content_sha256": digest,
            }
            return [{"record_id": record_id}]
        if sql == READ_SQL:
            record_id, project_key = params
            row = self.rows.get(record_id)
            return [dict(row)] if row and row["project_key"] == project_key else []
        if sql == RESTORE_SQL:
            project_key, limit = params
            return [dict(x) for x in self.rows.values()
                    if x["project_key"] == project_key
                    and x["kind"] in ("goal", "task_result")][:limit]
        raise AssertionError("UNEXPECTED_QUERY")

class TestSelectiveProjectMemory(unittest.TestCase):
    def test_selected_goal_save_and_readback(self):
        db = FakePostgres()
        result = save_selected_event(db, event(), test_branch_id=TEST_BRANCH)
        self.assertEqual(result["status"], "INSERTED")
        self.assertTrue(result["readback_verified"])
        self.assertEqual(db.rows[event()["record_id"]]["content_sha256"],
                         hashlib.sha256(event()["body"].encode()).hexdigest())

    def test_task_result_and_restore(self):
        db = FakePostgres()
        save_selected_event(db, event(), test_branch_id=TEST_BRANCH)
        save_selected_event(db, event("task_result", record_id="synthetic-result-v85-20261101-01"),
                            test_branch_id=TEST_BRANCH)
        rows = restore_project_records(db, "project.ai-bot-v81", test_branch_id=TEST_BRANCH)
        self.assertEqual({r["kind"] for r in rows}, {"goal", "task_result"})
        self.assertEqual(len(rows), 2)

    def test_idempotent_same_record(self):
        db = FakePostgres()
        self.assertEqual(save_selected_event(db, event(), test_branch_id=TEST_BRANCH)["status"], "INSERTED")
        self.assertEqual(save_selected_event(db, event(), test_branch_id=TEST_BRANCH)["status"], "ALREADY_EXISTS")
        self.assertEqual(len(db.rows), 1)

    def test_conflicting_payload_fails_closed(self):
        db = FakePostgres()
        save_selected_event(db, event(), test_branch_id=TEST_BRANCH)
        with self.assertRaisesRegex(RuntimeError, "READBACK_MISMATCH"):
            save_selected_event(db, event(body="Edited different goal."), test_branch_id=TEST_BRANCH)
        self.assertEqual(len(db.rows), 1)

    def test_unselected_event_never_touches_db(self):
        db = FakePostgres()
        self.assertEqual(save_selected_event(db, event(selected=False), test_branch_id=TEST_BRANCH)["status"],
                         "SKIPPED")
        self.assertEqual(db.calls, [])

    def test_unapproved_kind_is_skipped(self):
        db = FakePostgres()
        self.assertIsNone(select_event(event(kind="conversation")))
        self.assertEqual(save_selected_event(db, event(kind="transcript"), test_branch_id=TEST_BRANCH)["status"],
                         "SKIPPED")
        self.assertEqual(db.calls, [])

    def test_extra_fields_rejected(self):
        db = FakePostgres()
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_FIELDS"):
            save_selected_event(db, event(chat_transcript="private content"), test_branch_id=TEST_BRANCH)
        self.assertEqual(db.calls, [])

    def test_credential_markers_rejected(self):
        for body in ("password: 123456", "Bearer some-credential", "postgresql://private", "api_key=value",
                     "secret-test", "token = hidden", "sk-abcdefghi"):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, "POSSIBLE_SECRET"):
                    select_event(event(body=body))

    def test_neon_main_branch_blocked_before_io(self):
        db = FakePostgres()
        with self.assertRaisesRegex(ValueError, "MAIN_BRANCH_BLOCKED"):
            save_selected_event(db, event(), test_branch_id=MAIN)
        with self.assertRaisesRegex(ValueError, "EXPLICIT_TEST_BRANCH_REQUIRED"):
            restore_project_records(db, "project.ai-bot-v81", test_branch_id=MAIN)
        self.assertEqual(db.calls, [])

    def test_missing_branch_rejected(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_TEST_BRANCH_REQUIRED"):
            save_selected_event(FakePostgres(), event(), test_branch_id="")

    def test_bad_project_and_control_characters(self):
        for updates in ({"project_key": "personal.chats"}, {"record_id": "x"}, {"body": "line\nbreak"}):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    select_event(event(**updates))

    def test_restore_scope_hash_and_limits(self):
        db = FakePostgres()
        save_selected_event(db, event(), test_branch_id=TEST_BRANCH)
        self.assertEqual(restore_project_records(db, "project.ai-bot-abc", test_branch_id=TEST_BRANCH), [])
        for invalid in (0, 26, True):
            with self.assertRaisesRegex(ValueError, "INVALID_RESTORE_REQUEST"):
                restore_project_records(db, "project.ai-bot-v81", test_branch_id=TEST_BRANCH, limit=invalid)
        db.rows[event()["record_id"]]["body"] = "tampER"
        with self.assertRaisesRegex(RuntimeError, "RESTORE_HASH_MISMATCH"):
            restore_project_records(db, "project.ai-bot-v81", test_branch_id=TEST_BRANCH)

    def test_static_schema_scoped_to_isolated_table(self):
        self.assertIn("isolated_project_memory_v85", CREATE_TABLE_TEST_BRANCH_ONLY)
        self.assertIn("ON CONFLICT (record_id) DO NOTHING", INSERT_SQL)
        self.assertIn("AND kind IN ('goal','task_result')", RESTORE_SQL)

if __name__ == "__main__":
    unittest.main()
