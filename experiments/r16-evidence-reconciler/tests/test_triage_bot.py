"""No provider calls: verify R16 three-role audit BOT never claims success."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_v2 import AUTOMATION_ID, REQUIRED
from triage_bot import MAX_INPUT_BYTES, triage


def fixture():
    slot = "2026-10-23T13:00:00+09:00"
    run_id = "SYNTHETIC-NOT-A-NATIVE-RUN"
    return {
        "target_slot": slot,
        "schedule": {
            "id": AUTOMATION_ID, "is_enabled": True,
            "last_run_time": "2026-10-23T04:59:11Z",
        },
        "native_run": {
            "origin": "official_task_run_details",
            "run_id": run_id,
            "automation_id": AUTOMATION_ID,
            "scheduled_for": slot,
            "started_at": "2026-10-23T13:01:00+09:00",
            "completed_at": "2026-10-23T13:02:00+09:00",
            "status": "completed",
        },
        "tool_calls": [
            {
                "origin": "official_task_tool_call", "target": target,
                "run_id": run_id, "invocation_id": "SYNTH-" + target,
                "tool": tool, "locator": locator,
                "success": True, "observed_at": "2026-10-23T13:01:30+09:00",
                "version": "a" * 40 if version_type == "sha" else "1792416391.631669",
            }
            for target, (tool, locator, version_type) in REQUIRED.items()
        ],
    }


class TriageBotTests(unittest.TestCase):
    def test_original_run_only_does_not_authenticate(self):
        p = fixture()
        p["native_run"] = None
        p["tool_calls"] = []
        r = triage(p)
        self.assertFalse(r["authenticated_unattended_success"])
        self.assertEqual(r["format_check"], "INCOMPLETE")
        self.assertIn("Previous runs", r["next_goal"])

    def test_synthetic_fake_official_record_never_authenticates(self):
        r = triage(fixture())
        self.assertEqual(r["format_check"], "PASS_NOT_AUTHENTICATED")
        self.assertFalse(r["authenticated_unattended_success"])
        self.assertEqual(r["outcome"], "미검증")
        self.assertIn("진위", r["next_goal"])

    def test_other_automation_rejected(self):
        p = fixture()
        p["schedule"]["id"] = "OTHER"
        r = triage(p)
        self.assertEqual(r["format_check"], "INCOMPLETE")
        self.assertIn("예약 ID", r["next_goal"])

    def test_disabled_task_no_implicit_reenable(self):
        p = fixture()
        p["schedule"]["is_enabled"] = False
        r = triage(p)
        self.assertTrue(r["read_only"])
        self.assertEqual(r["external_calls"], 0)
        self.assertIn("임의 변경 금지", r["next_goal"])

    def test_missing_slack_tool_call(self):
        p = fixture()
        p["tool_calls"] = p["tool_calls"][:1]
        r = triage(p)
        self.assertEqual(r["missing_targets"], ["slack_thread"])
        self.assertIn("tool-call", r["next_goal"])

    def test_malformed_types_never_crash(self):
        for bad in [None, [], "x", 42, {"schedule": []}, {"schedule": {"id": []}}]:
            with self.subTest(payload=repr(bad)):
                self.assertFalse(triage(bad)["authenticated_unattended_success"])

    def test_no_source_or_secret_echo(self):
        p = fixture()
        p["credential"] = "sk-super-private-input"
        p["native_run"]["run_id"] = "SECRET-RUN"
        p["tool_calls"] = []
        output = json.dumps(triage(p))
        self.assertNotIn("SECRET-RUN", output)
        self.assertNotIn("sk-super-private-input", output)

    def test_cli_failure_exit_for_forged_format_pass(self):
        p = fixture()
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "fixture.json"
            file.write_text(json.dumps(p), encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "triage_bot.py"
            done = subprocess.run([sys.executable, str(script), "--input", str(file)],
                                  capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 3)
        self.assertFalse(json.loads(done.stdout)["authenticated_unattended_success"])

    def test_cli_no_evidence_exit_2(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "fixture.json"
            file.write_text(json.dumps({}), encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "triage_bot.py"
            done = subprocess.run([sys.executable, str(script), "--input", str(file)],
                                  capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)

    def test_oversized_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "too_large.json"
            file.write_bytes(b"x" * (MAX_INPUT_BYTES + 2))
            script = Path(__file__).resolve().parents[1] / "triage_bot.py"
            done = subprocess.run([sys.executable, str(script), "--input", str(file)],
                                  capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)
        self.assertFalse(json.loads(done.stdout)["authenticated_unattended_success"])


if __name__ == "__main__":
    unittest.main()
