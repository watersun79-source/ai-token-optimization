"""Network-free except localhost: real process start, stop, restart checks."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.isolated_probe_v832 import PROBE_VERSION


class HostedProbeTests(unittest.TestCase):
    def setUp(self):
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=5)
            if p.stdout:
                p.stdout.close()
            if p.stderr:
                p.stderr.close()

    def _port(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _boot(self, port):
        env = dict(os.environ, PORT=str(port), PROBE_HOST="127.0.0.1")
        proc = subprocess.Popen(
            [sys.executable, "-m", "tools.isolated_probe_v832"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        self.procs.append(proc)
        for _ in range(60):
            try:
                return proc, self._get(port)
            except (OSError, URLError):
                if proc.poll() is not None:
                    self.fail("probe exited before listen: " + proc.stderr.read()[-500:].decode())
                time.sleep(0.05)
        self.fail("probe did not bind in time")

    def _get(self, port, path="/healthz"):
        with urlopen("http://127.0.0.1:" + str(port) + path, timeout=1) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def test_probe_version_and_non_operational_guard(self):
        self.assertEqual(PROBE_VERSION, "8.3.2")
        _, data = self._boot(self._port())
        self.assertEqual(data[0], 200)
        self.assertEqual(data[1]["probe_version"], "8.3.2")
        self.assertEqual(data[1]["lease_code_version"], "8.3.1")
        self.assertFalse(data[1]["jobs_enabled"])
        self.assertFalse(data[1]["persistent_database_connected"])
        self.assertFalse(data[1]["automatic_restart_verified"])

    def test_404_does_not_expose_paths(self):
        port = self._port()
        self._boot(port)
        with self.assertRaises(HTTPError) as err:
            self._get(port, "/secrets")
        self.assertEqual(err.exception.code, 404)

    def test_mutating_http_methods_are_denied(self):
        port = self._port()
        self._boot(port)
        req = Request("http://127.0.0.1:" + str(port) + "/healthz",
                      data=b"unsafe-write", method="POST")
        with self.assertRaises(HTTPError) as err:
            urlopen(req, timeout=1)
        self.assertEqual(err.exception.code, 405)

    def test_local_process_restart_changes_boot_id(self):
        # Simulates manual termination + restart. It does NOT verify Render auto-restart.
        port = self._port()
        proc, before = self._boot(port)
        old_boot = before[1]["boot_id"]
        proc.terminate()
        proc.wait(timeout=5)
        _, after = self._boot(port)
        self.assertNotEqual(old_boot, after[1]["boot_id"])
        self.assertEqual(after[1]["status"], "UP")

    def test_two_distinct_independent_services_have_distinct_boot_ids(self):
        _, a = self._boot(self._port())
        _, b = self._boot(self._port())
        self.assertNotEqual(a[1]["boot_id"], b[1]["boot_id"])

    def test_head_returns_headers_only(self):
        port = self._port()
        self._boot(port)
        req = Request("http://127.0.0.1:" + str(port) + "/healthz", method="HEAD")
        with urlopen(req, timeout=1) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.read(), b"")
            self.assertIn("application/json", res.headers["Content-Type"])
