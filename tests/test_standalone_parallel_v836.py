"""v8.3.7 offline process-crash/restart, durable SQLite and parallel tests."""
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.standalone_parallel_v836 import (
    DEFAULT_REQUESTED_PROCESSES, MAX_PROCESSES, VERSION, choose_processes, run_parallel,
    runtime_process_ceiling,
)


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
        self.assertEqual(VERSION, "8.3.10")
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
        for opts in ({"processes": 0}, {"processes": 257},
                     {"processes": True}, {"per_process": 0},
                     {"per_process": 17}, {"per_process": True}):
            with self.assertRaises(ValueError):
                run_parallel(self.db, **opts)
        with self.assertRaisesRegex(ValueError, "PERSISTENT_DB_PATH_REQUIRED"):
            run_parallel(":memory:")



    def test_adaptive_process_count_caps_to_backlog(self):
        self.assertEqual(choose_processes("auto", 0, 4, resource_cap=64), 1)
        self.assertEqual(choose_processes("auto", 3, 4, resource_cap=64), 1)
        self.assertEqual(choose_processes("auto", 64, 4, resource_cap=64), 16)
        self.assertEqual(choose_processes(256, 64, 4, resource_cap=8), 8)
        self.assertEqual(choose_processes(32, 64, 4, resource_cap=64), 16)
        self.assertEqual(MAX_PROCESSES, 256)
        with self.assertRaisesRegex(ValueError, "INVALID_RESOURCE_LIMIT"):
            choose_processes("auto", 12, 4, resource_cap=0)

    def test_cpu_quota_caps_resource_ceiling(self):
        with mock.patch("tools.standalone_parallel_v836._cpu_capacity", return_value=2), \
             mock.patch("tools.standalone_parallel_v836._memory_capacity", return_value=80):
            self.assertEqual(runtime_process_ceiling(), 4)
            self.assertEqual(choose_processes(256, 1000, 4), 4)

    def test_memory_quota_caps_processes(self):
        with mock.patch("tools.standalone_parallel_v836._cpu_capacity", return_value=64), \
             mock.patch("tools.standalone_parallel_v836._memory_capacity", return_value=3):
            self.assertEqual(runtime_process_ceiling(), 3)
            self.assertEqual(choose_processes("auto", 80, 4), 3)

    def test_auto_processes_honor_small_queue_and_persist_metrics(self):
        self.add("synthetic-v83-v838-automatic")
        with mock.patch("tools.standalone_parallel_v836.runtime_process_ceiling",
                        return_value=16):
            report = run_parallel(self.db, processes="auto", per_process=4)
        self.assertEqual(report["version"], "8.3.10")
        self.assertEqual(report["processes_started"], 1)
        self.assertEqual(report["processes_requested"], "auto")
        self.assertGreater(report["elapsed_ms"], 0)
        self.assertGreater(report["throughput_jobs_per_sec"], 0)
        self.assertEqual(report["queue_state"], {"SUCCEEDED": 1})


    def test_workload_profiles_effective_cpu_cap(self):
        with mock.patch("tools.standalone_parallel_v836._cpu_capacity", return_value=3), \
             mock.patch("tools.standalone_parallel_v836._memory_capacity", return_value=100):
            self.assertEqual(runtime_process_ceiling("cpu"), 3)
            self.assertEqual(runtime_process_ceiling("mixed"), 6)
            self.assertEqual(runtime_process_ceiling("waiting"), 12)
            self.assertEqual(choose_processes("auto", 100, 4, profile="cpu"), 3)
            self.assertEqual(choose_processes("auto", 100, 4, profile="waiting"), 12)
        with self.assertRaisesRegex(ValueError, "INVALID_WORKLOAD_PROFILE"):
            choose_processes("auto", 10, 4, profile="external")
        with self.assertRaisesRegex(ValueError, "INVALID_WORKLOAD_PROFILE"):
            run_parallel(self.db, profile="external")

    def test_cgroup_memory_remaining_is_not_total_quota(self):
        from tools.standalone_parallel_v836 import _memory_capacity
        mib = 1024 * 1024
        with mock.patch("tools.standalone_parallel_v836._read_cgroup_number",
                        side_effect=lambda path: (1024*mib if path.endswith("memory.max")
                                                 else 640*mib)):
            self.assertEqual(_memory_capacity(), 1)  # only 384MiB free, 256MiB reserved
        with mock.patch("tools.standalone_parallel_v836._read_cgroup_number",
                        side_effect=lambda path: (2048*mib if path.endswith("memory.max")
                                                 else 512*mib)):
            self.assertEqual(_memory_capacity(), 13)
        with mock.patch("tools.standalone_parallel_v836._read_cgroup_number",
                        side_effect=lambda path: (1024*mib if path.endswith("memory.max")
                                                 else None)):
            self.assertEqual(_memory_capacity(), 1)  # fail closed on no usage evidence

    def test_profile_report_is_explicit_hint_not_real_workload(self):
        self.add("synthetic-v83-v839-profile")
        with mock.patch("tools.standalone_parallel_v836._cpu_capacity", return_value=2), \
             mock.patch("tools.standalone_parallel_v836._memory_capacity", return_value=12):
            report = run_parallel(self.db, profile="cpu")
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["workload_profile_hint"], "cpu")
        self.assertEqual(report["processes_started"], 1)
        self.assertEqual(self.queue.get("synthetic-v83-v839-profile")["attempt"], 1)


    def test_default_64_requested_but_cpu_memory_cap_still_enforced(self):
        self.assertEqual(DEFAULT_REQUESTED_PROCESSES, 64)
        self.assertEqual(choose_processes(64, 256, 4, resource_cap=64), 64)
        self.assertEqual(choose_processes(64, 256, 4, resource_cap=8), 8)
        self.assertEqual(choose_processes(64, 2, 4, resource_cap=64), 1)
        self.assertEqual(choose_processes(64, 256, 4, resource_cap=1), 1)
        for i in range(12):
            self.add(f"synthetic-v83-v8310-cap-{i}")
        with mock.patch("tools.standalone_parallel_v836.runtime_process_ceiling",
                        return_value=2):
            report = run_parallel(self.db)
        self.assertEqual(report["processes_requested"], 64)
        self.assertEqual(report["processes_started"], 2)
        self.assertEqual(report["succeeded"], 8)
        self.assertEqual(report["queue_state"], {"SUCCEEDED": 8, "QUEUED": 4})
        self.assertEqual(report["verdict"], "PARTIAL")

    def test_explicit_64_request_drains_all_synthetic_jobs_without_duplicates(self):
        tasks = [f"synthetic-v83-v8310-job-{i}" for i in range(64)]
        for name in tasks:
            self.add(name)
        reports = []
        while self.queue.summary().get("QUEUED", 0):
            report = run_parallel(self.db, processes=64, per_process=4)
            self.assertIn(report["verdict"], {"PASS", "PARTIAL"})
            self.assertEqual(report["child_failures"], 0)
            self.assertEqual(report["lease_conflicts"], 0)
            self.assertLessEqual(report["processes_started"], 64)
            reports.append(report)
            self.assertLess(len(reports), 17)
        self.assertEqual(sum(v["succeeded"] for v in reports), 64)
        self.assertEqual(DurableLeaseQueue(self.db).summary(), {"SUCCEEDED": 64})
        self.assertTrue(all(self.queue.get(name)["attempt"] == 1 for name in tasks))
        self.assertEqual(run_parallel(self.db)["claimed"], 0)

    def test_killed_real_claiming_process_recovers_after_lease_expiry(self):
        """A real child claims work, is SIGKILLed, then a new batch resumes it."""
        name = "synthetic-v83-v837-crashed"
        self.add(name)
        marker = os.path.join(self.tmp.name, "claim.marker")
        code = (
            "import sys,time\n"
            "from pathlib import Path\n"
            "from tools.durable_queue_v831 import DurableLeaseQueue\n"
            "q=DurableLeaseQueue(sys.argv[1])\n"
            "lease=q.claim('crashed-v837',lease_seconds=1)\n"
            "assert lease is not None and lease['attempt']==1\n"
            "Path(sys.argv[2]).write_text('CLAIMED')\n"
            "time.sleep(30)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", code, self.db, marker],
            cwd=os.getcwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not os.path.exists(marker) and time.monotonic() < deadline:
                if child.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue(os.path.exists(marker), "CHILD_CLAIM_NOT_OBSERVED")
            self.assertIsNone(child.poll())
            owned = self.queue.get(name)
            self.assertEqual(owned["state"], "CLAIMED")
            expiry = owned["lease_until"]
        finally:
            if child.poll() is None:
                child.kill()  # This is only this test's own offline child.
            child.wait(timeout=5)

        self.assertNotEqual(child.returncode, 0)
        time.sleep(max(0.0, expiry - time.time() + 0.2))
        result = run_parallel(self.db, processes=4, per_process=2)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["recovered_requeued"], 1)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["lease_conflicts"], 0)
        final = DurableLeaseQueue(self.db).get(name)
        self.assertEqual(final["state"], "SUCCEEDED")
        self.assertEqual(final["attempt"], 2)
        self.assertEqual(run_parallel(self.db)["claimed"], 0)

    def test_unexpired_lease_not_stolen_by_parallel_workers(self):
        name = "synthetic-v83-v837-owned"
        self.add(name)
        own = self.queue.claim("still-alive", lease_seconds=60)
        self.assertEqual(own["attempt"], 1)
        report = run_parallel(self.db, processes=4, per_process=4)
        self.assertEqual(report["verdict"], "PARTIAL")
        self.assertEqual(report["claimed"], 0)
        self.assertEqual(report["recovered_requeued"], 0)
        self.assertEqual(report["queue_state"], {"CLAIMED": 1})
        self.assertEqual(self.queue.get(name)["lease_owner"], "still-alive")

    def test_child_timeout_is_unverified_and_does_not_log_secret(self):
        self.add("synthetic-v83-v836-timeout")
        with mock.patch("tools.standalone_parallel_v836.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("DO_NOT_LOG_SECRET", 30)):
            report = run_parallel(self.db, processes=1)
        self.assertEqual(report["verdict"], "UNVERIFIED")
        self.assertEqual(report["child_failures"], 1)
        self.assertNotIn("SECRET", str(report))
        self.assertEqual(self.queue.get("synthetic-v83-v836-timeout")["state"], "QUEUED")
