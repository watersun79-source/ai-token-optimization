"""Regression checks: CI != prod, dispatch != schedule, HTTP != permission."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ai_version_evidence_guard", ROOT / "tools" / "ai_version_evidence_guard.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate = module.evaluate

BASE = {
    "observed_at": "2026-11-02T09:48:47Z",
    "activepieces_github_connection": {"status": "ACTIVE"},
    "read_only_watcher": {"is_read_only": True, "github_api_http_status": 200,
                          "github_dispatch_blocker": "NO_ACTIVEPIECES_GITHUB_CONNECTION"},
    "last_schedule_run": {"event": "schedule", "status": "completed", "conclusion": "success",
                          "created_at": "2026-11-02T02:27:07Z", "id": 41377802700},
    "hosted_collector": {"observed_at": "2026-11-02T09:48:44Z", "successful_reads": 2,
                         "total_reads": 2, "failed_reads": 0},
    "native_run": {},
    "candidate_release": {"version": "v8.5.14", "official_ci_sha_matched": True,
                          "merged": False, "authorized": False, "deploy_live": False,
                          "live_health_verified": False, "rollback_ready": False},
}


class GuardTests(unittest.TestCase):
    def data(self, **changed):
        return {**BASE, **changed}

    def test_observed_read_is_not_dispatch_permission(self):
        result = evaluate(BASE)
        self.assertEqual(result["activepieces_github_connection"], "PASS_CONNECTED_CONFIG_ONLY")
        self.assertEqual(result["github_read_only_api"], "PASS_READ_ONLY_HTTP")
        self.assertEqual(result["github_dispatch_permission"], "UNVERIFIED_READ_ONLY_WATCH")

    def test_fixed_false_negative_detection(self):
        self.assertTrue(evaluate(BASE)["false_disconnected_warning_detected"])
        fixed = self.data(read_only_watcher={"is_read_only": True,
                                            "github_api_http_status": 200,
                                            "github_dispatch_blocker": "NOT_APPLICABLE_READ_ONLY_WATCH"})
        self.assertFalse(evaluate(fixed)["false_disconnected_warning_detected"])

    def test_stale_scheduled_run_even_if_hosted_api_succeeds(self):
        result = evaluate(BASE)
        self.assertEqual(result["github_schedule"], "WARN_LAST_SCHEDULE_STALE")
        self.assertEqual(result["hosted_github_collector"], "PASS_BOUNDED_READS_ONLY")

    def test_dispatch_run_not_a_schedule(self):
        data = self.data(last_schedule_run={"event": "workflow_dispatch", "status": "completed",
                                            "conclusion": "success", "created_at": "2026-11-02T09:30:00Z"})
        self.assertEqual(evaluate(data)["github_schedule"], "UNVERIFIED_NOT_A_SCHEDULE_EVENT")

    def test_explicit_403_overrides_historical_success(self):
        data = self.data(hosted_collector={"observed_at": "2026-11-02T09:48:44Z", "http_code": 403,
                                               "successful_reads": 2, "total_reads": 2, "failed_reads": 2})
        self.assertEqual(evaluate(data)["hosted_github_collector"], "UNVERIFIED_LATEST_FAILED")

    def test_stale_collector_is_not_current_pass(self):
        data = self.data(hosted_collector={"observed_at": "2026-11-02T07:43:40Z",
                                               "successful_reads": 2, "total_reads": 2, "failed_reads": 0})
        self.assertEqual(evaluate(data)["hosted_github_collector"], "UNVERIFIED_STALE")

    def test_draft_ci_is_not_production_deployment(self):
        self.assertEqual(evaluate(BASE)["release_promotion"], "BLOCK_NO_PRODUCTION_PROOF")
        self.assertEqual(evaluate(BASE)["candidate_software_version"], "v8.5.14")

    def test_native_run_requires_same_id_and_verified_ledger(self):
        x = self.data(native_run={"run_id": "run-A", "status": "completed",
                                       "external_ledger_native_run_id": "run-B", "external_ledger_verified": True})
        self.assertEqual(evaluate(x)["chatgpt_native_same_run"], "UNVERIFIED")
        x["native_run"]["external_ledger_native_run_id"] = "run-A"
        self.assertEqual(evaluate(x)["chatgpt_native_same_run"], "PASS_SAME_NATIVE_RUN")

    def test_no_timestamp_is_not_assumed_utc(self):
        x = self.data(last_schedule_run={"event": "schedule", "status": "completed",
                                         "conclusion": "success", "created_at": "2026-11-02T09:45:00"})
        self.assertEqual(evaluate(x)["github_schedule"], "UNVERIFIED_TIMESTAMPS")

    def test_recent_proven_schedule_is_separate_gate(self):
        x = self.data(last_schedule_run={"event": "schedule", "status": "completed", "conclusion": "success",
                                         "created_at": "2026-11-02T09:30:00Z"})
        self.assertEqual(evaluate(x)["github_schedule"], "PASS_RECENT_GITHUB_SCHEDULE_ONLY")
        self.assertEqual(evaluate(x)["chatgpt_native_same_run"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
