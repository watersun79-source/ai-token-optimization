"""Fail-closed HTTP gateway tests; no Neon credentials or external APIs."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from tools.isolated_neon_gateway_v835 import App


class GatewayTests(unittest.TestCase):
    key = "TEST_PRIVATE_KEY_REPLACE_WITH_REAL_SECRET_012345"
    url = "postgresql://fake.invalid/test"

    def setUp(self):
        self.server = App("127.0.0.1", 0, database_url=self.url, api_key=self.key)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def get(self, path, *, api_key=None, body=None, method="GET"):
        req = urllib.request.Request(
            "http://127.0.0.1:" + str(self.port) + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method, headers={
                "Content-Type": "application/json",
                **({"X-Queue-Key": api_key} if api_key else {})
            })
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as r:
            return r.code, json.loads(r.read())

    def test_public_health_does_not_expose_credentials(self):
        status, data = self.get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(data["version"], "8.3.5")
        self.assertFalse(data["always_on_verified"])
        self.assertFalse(data["automatic_recovery_verified"])
        self.assertNotIn("fake.invalid", json.dumps(data))
        self.assertNotIn(self.key, json.dumps(data))

    def test_unauthorized_post_fails_closed(self):
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue") as enqueue:
            status, data = self.get("/private/submit",
                                    body={"task_id":"synthetic-v83-test","kind":"offline_check"},
                                    method="POST")
            self.assertEqual(status,401)
            self.assertEqual(data["error"],"UNAUTHORIZED")
            enqueue.assert_not_called()

    def test_authorized_synthetic_job_runs_once(self):
        self.server.mark_db_verified()
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue",return_value=True) as enq, \
             patch("tools.isolated_neon_gateway_v835.worker.run_once",
                   return_value={"claimed":1,"succeeded":1}) as run:
            status, data = self.get("/private/submit",
                api_key=self.key,
                body={"task_id":"synthetic-v83-test","kind":"offline_check"},
                method="POST")
            self.assertEqual(status,200)
            self.assertTrue(data["new"])
            self.assertEqual(data["batch"]["succeeded"],1)
            enq.assert_called_once()
            run.assert_called_once()

    def test_invalid_role_does_not_touch_queue(self):
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue") as enq:
            status, data = self.get("/private/submit",api_key=self.key,
                body={"task_id":"synthetic-v83-test","kind":"paid_model"},method="POST")
            self.assertEqual(status,400)
            self.assertEqual(data["error"],"UNSAFE_JOB")
            enq.assert_not_called()

    def test_backend_failure_returns_only_sanitized_error(self):
        # Simulate a previously connected database becoming unavailable.
        self.server.mark_db_verified()
        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   side_effect=RuntimeError("SECRET_IN_EXCEPTION")):
            status, data = self.get("/private/state",api_key=self.key)
            self.assertEqual(status,503)
            self.assertEqual(data,{"error":"BACKEND_UNAVAILABLE"})
            self.assertFalse(self.server.last_db_ok)
            self.assertFalse(self.get("/healthz")[1]["database_connection_verified"])

    def test_write_failure_clears_previously_verified_database_state(self):
        self.server.mark_db_verified()
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue",
                   side_effect=RuntimeError("SECRET_NO_PRINTING")):
            status, response = self.get(
                "/private/submit", api_key=self.key,
                body={"task_id":"synthetic-v83-failed-backend","kind":"offline_check"},
                method="POST")
            self.assertEqual(status,503)
            self.assertEqual(response,{"error":"BACKEND_UNAVAILABLE"})
            self.assertFalse(self.get("/healthz")[1]["database_connection_verified"])

    def test_no_database_or_short_key_does_not_accept_jobs(self):
        self.server.enabled=False
        status,_ = self.get("/private/submit",api_key=self.key,
             body={"task_id":"synthetic-v83-test","kind":"offline_check"},method="POST")
        self.assertEqual(status,401)

    def test_recovery_requires_empty_body(self):
        self.server.mark_db_verified()
        with patch("tools.isolated_neon_gateway_v835.worker.run_once",
                   return_value={"claimed":0,"succeeded":0}) as mock:
            bad,_=self.get("/private/recover",api_key=self.key,body={"force":True},method="POST")
            self.assertEqual(bad,400)
            ok,data=self.get("/private/recover",api_key=self.key,body={},method="POST")
            self.assertEqual(ok,200)
            mock.assert_called_once()


    def test_global_limit_rejects_third_concurrent_backend_request(self):
        arrived = threading.Event()
        release = threading.Event()
        lock = threading.Lock()
        active = [0]
        peak = [0]

        def slow_backend(_url):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
                if active[0] == 2:
                    arrived.set()
            try:
                if not release.wait(timeout=2.5):
                    raise RuntimeError("TEST_RELEASE_NOT_SIGNALED")
                return {"QUEUED": 0}
            finally:
                with lock:
                    active[0] -= 1

        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   side_effect=slow_backend) as read:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.get, "/private/state", api_key=self.key)
                second = pool.submit(self.get, "/private/state", api_key=self.key)
                try:
                    self.assertTrue(arrived.wait(timeout=1.5))
                    code, body = self.get("/private/state", api_key=self.key)
                    self.assertEqual(code, 429)
                    self.assertEqual(body, {"error": "BUSY_RETRY"})
                    self.assertEqual(read.call_count, 2)
                    self.assertEqual(peak[0], 2)
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=3)[0], 200)
                self.assertEqual(second.result(timeout=3)[0], 200)
            self.assertEqual(self.get("/private/state", api_key=self.key)[0], 200)

    def test_busy_post_never_enqueues_or_executes_work(self):
        self.server.mark_db_verified()
        self.assertTrue(self.server.db_slots.acquire(blocking=False))
        self.assertTrue(self.server.db_slots.acquire(blocking=False))
        try:
            with patch("tools.isolated_neon_gateway_v835.worker.enqueue") as enqueue, \
                 patch("tools.isolated_neon_gateway_v835.worker.run_once") as runner:
                code, data = self.get(
                    "/private/submit", api_key=self.key,
                    body={"task_id": "synthetic-v83-when-busy", "kind": "offline_check"},
                    method="POST")
                self.assertEqual(code, 429)
                self.assertEqual(data, {"error": "BUSY_RETRY"})
                enqueue.assert_not_called()
                runner.assert_not_called()
        finally:
            self.server.db_slots.release()
            self.server.db_slots.release()


    def test_configured_secret_does_not_prove_neon_authentication(self):
        code, health = self.get("/healthz")
        self.assertEqual(code, 200)
        self.assertTrue(health["configuration_present"])
        self.assertFalse(health["intake_enabled"])
        self.assertFalse(health["database_connection_verified"])
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue") as enqueue, \
             patch("tools.isolated_neon_gateway_v835.worker.run_once") as run:
            code, response = self.get("/private/submit", api_key=self.key,
                body={"task_id": "synthetic-v83-auth-unverified", "kind": "offline_check"},
                method="POST")
            self.assertEqual(code, 503)
            self.assertEqual(response, {"error": "DATABASE_NOT_VERIFIED"})
            enqueue.assert_not_called()
            run.assert_not_called()
        with patch("tools.isolated_neon_gateway_v835.worker.summary", return_value={}) as validate:
            code, result = self.get("/private/state", api_key=self.key)
            self.assertEqual(code, 200)
            self.assertEqual(result["state_counts"], {})
            validate.assert_called_once()
        check = self.get("/healthz")[1]
        self.assertTrue(check["intake_enabled"])
        self.assertTrue(check["database_connection_verified"])

    def test_failed_neon_auth_never_enables_work(self):
        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   side_effect=RuntimeError("secret_auth_failure")):
            code, response = self.get("/private/state", api_key=self.key)
            self.assertEqual(code, 503)
            self.assertEqual(response, {"error": "BACKEND_UNAVAILABLE"})
        check = self.get("/healthz")[1]
        self.assertTrue(check["configuration_present"])
        self.assertFalse(check["intake_enabled"])
        self.assertFalse(check["database_connection_verified"])
        code, rejected = self.get("/private/recover", api_key=self.key, body={},
                                  method="POST")
        self.assertEqual(code, 503)
        self.assertEqual(rejected, {"error": "DATABASE_NOT_VERIFIED"})


    def test_neon_verification_expires_without_fresh_auth_probe(self):
        from tools.isolated_neon_gateway_v835 import DB_VERIFICATION_TTL_SECONDS
        self.server.mark_db_verified()
        self.assertTrue(self.get("/healthz")[1]["intake_enabled"])
        # Simulate elapsed monotonic time without a real sleep.
        self.server.last_db_check_at -= DB_VERIFICATION_TTL_SECONDS + 1
        health = self.get("/healthz")[1]
        self.assertFalse(health["intake_enabled"])
        self.assertFalse(health["database_connection_verified"])
        with patch("tools.isolated_neon_gateway_v835.worker.enqueue") as enqueue:
            status, result = self.get(
                "/private/submit", api_key=self.key,
                body={"task_id": "synthetic-v83-expired-preflight", "kind": "offline_check"},
                method="POST")
            self.assertEqual(status, 503)
            self.assertEqual(result, {"error": "DATABASE_NOT_VERIFIED"})
            enqueue.assert_not_called()
        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   return_value={"QUEUED": 0}):
            status, _ = self.get("/private/state", api_key=self.key)
            self.assertEqual(status, 200)
        self.assertTrue(self.get("/healthz")[1]["database_connection_verified"])

    def test_neon_failed_probe_invalidates_ready_timestamp(self):
        self.server.mark_db_verified()
        self.assertIsNotNone(self.server.last_db_check_at)
        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   side_effect=RuntimeError("test-backend-unavailable")):
            status, result = self.get("/private/state", api_key=self.key)
            self.assertEqual(status, 503)
            self.assertEqual(result, {"error": "BACKEND_UNAVAILABLE"})
        self.assertIsNone(self.server.last_db_check_at)
        self.assertFalse(self.get("/healthz")[1]["database_connection_verified"])

    def test_private_state_requires_authorization(self):
        self.assertEqual(self.get("/private/state")[0],401)
        self.assertEqual(self.get("/unknown")[0],404)
