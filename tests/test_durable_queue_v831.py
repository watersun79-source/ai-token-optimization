"""Offline v8.3.1 durability tests: no network, no model, no scheduler mutations."""
import concurrent.futures
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

from tools.durable_queue_v831 import DurableLeaseQueue, VERSION


def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


class DurableLeaseQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "jobs.sqlite3")
        self.clock = Clock()
        self.q = DurableLeaseQueue(self.path, self.clock)

    def add(self, id="job-1", kind="offline_check"):
        return self.q.enqueue(id, kind, digest(id))

    def test_version_and_persistent_path(self):
        self.assertEqual(VERSION, "8.3.1")
        with self.assertRaisesRegex(ValueError, "PERSISTENT_DB_PATH_REQUIRED"):
            DurableLeaseQueue(":memory:")

    def test_reopen_keeps_queued_job(self):
        self.add()
        restarted = DurableLeaseQueue(self.path, self.clock)
        self.assertEqual(restarted.get("job-1")["state"], "QUEUED")
        claimed = restarted.claim("worker-b")
        self.assertEqual(claimed["task_id"], "job-1")
        self.assertEqual(claimed["attempt"], 1)

    def test_actual_child_process_crash_recovery(self):
        snippet = (
            "import sys\n"
            "from tools.durable_queue_v831 import DurableLeaseQueue\n"
            "q = DurableLeaseQueue(sys.argv[1],clock=lambda:100.0)\n"
            "q.enqueue('crash-job','offline_check',sys.argv[2])\n"
            "c=q.claim('crashed-worker',30)\n"
            "assert c['attempt']==1\n"
        )
        child = subprocess.run(
            [sys.executable, "-c", snippet, self.path, digest("crash-job")],
            cwd=os.getcwd(), capture_output=True, text=True, check=False, timeout=10
        )
        self.assertEqual(child.returncode, 0, child.stderr[:300])
        resumed = DurableLeaseQueue(self.path, self.clock)
        self.assertEqual(resumed.get("crash-job")["state"], "CLAIMED")
        self.assertEqual(resumed.recover()["requeued"], 0)
        self.clock.t = 131
        self.assertEqual(resumed.recover()["requeued"], 1)
        next_claim = resumed.claim("recovery-worker", 30)
        self.assertEqual(next_claim["task_id"], "crash-job")
        self.assertEqual(next_claim["attempt"], 2)
        self.assertTrue(resumed.complete(
            "crash-job", "recovery-worker", next_claim["lease_token"], success=True
        ))
        self.assertEqual(DurableLeaseQueue(self.path, self.clock).get("crash-job")["state"], "SUCCEEDED")

    def test_active_lease_not_stolen(self):
        self.add()
        claim = self.q.claim("owner", 50)
        self.clock.t = 149
        self.assertEqual(DurableLeaseQueue(self.path, self.clock).recover()["requeued"], 0)
        self.assertIsNone(DurableLeaseQueue(self.path, self.clock).claim("other"))
        self.assertEqual(self.q.get("job-1")["lease_owner"], "owner")

    def test_expired_owner_token_fenced_out(self):
        self.add()
        old = self.q.claim("old", 10)
        self.clock.t = 111
        new = DurableLeaseQueue(self.path, self.clock).claim("new", 10)
        self.assertNotEqual(old["lease_token"], new["lease_token"])
        self.assertFalse(self.q.complete("job-1", "old", old["lease_token"], success=True))
        self.assertFalse(self.q.heartbeat("job-1", "old", old["lease_token"], 10))
        self.assertTrue(self.q.complete("job-1", "new", new["lease_token"], success=True))

    def test_heartbeat_extends_lease(self):
        self.add()
        c = self.q.claim("worker", 10)
        self.clock.t = 109
        self.assertTrue(self.q.heartbeat("job-1", "worker", c["lease_token"], 20))
        self.clock.t = 112
        self.assertEqual(self.q.recover()["requeued"], 0)
        self.clock.t = 130
        self.assertEqual(self.q.recover()["requeued"], 1)

    def test_expired_final_attempt_dead_letters(self):
        q = DurableLeaseQueue(self.path, self.clock, max_attempts=1)
        q.enqueue("one", "read_only", digest("one"))
        q.claim("one-worker", 10)
        self.clock.t = 111
        self.assertEqual(q.recover(), {"requeued": 0, "dead": 1})
        self.assertEqual(q.get("one")["state"], "DEAD")
        self.assertIsNone(q.claim("other"))

    def test_retryable_completion_requeues_then_dead(self):
        q = DurableLeaseQueue(self.path, self.clock, max_attempts=2)
        q.enqueue("retry", "read_only", digest("retry"))
        a = q.claim("worker")
        self.assertTrue(q.complete("retry", "worker", a["lease_token"], success=False, retryable=True))
        b = q.claim("worker")
        self.assertEqual(b["attempt"], 2)
        self.assertTrue(q.complete("retry", "worker", b["lease_token"], success=False, retryable=True))
        self.assertEqual(q.get("retry")["state"], "DEAD")
        self.assertIsNone(q.claim("worker"))

    def test_idempotent_intake_and_conflicting_payload(self):
        self.assertTrue(self.add()["created"])
        self.assertFalse(self.add()["created"])
        with self.assertRaisesRegex(ValueError, "IDEMPOTENCY_PAYLOAD_CONFLICT"):
            self.q.enqueue("job-1", "offline_check", digest("different"))
        self.assertEqual(self.q.summary(), {"QUEUED": 1})

    def test_atomic_claim_across_independent_connections(self):
        for i in range(12):
            self.add("concurrent-" + str(i))
        def competing(i):
            return DurableLeaseQueue(self.path, self.clock).claim("worker-" + str(i), 100)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            claims = list(pool.map(competing, range(12)))
        names = [x["task_id"] for x in claims if x]
        self.assertEqual(len(names), 12)
        self.assertEqual(len(set(names)), 12)
        self.assertEqual(self.q.summary(), {"CLAIMED": 12})

    def test_claim_requeues_expired_jobs_automatically(self):
        self.add()
        a = self.q.claim("before", 10)
        self.clock.t = 111
        b = self.q.claim("after", 10)
        self.assertEqual(b["task_id"], a["task_id"])
        self.assertEqual(b["attempt"], 2)

    def test_invalid_or_risky_jobs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ID"):
            self.q.enqueue("../escape", "read_only", digest("bad"))
        with self.assertRaisesRegex(ValueError, "UNSAFE_OR_INVALID_TASK"):
            self.q.enqueue("bad-kind", "write", digest("bad"))
        with self.assertRaisesRegex(ValueError, "UNSAFE_OR_INVALID_TASK"):
            self.q.enqueue("bad-hash", "read_only", "raw payload")

    def test_result_text_secrets_cannot_be_logged_as_code(self):
        self.add()
        c = self.q.claim("worker", 100)
        with self.assertRaisesRegex(ValueError, "INVALID_COMPLETION"):
            self.q.complete("job-1", "worker", c["lease_token"], success=True,
                            result_code="secret=do-not-log")
        self.assertTrue(self.q.complete("job-1", "worker", c["lease_token"], success=True))
        self.assertEqual(self.q.get("job-1")["result_code"], "OK")

    def test_terminal_job_prevents_double_completion(self):
        self.add()
        c = self.q.claim("worker")
        self.assertTrue(self.q.complete("job-1", "worker", c["lease_token"], success=True))
        self.assertFalse(self.q.complete("job-1", "worker", c["lease_token"], success=True))
        self.assertIsNone(self.q.claim("other"))

    def test_invalid_attempts_and_leases_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ATTEMPT_BOUND"):
            DurableLeaseQueue(self.path, self.clock, max_attempts=0)
        self.add()
        with self.assertRaisesRegex(ValueError, "INVALID_LEASE_SECONDS"):
            self.q.claim("worker", 10000)
        with self.assertRaisesRegex(ValueError, "INVALID_LEASE_SECONDS"):
            self.q.claim("worker", 0)
