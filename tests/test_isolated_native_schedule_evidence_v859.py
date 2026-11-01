"""Regression tests using the documented official native automation peek shape.

Isolated, network-free: no scheduler, provider, transcript or secrets.
"""
import unittest

from tools.isolated_native_schedule_evidence_v858 import (
    VERSION, reconcile_native_snapshot,
)

SCHEDULED = "2026-11-01T00:00:00Z"
STARTED = "2026-10-31T23:56:42Z"
COMPLETED = "2026-10-31T23:57:31Z"


def task(status="completed", with_result=True):
    run = {
        "id": "official-run-001",
        "recorded_status": status,
        "scheduled_for": SCHEDULED,
        "started_at": STARTED,
        "completed_at": COMPLETED if status != "in_progress" else None,
    }
    result = {
        "run_id": "official-run-001",
        "created_at": COMPLETED,
        "completed_at": COMPLETED,
        "content_text": "synthetic: never persist result content",
        "requires_user_action": False,
        "is_failure_message": False,
    } if with_result else None
    return {
        "id": "official-task-001",
        "run_details": {
            "last_run": run,
            "latest_result": result,
            "delivery_status": "unknown",
        },
    }


class NativeScheduleEvidenceTests(unittest.TestCase):
    def test_official_result_schema_has_no_scheduled_for(self):
        item = task()
        self.assertNotIn("scheduled_for", item["run_details"]["latest_result"])
        out = reconcile_native_snapshot(item)
        self.assertEqual(out["schema"], VERSION)
        self.assertEqual(out["verdict"], "RECORDED_COMPLETED_SAME_RUN_RESULT")
        self.assertEqual(out["result_link"], "SAME_RUN_RESULT_METADATA")
        self.assertEqual(out["timing"], "STARTED_BEFORE_SCHEDULED_FOR")
        self.assertNotIn("content_text", out)
        self.assertEqual(out["native_call_ledger"], "UNVERIFIED")

    def test_optional_matching_schedule_remains_accepted(self):
        item = task()
        item["run_details"]["latest_result"]["scheduled_for"] = SCHEDULED
        self.assertEqual(
            reconcile_native_snapshot(item)["result_link"],
            "SAME_RUN_RESULT_METADATA",
        )

    def test_mismatched_optional_schedule_must_not_link(self):
        item = task()
        item["run_details"]["latest_result"]["scheduled_for"] = "2026-11-01T01:00:00Z"
        self.assertEqual(
            reconcile_native_snapshot(item)["result_link"],
            "DIFFERENT_RUN_RESULT",
        )

    def test_different_run_id_cannot_claim_success(self):
        item = task()
        item["run_details"]["latest_result"]["run_id"] = "older-run"
        out = reconcile_native_snapshot(item)
        self.assertEqual(out["verdict"], "RECORDED_COMPLETED_RESULT_UNVERIFIED")
        self.assertEqual(out["result_link"], "DIFFERENT_RUN_RESULT")

    def test_different_completion_cannot_claim_success(self):
        item = task()
        item["run_details"]["latest_result"]["completed_at"] = "2026-10-31T23:58:00Z"
        self.assertEqual(
            reconcile_native_snapshot(item)["result_link"],
            "DIFFERENT_RUN_RESULT",
        )

    def test_required_result_metadata_still_enforced(self):
        item = task()
        del item["run_details"]["latest_result"]["completed_at"]
        with self.assertRaisesRegex(ValueError, "INVALID_RESULT"):
            reconcile_native_snapshot(item)

    def test_no_update_cannot_be_claimed_as_work_success(self):
        item = task(status="no_update", with_result=False)
        out = reconcile_native_snapshot(item)
        self.assertEqual(out["verdict"], "RECORDED_NO_UPDATE_NOT_WORK_SUCCESS")

    def test_in_progress_not_reported_as_completed(self):
        item = task(status="in_progress", with_result=False)
        self.assertEqual(
            reconcile_native_snapshot(item)["verdict"],
            "RECORDED_IN_PROGRESS",
        )

    def test_bad_chronology_still_rejected(self):
        item = task()
        item["run_details"]["last_run"]["completed_at"] = "2026-10-31T23:55:00Z"
        with self.assertRaisesRegex(ValueError, "INVALID_CHRONOLOGY"):
            reconcile_native_snapshot(item)


if __name__ == "__main__":
    unittest.main()
