"""Real local HTTP + actual SQLite worker process E2E (no external APIs)."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from tools.durable_queue_v831 import DurableLeaseQueue
from tools.isolated_queue_api_v834 import VERSION


class AuthenticatedQueueTests(unittest.TestCase):
    KEY = "LOCAL_TEST_ONLY_SECRET_0123456789_abcdef"
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "jobs.sqlite3")
        self.proc = None
        self.port = None

    def tearDown(self):
        self._stop()

    def _stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None

    def _start(self, *, secret=True, db=True):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        env = dict(os.environ, PROBE_HOST="127.0.0.1", PORT=str(self.port),
                   ISOLATED_DB_PATH=self.db if db else "",
                   ISOLATED_JOB_KEY=self.KEY if secret else "")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "tools.isolated_queue_api_v834"],
            cwd=os.getcwd(), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(80):
            if self.proc.poll() is not None:
                raise AssertionError("server exited: " + self.proc.stderr.read()[-600:].decode())
            try:
                return self._http("/healthz")[1]
            except (OSError, urllib.error.URLError):
                time.sleep(.04)
        self.fail("gateway did not listen")

    def _http(self, path, *, body=None, key=None, method="GET"):
        payload = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-Queue-Key"] = key
        request = urllib.request.Request(
            "http://127.0.0.1:" + str(self.port) + path,
            data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as ex:
            return ex.code, json.loads(ex.read())

    def test_version_and_fail_closed_without_environment_key(self):
        self.assertEqual(VERSION, "8.3.4")
        status = self._start(secret=False)
        self.assertFalse(status["ingress_configured"])
        self.assertFalse(status["persistent_disk_verified"])
        code, body = self._http("/private/submit", body={
            "task_id": "synthetic-v83-denied", "kind": "offline_check"
        }, key=self.KEY, method="POST")
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "UNAUTHORIZED")

    def test_authenticated_submit_runs_worker_and_commits_same_database(self):
        status = self._start()
        self.assertTrue(status["ingress_configured"])
        code, response = self._http("/private/submit", body={
            "task_id": "synthetic-v83-http-once", "kind": "offline_check"
        }, key=self.KEY, method="POST")
        self.assertEqual(code, 200)
        self.assertTrue(response["new"])
        self.assertEqual(response["state"], "SUCCEEDED")
        self.assertEqual(response["batch"]["succeeded"], 1)
        db = DurableLeaseQueue(self.db)
        self.assertEqual(db.get("synthetic-v83-http-once")["state"], "SUCCEEDED")

    def test_duplicate_http_submission_is_idempotent(self):
        self._start()
        job = {"task_id": "synthetic-v83-dedup", "kind": "offline_check"}
        first = self._http("/private/submit", body=job, key=self.KEY, method="POST")
        second = self._http("/private/submit", body=job, key=self.KEY, method="POST")
        self.assertEqual(first[0], 200)
        self.assertTrue(first[1]["new"])
        self.assertFalse(second[1]["new"])
        self.assertEqual(second[1]["batch"]["claimed"], 0)
        self.assertEqual(DurableLeaseQueue(self.db).summary(), {"SUCCEEDED": 1})

    def test_state_survives_real_server_process_restart_with_same_disk(self):
        self._start()
        job = {"task_id": "synthetic-v83-restart", "kind": "offline_check"}
        old = self._http("/private/submit", body=job, key=self.KEY, method="POST")
        self.assertEqual(old[1]["state"], "SUCCEEDED")
        self._stop()
        status = self._start()
        self.assertNotEqual(old[1].get("boot_id"), status["boot_id"])
        code, observed = self._http("/private/state", key=self.KEY)
        self.assertEqual(code, 200)
        self.assertEqual(observed["queue"], {"SUCCEEDED": 1})
        again = self._http("/private/submit", body=job, key=self.KEY, method="POST")
        self.assertFalse(again[1]["new"])
        self.assertEqual(again[1]["batch"]["claimed"], 0)

    def test_expired_claim_recovered_by_authenticated_new_process(self):
        store = DurableLeaseQueue(self.db, clock=lambda: 1.0)
        id = "synthetic-v83-expired"
        store.enqueue(id, "offline_check", hashlib.sha256(id.encode()).hexdigest())
        claim = store.claim("crashed", lease_seconds=3)
        self.assertEqual(claim["attempt"], 1)
        self._start()
        code, report = self._http("/private/recover", key=self.KEY,
                                  body={}, method="POST")
        self.assertEqual(code, 200)
        self.assertEqual(report["recovered"]["requeued"], 1)
        self.assertEqual(report["succeeded"], 1)
        self.assertEqual(DurableLeaseQueue(self.db).get(id)["attempt"], 2)

    def test_invalid_role_and_unauthorized_access_cannot_mutate_db(self):
        self._start()
        bad = {"task_id": "synthetic-v83-no", "kind": "paid_model"}
        self.assertEqual(self._http("/private/submit", body=bad, key=self.KEY, method="POST")[0], 400)
        self.assertEqual(self._http("/private/submit", body=bad, method="POST")[0], 401)
        self.assertEqual(self._http("/private/submit", body={
            "task_id": "nonsynthetic", "kind": "offline_check"
        }, key=self.KEY, method="POST")[0], 400)
        self.assertEqual(DurableLeaseQueue(self.db).summary(), {})

    def test_no_external_methods_or_public_private_state(self):
        self._start()
        self.assertEqual(self._http("/private/state")[0], 401)
        self.assertEqual(self._http("/does-not-exist")[0], 404)
        self.assertEqual(self._http("/private/submit", body={}, key=self.KEY, method="PUT")[0], 405)
