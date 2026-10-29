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
        with patch("tools.isolated_neon_gateway_v835.worker.summary",
                   side_effect=RuntimeError("SECRET_IN_EXCEPTION")):
            status, data = self.get("/private/state",api_key=self.key)
            self.assertEqual(status,503)
            self.assertEqual(data,{"error":"BACKEND_UNAVAILABLE"})

    def test_no_database_or_short_key_does_not_accept_jobs(self):
        self.server.enabled=False
        status,_ = self.get("/private/submit",api_key=self.key,
             body={"task_id":"synthetic-v83-test","kind":"offline_check"},method="POST")
        self.assertEqual(status,401)

    def test_recovery_requires_empty_body(self):
        with patch("tools.isolated_neon_gateway_v835.worker.run_once",
                   return_value={"claimed":0,"succeeded":0}) as mock:
            bad,_=self.get("/private/recover",api_key=self.key,body={"force":True},method="POST")
            self.assertEqual(bad,400)
            ok,data=self.get("/private/recover",api_key=self.key,body={},method="POST")
            self.assertEqual(ok,200)
            mock.assert_called_once()

    def test_private_state_requires_authorization(self):
        self.assertEqual(self.get("/private/state")[0],401)
        self.assertEqual(self.get("/unknown")[0],404)
