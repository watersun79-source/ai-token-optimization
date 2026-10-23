"""Regression tests for the opt-in offline background coordinator."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest

from background_coordinator import KIND, run_loop


class BackgroundCoordinatorTests(unittest.TestCase):
    @staticmethod
    def ok(goal, state_dir):
        return {"status": "PASS", "selected_roles": ["scheduled_audit", "verify"]}

    def test_one_cycle_persists_explicitly_unverified_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = []
            result = run_loop("audit", Path(tmp), max_runs=1,
                              dispatch_fn=self.ok, emit_fn=events.append)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["cycles"], 1)
            payload = json.loads((Path(tmp) / "background_latest.json").read_text())
            self.assertEqual(payload["kind"], KIND)
            self.assertEqual(payload["cycle"], 1)
            self.assertEqual(payload["official_unattended_app_call_success"], "UNVERIFIED")
            self.assertEqual(len(events), 1)

    def test_two_cycles_have_at_least_hourly_spacing_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, sleeps = [], []

            def dispatcher(goal, state_dir):
                calls.append(goal)
                return {"status": "PASS"}

            result = run_loop("verify", Path(tmp), max_runs=2,
                              dispatch_fn=dispatcher,
                              sleep_fn=sleeps.append,
                              emit_fn=lambda _: None)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(calls, ["verify", "verify"])
            self.assertEqual(sleeps, [3600])
            payload = json.loads((Path(tmp) / "background_latest.json").read_text())
            self.assertEqual(payload["cycle"], 2)

    def test_failure_never_becomes_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = iter([{"status": "ERROR"}, {"status": "PASS"}])
            result = run_loop("audit", Path(tmp), max_runs=2,
                              dispatch_fn=lambda *_: next(calls),
                              sleep_fn=lambda _: None,
                              emit_fn=lambda _: None)
            self.assertEqual(result["status"], "ERROR")
            self.assertEqual(result["errors"], 1)

    def test_malformed_status_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_loop("audit", Path(tmp), max_runs=1,
                              dispatch_fn=lambda *_: {"status": "SUCCESS"},
                              emit_fn=lambda _: None)
            self.assertEqual(result["status"], "ERROR")
            payload = json.loads((Path(tmp) / "background_latest.json").read_text())
            self.assertEqual(payload["status"], "ERROR")

    def test_exceptions_do_not_expose_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            def broken(*_):
                raise RuntimeError("super-secret-value")

            result = run_loop("audit", Path(tmp), max_runs=1,
                              dispatch_fn=broken, emit_fn=lambda _: None)
            self.assertEqual(result["status"], "ERROR")
            self.assertNotIn("super-secret-value",
                             (Path(tmp) / "background_latest.json").read_text())

    def test_duplicate_daemon_does_not_overwrite_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            receipt = state / "background_latest.json"
            receipt.write_text('{"status":"previous"}')
            fd = os.open(state / ".background.lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = run_loop("audit", state, max_runs=1,
                                  dispatch_fn=self.ok, emit_fn=lambda _: None)
                self.assertEqual(result["status"], "BUSY")
                self.assertEqual(receipt.read_text(), '{"status":"previous"}')
            finally:
                os.close(fd)

    def test_symlink_lock_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            target = state / "outside"
            target.write_text("unchanged")
            (state / ".background.lock").symlink_to(target)
            with self.assertRaises(OSError):
                run_loop("audit", state, max_runs=1, dispatch_fn=self.ok)
            self.assertEqual(target.read_text(), "unchanged")

    def test_interval_and_run_counts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kw in ({"interval_seconds": 59, "max_runs": 1},
                       {"interval_seconds": 3600, "max_runs": 0}):
                with self.subTest(kw=kw), self.assertRaises(ValueError):
                    run_loop("audit", Path(tmp), dispatch_fn=self.ok, **kw)


if __name__ == "__main__":
    unittest.main()
