"""v8.4.0: verify *256* overlapping async tasks and SQLite idempotency offline."""
import asyncio
import hashlib
import os
import tempfile
import unittest

from tools.async_slots_v840 import MAX_ASYNC_SLOTS, run_async_slots
from tools.durable_queue_v831 import DurableLeaseQueue


class AsyncSlotsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "queue.sqlite3")
        self.q = DurableLeaseQueue(self.db)

    def add(self, name, kind="offline_check"):
        self.q.enqueue(name, kind, hashlib.sha256(name.encode("ascii")).hexdigest())

    def run_slots(self, **kwargs):
        return asyncio.run(run_async_slots(self.db, **kwargs))

    def test_real_256_concurrent_coroutines_and_persisted_results(self):
        names = [f"synthetic-v83-v840-{i:03d}" for i in range(256)]
        for name in names:
            self.add(name)
        r = self.run_slots(slots=256, simulated_wait_ms=100)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["created_coroutines"], 256)
        self.assertEqual(r["peak_in_flight_coroutines"], 256)
        self.assertEqual(r["actual_os_processes"], 1)
        self.assertEqual(r["succeeded"], 256)
        self.assertEqual(r["lease_conflicts"], 0)
        self.assertEqual(r["queue_state"], {"SUCCEEDED": 256})
        self.assertFalse(r["unattended_24h_verified"])
        fresh = DurableLeaseQueue(self.db)
        self.assertTrue(all(fresh.get(name)["attempt"] == 1 for name in names))
        again = self.run_slots(slots=256)
        self.assertEqual(again["verdict"], "IDLE")
        self.assertEqual(again["claimed"], 0)
        self.assertEqual(fresh.summary(), {"SUCCEEDED": 256})

    def test_small_backlog_starts_only_what_exists(self):
        for i in range(3):
            self.add(f"synthetic-v83-v840-small-{i}")
        r = self.run_slots(slots=256, simulated_wait_ms=0)
        self.assertEqual(r["created_coroutines"], 3)
        self.assertEqual(r["peak_in_flight_coroutines"], 3)
        self.assertEqual(r["succeeded"], 3)

    def test_queue_backpressure_does_not_take_more_than_slots(self):
        for i in range(64):
            self.add(f"synthetic-v83-v840-backpressure-{i}")
        r = self.run_slots(slots=16, simulated_wait_ms=10)
        self.assertEqual(r["verdict"], "PARTIAL")
        self.assertEqual(r["succeeded"], 16)
        self.assertEqual(r["queue_state"], {"QUEUED": 48, "SUCCEEDED": 16})
        r2 = self.run_slots(slots=64, simulated_wait_ms=0)
        self.assertEqual(r2["succeeded"], 48)
        self.assertEqual(self.q.summary(), {"SUCCEEDED": 64})

    def test_non_synthetic_work_fails_closed(self):
        self.add("unsafe-user-work", kind="read_only")
        r = self.run_slots(slots=1, simulated_wait_ms=0)
        self.assertEqual(r["verdict"], "FAILED")
        self.assertEqual(r["dead"], 1)
        self.assertEqual(self.q.get("unsafe-user-work")["state"], "DEAD")

    def test_invalid_limits_and_ephemeral_db_rejected(self):
        self.assertEqual(MAX_ASYNC_SLOTS, 256)
        for opts in ({"slots": 0}, {"slots": 257}, {"slots": True},
                     {"simulated_wait_ms": -1}, {"simulated_wait_ms": 501},
                     {"simulated_wait_ms": True}):
            with self.assertRaises(ValueError):
                self.run_slots(**opts)
        with self.assertRaisesRegex(ValueError, "PERSISTENT_DB_PATH_REQUIRED"):
            asyncio.run(run_async_slots(":memory:"))
