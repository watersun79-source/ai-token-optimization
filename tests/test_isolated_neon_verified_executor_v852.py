"""Offline proof that every permitted SQL query checks TEST identity first."""
from types import SimpleNamespace
import unittest

from tools.isolated_neon_verified_executor_v852 import (
    VerifiedNeonTestExecutor, IDENTITY_SQL, MARKER_SQL, TEST_ROLE,
    SCOPE_MARKER_HASH, SCOPE_MARKER_ID,
)
from tools.isolated_selective_memory_v85 import (
    INSERT_SQL, READ_SQL, RESTORE_SQL, save_selected_event,
    TEST_BRANCH_ID, TEST_DB_NAME, TEST_PROJECT_ID,
)

class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.conn.commands.append(sql)
        self.description = None
        if sql == IDENTITY_SQL:
            self.rows = [(self.conn.db, self.conn.role)]
        elif sql == MARKER_SQL:
            self.rows = [(self.conn.marker,)] if self.conn.marker is not None else []
        elif sql == INSERT_SQL:
            *record, = params
            self.conn.rows[record[0]] = {
                "record_id": record[0], "project_key": record[1],
                "kind": record[2], "title": record[3], "body": record[4],
                "content_sha256": record[5],
            }
            self.description = (SimpleNamespace(name="record_id"),)
            self.rows = [(record[0],)]
        elif sql == READ_SQL:
            id_, project = params
            data = self.conn.rows.get(id_)
            names = ("record_id", "project_key", "kind", "title", "body", "content_sha256")
            self.description = tuple(SimpleNamespace(name=n) for n in names)
            self.rows = [tuple(data.get(n) for n in names)] if data and data["project_key"] == project else []
        elif sql == RESTORE_SQL:
            project, limit = params
            names = ("record_id", "project_key", "kind", "title", "body", "content_sha256")
            self.description = tuple(SimpleNamespace(name=n) for n in names)
            self.rows = [
                tuple(r[n] for n in names) for r in self.conn.rows.values()
                if r["project_key"] == project and r["kind"] in ("goal", "task_result")
            ][:limit]
        else:
            raise AssertionError("UNEXPECTED_SQL")

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return self.rows

class FakeConnection:
    def __init__(self, *, db=TEST_DB_NAME, role=TEST_ROLE, marker=SCOPE_MARKER_HASH, rows=None):
        self.db, self.role, self.marker = db, role, marker
        self.rows = rows if rows is not None else {}
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return FakeCursor(self)

class TestBoundNeonExecutor(unittest.TestCase):
    def test_write_preflight_on_exact_same_connection(self):
        connections = []
        shared = {}
        def connect():
            c = FakeConnection(rows=shared)
            connections.append(c)
            return c
        execute = VerifiedNeonTestExecutor(connect)
        outcome = save_selected_event(execute, {
            "selected": True, "record_id": "synthetic-scope-test-v852",
            "project_key": "project.ai-bot-v81", "kind": "goal",
            "title": "Synthetic scope", "body": "Scoped test operation.",
        }, test_branch_id=TEST_BRANCH_ID)
        self.assertEqual(outcome["status"], "INSERTED")
        self.assertTrue(outcome["readback_verified"])
        self.assertGreaterEqual(len(connections), 3)  # outer scope, insert, readback
        for c in connections:
            self.assertEqual(c.commands[:2], [IDENTITY_SQL, MARKER_SQL])
        self.assertIn(INSERT_SQL, connections[-2].commands)
        self.assertIn(READ_SQL, connections[-1].commands)

    def test_wrong_role_denies_every_operation(self):
        connections = []
        def connect():
            c = FakeConnection(role="aibot_isolated_owner")
            connections.append(c)
            return c
        execute = VerifiedNeonTestExecutor(connect)
        with self.assertRaisesRegex(ValueError, "DATABASE_IDENTITY_UNVERIFIED"):
            execute.verify_test_scope()
        with self.assertRaisesRegex(ValueError, "DATABASE_IDENTITY_UNVERIFIED"):
            execute(INSERT_SQL, ("dummy",) * 6)
        self.assertEqual(connections[-1].commands, [IDENTITY_SQL])

    def test_wrong_database_denied(self):
        execute = VerifiedNeonTestExecutor(lambda: FakeConnection(db="otherdb"))
        with self.assertRaisesRegex(ValueError, "DATABASE_IDENTITY_UNVERIFIED"):
            execute.verify_test_scope()

    def test_missing_or_wrong_marker_denied(self):
        for marker in (None, "a"*64):
            with self.subTest(marker=marker):
                execute = VerifiedNeonTestExecutor(lambda: FakeConnection(marker=marker))
                with self.assertRaisesRegex(ValueError, "BRANCH_SCOPE_UNVERIFIED"):
                    execute.verify_test_scope()

    def test_changed_target_after_verification_denied(self):
        connections = []
        def connect():
            c = FakeConnection(role=TEST_ROLE if not connections else "aibot_isolated_owner")
            connections.append(c)
            return c
        execute = VerifiedNeonTestExecutor(connect)
        self.assertTrue(execute.verify_test_scope())
        with self.assertRaisesRegex(ValueError, "DATABASE_IDENTITY_UNVERIFIED"):
            execute(INSERT_SQL, ("dummy",) * 6)
        self.assertEqual(connections[1].commands, [IDENTITY_SQL])

    def test_unapproved_sql_rejected_without_connection(self):
        connections = []
        execute = VerifiedNeonTestExecutor(lambda: connections.append(1))
        for sql, params in (("DROP TABLE x", ()), ("SELECT 1", ()), (INSERT_SQL, [])):
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(ValueError, "UNAPPROVED_SQL"):
                    execute(sql, params)
        self.assertEqual(connections, [])

    def test_executor_metadata_fixed(self):
        obj = VerifiedNeonTestExecutor(lambda: FakeConnection())
        self.assertEqual(obj.bound_branch_id, TEST_BRANCH_ID)
        self.assertEqual(obj.bound_database_name, TEST_DB_NAME)
        self.assertEqual(obj.bound_project_id, TEST_PROJECT_ID)

    def test_no_factory_denied(self):
        with self.assertRaisesRegex(ValueError, "CONNECTION_FACTORY_REQUIRED"):
            VerifiedNeonTestExecutor(None)

if __name__ == "__main__":
    unittest.main()
