"""Synthetic offline regressions, not provider/live evidence."""
import copy
import unittest
from progress_tracker import reconcile, ProgressError, Conflict

BOARD = {
    "schema": "AI_BOT_VERSION_PROGRESS_BOARD_V1",
    "components": [
        {"id": "github_isolated_dev", "version": "v8.5.14", "state": "CI_VERIFIED",
         "gates": {"ci": "PASS", "review": "UNVERIFIED", "merge": "BLOCKED", "live": "UNVERIFIED"}},
        {"id": "bot_operating", "version": "v8.1", "state": "NO_UPDATE",
         "gates": {"deployed": "UNVERIFIED", "live": "UNVERIFIED"}}
    ],
    "history": []
}
OBS = {"id": "github_isolated_dev", "observed_at": "2026-11-03T00:10:00Z",
       "evidence_id": "synthetic-1", "authenticated_source": True,
       "gates": {"review": "IN_PROGRESS"}}


class Tests(unittest.TestCase):
    def test_update_immutable(self):
        before = copy.deepcopy(BOARD)
        got, code = reconcile(BOARD, OBS, 1, 1)
        self.assertEqual("UPDATE", code)
        self.assertEqual("IN_PROGRESS", got["components"][0]["gates"]["review"])
        self.assertEqual(before, BOARD)

    def test_noop(self):
        got, state = reconcile(BOARD, {**OBS, "gates": {"ci": "PASS"}}, 1, 1)
        self.assertEqual("NO_UPDATE", state)
        self.assertEqual(BOARD, got)

    def test_cas_conflict(self):
        with self.assertRaises(Conflict):
            reconcile(BOARD, OBS, 1, 2)

    def test_version_requires_new_authenticated_release_evidence(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "version": "v9.9.9"}, 1, 1)

    def test_operating_requires_live_deploy_approval(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "id": "bot_operating", "version": "v8.9",
                    "version_proof": {"authenticated_provider_readback": True,
                    "source_sha": "sha", "ci_run_id": "123", "ci_success_receipt": "yes"}}, 1, 1)

    def test_runtime_requires_receipt(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "gates": {"live": "PASS"}}, 1, 1)

    def test_unknown_component(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "id": "other"}, 1, 1)

    def test_untrusted_source(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "authenticated_source": False}, 1, 1)

    def test_stale_read(self):
        s = copy.deepcopy(BOARD)
        s["components"][0]["last_observed_at"] = "2026-11-03T00:11:00Z"
        with self.assertRaises(ProgressError):
            reconcile(s, OBS, 1, 1)

    def test_unknown_milestone(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "gates": {"magic": "PASS"}}, 1, 1)

    def test_timezone_required(self):
        with self.assertRaises(ProgressError):
            reconcile(BOARD, {**OBS, "observed_at": "2026-11-03T00:10:00"}, 1, 1)

    def test_bounded_history(self):
        s = copy.deepcopy(BOARD)
        s["history"] = [{"evidence_id": str(x)} for x in range(25)]
        result, status = reconcile(s, OBS, 1, 1)
        self.assertEqual("UPDATE", status)
        self.assertEqual(12, len(result["history"]))


if __name__ == "__main__":
    unittest.main()
