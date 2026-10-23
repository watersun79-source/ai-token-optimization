"""Offline supervisor behavior and fail-closed regression."""
import json
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


if __name__ == "__main__":
    unittest.main()
