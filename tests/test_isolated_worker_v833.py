"""v8.3.3: actual independent local worker process and bounded batch tests."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.isolated_worker_v833 import VERSION, run_batch


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "durable-jobs.sqlite3")
        self.queue = DurableLeaseQueue(self.path)

    def add(self, name):
        return self.queue.enqueue(name, "offline_check", digest(name))

    def test_version_is_explicitly_not_production(self):
        self.assertEqual(VERSION, "8.3.3")
        data = run_batch(self.path)
        self.assertEqual(data["claimed"], 0)
        self.assertFalse(data["production_connected"])
        self.assertFalse(data["render_worker_deployed"])

    def test_real_subprocess_claims_and_persists_results(self):
        self.add("synthetic-v83-worker-a")
        self.add("synthetic-v83-worker-b")
        child = subprocess.run([sys.executable, "-m", "tools.isolated_worker_v833",
                                "--db", self.path, "--limit", "2",
                                "--concurrency", "2"],
                               capture_output=True, text=True, cwd=os.getcwd(),
                               timeout=15, check=False)
        self.assertEqual(child.returncode, 0, child.stderr[:250])
        report = json.loads(child.stdout)
        self.assertEqual(report["claimed"], 2)
        self.assertEqual(report["succeeded"], 2)
        self.assertEqual(report["scope"], "LOCAL_SYNTHETIC_ONLY")
        fresh = DurableLeaseQueue(self.path)
        self.assertEqual(fresh.get("synthetic-v83-worker-a")["state"], "SUCCEEDED")
        self.assertEqual(fresh.get("synthetic-v83-worker-b")["state"], "SUCCEEDED")

    def test_multiple_jobs_execute_concurrently(self):
        for i in range(2):
            self.add("synthetic-v83-parallel-" + str(i))
        barrier = threading.Barrier(2, timeout=3)
        lock = threading.Lock()
        active = [0, 0]

        def overlap(job):
            with lock:
                active[0] += 1
                active[1] = max(active[1], active[0])
            barrier.wait()
            with lock:
                active[0] -= 1
            return True

        report = run_batch(self.path, limit=2, concurrency=2, check=overlap)
        self.assertEqual(report["succeeded"], 2)
        self.assertEqual(active[1], 2)

    def test_unsupported_job_dies_without_running_handler(self):
        self.queue.enqueue("private-work", "read_only", digest("private-work"))
        invoked = []

        def unsafe_handler(job):
            invoked.append(job)
            return True

        report = run_batch(self.path, check=unsafe_handler)
        self.assertEqual(report["dead"], 1)
        self.assertFalse(invoked)
        self.assertEqual(self.queue.get("private-work")["state"], "DEAD")

    def test_handler_errors_do_not_escape_and_mark_dead(self):
        self.add("synthetic-v83-error")
        def bad(_):
            raise ValueError("PRIVATE_TOKEN_MUST_NOT_LEAK")
        report = run_batch(self.path, check=bad)
        self.assertEqual(report["dead"], 1)
        self.assertNotIn("PRIVATE_TOKEN", json.dumps(report))
        self.assertEqual(self.queue.get("synthetic-v83-error")["state"], "DEAD")

    def test_repeated_run_does_not_execute_completed_job(self):
        self.add("synthetic-v83-once")
        a = run_batch(self.path)
        b = run_batch(self.path)
        self.assertEqual(a["succeeded"], 1)
        self.assertEqual(b["claimed"], 0)
        self.assertEqual(self.queue.summary(), {"SUCCEEDED": 1})

    def test_recover_abandoned_claim_after_restart(self):
        q = DurableLeaseQueue(self.path, clock=lambda: 1.0)
        self.add("synthetic-v83-abandoned")
        old = q.claim("dead-worker", lease_seconds=3)
        self.assertEqual(old["attempt"], 1)
        report = run_batch(self.path, worker_id="restarted-worker")
        self.assertEqual(report["recovered"]["requeued"], 1)
        self.assertEqual(report["succeeded"], 1)
        self.assertEqual(self.queue.get("synthetic-v83-abandoned")["attempt"], 2)

    def test_bounded_batch_only_claims_requested_jobs(self):
        for i in range(6):
            self.add("synthetic-v83-batch-" + str(i))
        report = run_batch(self.path, limit=3, concurrency=2)
        self.assertEqual(report["claimed"], 3)
        self.assertEqual(report["queue_state"]["QUEUED"], 3)
        self.assertEqual(report["queue_state"]["SUCCEEDED"], 3)

    def test_limits_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "INVALID_BATCH_LIMIT"):
            run_batch(self.path, limit=100)
        with self.assertRaisesRegex(ValueError, "INVALID_WORKER_CONCURRENCY"):
            run_batch(self.path, concurrency=0)
        with self.assertRaisesRegex(ValueError, "INVALID_WORKER_ID"):
            run_batch(self.path, worker_id="bad/worker")
