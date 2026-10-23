"""An OTLP tool must start as well as finish within its supplied native run."""
import unittest

from audit_v2 import check
from bot_team_r16 import collaborate
import test_bot_team_r16 as bot_tests


class TestOtelNativeWindow(unittest.TestCase):
    def test_tool_start_cannot_precede_native_run_even_by_one_nanosecond(self):
        for start, expected in (("1792735199999999999", ["slack_thread"]),
                                ("1792735200000000000", ["current_handoff", "slack_thread"])):
            with self.subTest(start=start):
                payload = bot_tests.BotTeamR16Tests().otel_sample()["evidence"]
                payload["otel"]["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["startTimeUnixNano"] = start
                result = check(payload)
                self.assertCountEqual(expected, result["verified_targets"])
                self.assertFalse(result["official_success_verified"])

    def test_native_submicrosecond_start_is_not_truncated(self):
        payload = bot_tests.BotTeamR16Tests().otel_sample()["evidence"]
        payload["native_run"]["started_at"] = "2026-10-23T06:00:00.000000001Z"
        spans = payload["otel"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        spans[2]["startTimeUnixNano"] = "1792735200000000001"
        result = check(payload)
        self.assertEqual(["slack_thread"], result["verified_targets"])
        self.assertFalse(result["official_success_verified"])

    def test_bot_rejects_tool_started_before_its_native_run(self):
        payload = bot_tests.BotTeamR16Tests().otel_sample()
        payload["evidence"]["otel"]["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["startTimeUnixNano"] = "1792735199999999999"
        result = collaborate(payload)
        self.assertEqual(["slack_thread"], result["audit"]["verified_targets"])
        self.assertEqual("READ_SAME_RUN_APP_CALLS", result["builder"]["next_action"])
        self.assertFalse(result["official_success_verified"])
        self.assertEqual(0, result["provider_calls"])


if __name__ == "__main__":
    unittest.main()
