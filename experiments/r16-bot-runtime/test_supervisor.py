"""Offline supervisor behavior and fail-closed regression."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest
from supervisor import run_once


class SupervisorTests(unittest.TestCase):
    def test_success_writes_local_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "ok.py"
            script.write_text("print('ok')\n")
            result = run_once(Path(tmp) / "state", script=script)
            self.assertEqual(result["status"], "PASS")
            saved = json.loads((Path(tmp) / "state/latest.json").read_text())
            self.assertEqual(saved["kind"], "OFFLINE_LOCAL_CHECK_NOT_SCHEDULED_APP_PROOF")

    def test_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "bad.py"
            script.write_text("raise RuntimeError('bad')\n")
            result = run_once(Path(tmp) / "state", script=script)
            self.assertEqual(result["status"], "ERROR")
            self.assertNotEqual(result["exit_code"], 0)

    def test_timeout_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "slow.py"
            script.write_text("import time; time.sleep(5)\n")
            result = run_once(Path(tmp) / "state", script=script, timeout=0.1)
            self.assertEqual(result["status"], "ERROR")
            self.assertEqual(result["reason"], "timeout")


    def test_busy_does_not_overwrite_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            state.mkdir()
            receipt = state / "latest.json"
            receipt.write_text('{"status":"previous"}')
            lockfd = os.open(state / ".supervisor.lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = run_once(state)
                self.assertEqual(result["status"], "BUSY")
                self.assertEqual(receipt.read_text(), '{"status":"previous"}')
            finally:
                os.close(lockfd)

    def test_lock_released_after_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            bad = Path(tmp) / "bad.py"
            good = Path(tmp) / "good.py"
            bad.write_text("raise RuntimeError('bad')\\n".replace("\\n", "\n"))
            good.write_text("print('ok')\\n".replace("\\n", "\n"))
            self.assertEqual(run_once(state, script=bad)["status"], "ERROR")
            self.assertEqual(run_once(state, script=good)["status"], "PASS")

    def test_symlink_lock_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            state.mkdir()
            target = Path(tmp) / "outside"
            target.write_text("unchanged")
            (state / ".supervisor.lock").symlink_to(target)
            with self.assertRaises(OSError):
                run_once(state)
            self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
