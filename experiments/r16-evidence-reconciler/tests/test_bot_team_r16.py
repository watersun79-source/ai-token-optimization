"""Offline R16 three-role policy gate regression. No AI API, network, scheduler."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from audit_v2 import AUTOMATION_ID
from bot_team_r16 import collaborate
from audit_v2 import check
from test_otel_evidence_adapter import fixture, RUN, TARGETS

ROOT = Path(__file__).resolve().parents[1]


class BotTeamR16Tests(unittest.TestCase):
    def otel_sample(self):
        return {"task": "OTLP 호출 증거를 봇 협업에서 검증", "evidence": {
            "target_slot": "2026-10-23T06:00:00Z",
            "schedule": {"id": AUTOMATION_ID, "is_enabled": True},
            "native_run": {"origin": "official_task_run_details", "run_id": RUN,
                           "automation_id": AUTOMATION_ID, "scheduled_for": "2026-10-23T06:00:00Z",
                           "started_at": "2026-10-23T06:00:00Z", "completed_at": "2026-10-23T06:00:05Z",
                           "status": "completed"},
            "otel": fixture(),
        }}

    def test_collaboration_preserves_otlp_evidence_without_legacy_calls(self):
        p = self.otel_sample()
        expected = check(p["evidence"])
        self.assertCountEqual(TARGETS, expected["verified_targets"])
        actual = collaborate(p)
        self.assertEqual(expected, actual["audit"])
        self.assertFalse(actual["official_success_verified"])
        self.assertEqual(0, actual["provider_calls"])

    def test_invalid_otlp_cannot_fall_back_to_legacy_calls_in_collaboration(self):
        p = self.otel_sample()
        p["evidence"]["tool_calls"] = [
            {"target": target, "origin": "official_task_tool_call", "run_id": RUN,
             "success": True, "tool": next(iter(aliases)), "locator": locator,
             "invocation_id": target, "observed_at": "2026-10-23T06:00:01Z",
             "version": "a" * 40 if target == "current_handoff" else "1792735600.070409"}
            for target, (aliases, locator, _) in TARGETS.items()
        ]
        # Without OTLP these supplied legacy calls would pass format checks.
        legacy = dict(p["evidence"])
        del legacy["otel"]
        self.assertTrue(check(legacy)["status"].startswith("형식 통과"))
        for invalid in ({}, None):
            with self.subTest(otel=invalid):
                p["evidence"]["otel"] = invalid
                expected = check(p["evidence"])
                self.assertEqual([], expected["verified_targets"])
                actual = collaborate(p)
                self.assertEqual(expected, actual["audit"])
                self.assertEqual("READ_SAME_RUN_APP_CALLS", actual["builder"]["next_action"])

    def sample(self):
        return {"task": "AI R16 예약 원본과 GitHub Slack 교차 검증",
                "references": [
                    {"name": "Microsoft Agent Framework",
                     "url": "https://github.com/microsoft/agent-framework"}],
                "evidence": {
                    "schedule": {"id": AUTOMATION_ID, "is_enabled": True,
                                 "last_run_time": "2026-10-23T04:00:15Z"},
                    "target_slot": "2026-10-23T13:00:00+09:00",
                }}

    def test_without_native_log_requests_authoritative_run(self):
        report = collaborate(self.sample())
        self.assertEqual(report["builder"]["next_action"], "READ_OFFICIAL_SCHEDULED_RUN")
        self.assertEqual(report["verifier"]["policy_checks"], "SAFE_UNVERIFIED")
        self.assertFalse(report["official_success_verified"])
        self.assertEqual(report["live_llm_bots"], 0)
        self.assertEqual(report["production_mutations"], 0)
        self.assertEqual(report["provider_calls"], 0)

    def test_research_reference_is_unverified(self):
        report = collaborate(self.sample())
        self.assertEqual(report["research"]["source_authenticity"],
                         "NOT_VERIFIED_BY_OFFLINE_BOT")
        self.assertEqual(len(report["research"]["references_reviewed"]), 1)

    def test_rejects_untrusted_reference_urls(self):
        p = self.sample()
        p["references"].extend([
            {"name": "Credential", "url": "https://user@github.com/somewhere"},
            {"name": "Insecure", "url": "http://github.com/any"},
            {"name": "Query", "url": "https://github.com/repo?token=x"},
        ])
        self.assertEqual(len(collaborate(p)["research"]["references_reviewed"]), 1)

    def test_injected_success_claim_is_ignored(self):
        p = self.sample()
        p["official_success_verified"] = True
        p["evidence"]["official_success_verified"] = True
        report = collaborate(p)
        self.assertFalse(report["official_success_verified"])
        self.assertFalse(report["verifier"]["official_success_verified"])

    def test_wrong_task_fails_closed(self):
        p = self.sample()
        p["evidence"]["schedule"]["id"] = "UNRELATED-AUTOMATION"
        r = collaborate(p)
        self.assertEqual(r["audit"]["status"], "미검증")
        self.assertFalse(r["official_success_verified"])

    def test_invalid_nested_input_fails_closed(self):
        p = self.sample()
        p["evidence"] = []
        with self.assertRaises(ValueError):
            collaborate(p)

    def test_format_match_requires_real_native_provenance(self):
        p = self.sample()
        rid = "SYNTHETIC-NOT-REAL-PLATFORM-RUN"
        p["evidence"]["native_run"] = dict(
            origin="official_task_run_details", automation_id=AUTOMATION_ID,
            run_id=rid, scheduled_for="2026-10-23T13:00:00+09:00",
            started_at="2026-10-23T13:00:10+09:00",
            completed_at="2026-10-23T13:00:20+09:00", status="completed")
        call = {"origin": "official_task_tool_call", "run_id": rid,
                "success": True, "observed_at": "2026-10-23T13:00:15+09:00"}
        p["evidence"]["tool_calls"] = [
            {**call, "target": "current_handoff", "tool": "mcp__GitHub__fetch_file",
             "locator": "docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md",
             "version": "a" * 40, "invocation_id": "SYN-1"},
            {**call, "target": "slack_thread", "tool": "mcp__Slack__slack_read_thread",
             "locator": "C0C9649RQAZ/1792416391.631669",
             "version": "1792416391.631669", "invocation_id": "SYN-2"},
        ]
        result = collaborate(p)
        self.assertTrue(result["audit"]["status"].startswith("형식 통과"))
        self.assertEqual(result["builder"]["next_action"],
                         "COMPARE_INDEPENDENT_GITHUB_SLACK_READBACK")
        self.assertFalse(result["official_success_verified"])
        self.assertFalse(result["verifier"]["native_run_authenticated"])

    def test_cli_never_returns_success_on_supplied_json(self):
        p = self.sample()
        with tempfile.TemporaryDirectory() as tmp:
            loc = Path(tmp) / "request.json"
            loc.write_text(json.dumps(p), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "bot_team_r16.py"),
                 "--input", str(loc)],
                text=True, capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["official_success_verified"])

    def test_input_limits(self):
        p = self.sample()
        p["references"] = [{"name": str(i)} for i in range(21)]
        with self.assertRaises(ValueError):
            collaborate(p)


if __name__ == "__main__":
    unittest.main()

