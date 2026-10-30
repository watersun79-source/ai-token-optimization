"""v8.3.6 offline real child-process SQLite integration and regression tests."""
import hashlib
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.standalone_parallel_v836 import VERSION, run_parallel


class StandaloneParallelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "jobs.sqlite3")
        self.queue = DurableLeaseQueue(self.db)

    def add(self, id, kind="offline_check"):
        return self.queue.enqueue(id, kind, hashlib.sha256(id.encode()).hexdigest())

    def test_four_real_child_processes_persist_without_double_claims(self):
        names = [f"synthetic-v83-v836-{i}" for i in range(20)]
        for name in names:
            self.add(name)
        report = run_parallel(self.db, processes=4, per_process=5)
        self.assertEqual(VERSION, "8.3.6")
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["processes_reported"], 4)
        self.assertEqual(report["succeeded"], 20)
        self.assertEqual(report["claimed"], 20)
        self.assertEqual(report["lease_conflicts"], 0)
        self.assertFalse(report["neon_connected"])
        self.assertFalse(report["unattended_24h_verified"])
        fresh = DurableLeaseQueue(self.db)
        self.assertEqual(fresh.summary(), {"SUCCEEDED": 20})
        self.assertTrue(all(fresh.get(name)["attempt"] == 1 for name in names))

    def test_second_invocation_is_idle_and_does_not_rerun_jobs(self):
        self.add("synthetic-v83-v836-repeat")
        self.assertEqual(run_parallel(self.db, processes=2)["succeeded"], 1)
        second = run_parallel(self.db, processes=4)
        self.assertEqual(second["verdict"], "IDLE")
        self.assertEqual(second["claimed"], 0)
        self.assertEqual(self.queue.get("synthetic-v83-v836-repeat")["attempt"], 1)

    def test_finite_capacity_keeps_unclaimed_jobs_queued(self):
        for i in range(10):
            self.add(f"synthetic-v83-v836-bound-{i}")
        result = run_parallel(self.db, processes=2, per_process=2)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertEqual(result["succeeded"], 4)
        self.assertEqual(result["queue_state"], {"SUCCEEDED": 4, "QUEUED": 6})

    def test_non_synthetic_task_must_not_be_executed(self):
        self.add("not-synthetic", kind="read_only")
        result = run_parallel(self.db, processes=1, per_process=1)
        self.assertEqual(result["verdict"], "FAILED")
        self.assertEqual(result["dead"], 1)
        self.assertEqual(self.queue.get("not-synthetic")["state"], "DEAD")

    def test_boundaries_fail_before_starting_any_child(self):
        for opts in ({"processes": 0}, {"processes": 5},
                     {"processes": True}, {"per_process": 0},
                     {"per_process": 17}, {"per_process": True}):
            with self.assertRaises(ValueError):
                run_parallel(self.db, **opts)
        with self.assertRaisesRegex(ValueError, "PERSISTENT_DB_PATH_REQUIRED"):
            run_parallel(":memory:")

    def test_child_timeout_is_unverified_and_does_not_log_secret(self):
        self.add("synthetic-v83-v836-timeout")
        with mock.patch("tools.standalone_parallel_v836.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("DO_NOT_LOG_SECRET", 30)):
            report = run_parallel(self.db, processes=1)
        self.assertEqual(report["verdict"], "UNVERIFIED")
        self.assertEqual(report["child_failures"], 1)
        self.assertNotIn("SECRET", str(report))
        self.assertEqual(self.queue.get("synthetic-v83-v836-timeout")["state"], "QUEUED")
