"""Prevent CI from treating unverified ChatGPT scheduled runs as completed."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_v2 import AUTOMATION_ID, REQUIRED

SCRIPT = Path(__file__).resolve().parents[1] / "audit_v2.py"


def native_format_fixture():
    slot = "2026-10-23T00:00:00+09:00"
    run_id = "SYNTHETIC-NEVER-OFFICIAL"
    calls = []
    for i, (target, (tool, locator, version_type)) in enumerate(REQUIRED.items()):
        calls.append({
            "origin": "official_task_tool_call", "run_id": run_id,
            "target": target, "tool": tool, "locator": locator,
            "success": True, "observed_at": "2026-10-23T00:02:00+09:00",
            "version": "a" * 40 if version_type == "sha" else "1792680263.547459",
            "invocation_id": "SYNTHETIC-CALL-" + str(i),
        })
    return {
        "target_slot": slot,
        "schedule": {
            "id": AUTOMATION_ID, "is_enabled": True,
            "last_run_time": "2026-10-22T15:01:00Z",
        },
        "native_run": {
            "origin": "official_task_run_details", "automation_id": AUTOMATION_ID,
            "run_id": run_id, "scheduled_for": slot,
            "started_at": "2026-10-23T00:01:00+09:00",
            "completed_at": "2026-10-23T00:03:00+09:00",
            "status": "completed",
        },
        "tool_calls": calls,
    }


class CliFailClosedExitCodes(unittest.TestCase):
    def run_audit(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "fixture.json"
            fixture.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(fixture)],
                capture_output=True, text=True, timeout=12,
            )
            self.assertTrue(proc.stdout.strip() or proc.stderr.strip())
            return proc, json.loads(proc.stdout)

    def test_format_only_success_must_not_exit_zero(self):
        proc, verdict = self.run_audit(native_format_fixture())
        self.assertEqual(verdict["status"], "형식 통과 · 진위 미검증")
        self.assertEqual(proc.returncode, 3, "format-only is never authenticated success")
        self.assertIs(verdict["official_success_verified"], False)

    def test_missing_native_run_stays_unverified_and_returns_two(self):
        payload = native_format_fixture()
        payload["native_run"] = None
        payload["tool_calls"] = []
        proc, verdict = self.run_audit(payload)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(verdict["status"], "미검증")
        self.assertIs(verdict["official_success_verified"], False)

    def test_wrong_scheduled_task_id_remains_unverified(self):
        payload = native_format_fixture()
        payload["schedule"]["id"] = "WRONG-TASK"
        proc, verdict = self.run_audit(payload)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("예약 ID", verdict["reason"])
        self.assertIs(verdict["official_success_verified"], False)


if __name__ == "__main__":
    unittest.main()
