"""Fail-closed SDK activation regression tests; no third-party packages or providers."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "oss-top10-safe-adoption"
sys.path.insert(0, str(ROOT))
import activation_guard as guard
from safe_adoption import load_catalog
from ten_adapter_runtime import simulate_all


class TestSecurityActivationGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = guard.load_evidence()
        cls.catalog = load_catalog(ROOT / "catalog.json")

    def test_all_ten_have_explicit_denied_activations(self):
        snapshot = guard.status_snapshot()
        self.assertEqual(set(snapshot["projects"]), guard.ALL)
        self.assertTrue(all(x["activation_allowed"] is False for x in snapshot["projects"].values()))

    def test_four_vulnerable_sdk_blocks(self):
        snap = guard.status_snapshot()
        self.assertEqual(set(snap["blocked_vulnerable"]), guard.BLOCKED)
        self.assertTrue(all(snap["projects"][x]["status"] == "BLOCKED_VULNERABILITY" for x in guard.BLOCKED))

    def test_five_clean_are_still_not_authorized(self):
        snap = guard.status_snapshot()
        self.assertTrue(all(snap["projects"][x]["status"] == "OFFLINE_ONLY_NOT_APPROVED" for x in guard.CLEAN))
        self.assertEqual(snap["runtime_activations"], 0)

    def test_flowise_eol_remains_denied(self):
        self.assertEqual(guard.status_snapshot()["projects"]["flowise"]["status"], "BLOCKED_EOL")

    def test_each_live_action_is_explicitly_denied_for_all_ten(self):
        for project in guard.ALL:
            with self.subTest(project=project), self.assertRaises(guard.SecurityBlock):
                guard.require_activation_allowed(project)

    def test_unknown_sdk_and_action_denied(self):
        for project, action in (("unexpected-sdk", "enable"), ("mem0", "bypass")):
            with self.subTest(project=project, action=action), self.assertRaises(guard.SecurityBlock):
                guard.require_activation_allowed(project, action=action)

    def test_source_run_or_sha_mismatch_fails_closed(self):
        for k, v in (("audit_run_id", 0), ("audit_head", "0" * 40), ("source", "trust_me")):
            with self.subTest(key=k):
                changed = copy.deepcopy(self.evidence)
                changed[k] = v
                with self.assertRaises(guard.SecurityBlock):
                    guard.verify_evidence(changed)

    def test_missing_security_record_rejected(self):
        changed = copy.deepcopy(self.evidence)
        del changed["projects"]["letta"]
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_bad_lock_sha_rejected(self):
        changed = copy.deepcopy(self.evidence)
        changed["projects"]["activepieces"]["git_blob_sha"] = "0" * 40
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_attempt_to_clear_known_advisories_fails(self):
        changed = copy.deepcopy(self.evidence)
        changed["projects"]["crewai"]["known_advisories"] = 0
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_license_unknown_must_remain_unverified(self):
        changed = copy.deepcopy(self.evidence)
        changed["projects"]["activepieces"]["license_state"] = "DECLARED_METADATA_ONLY"
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_license_review_must_remain_review(self):
        changed = copy.deepcopy(self.evidence)
        changed["projects"]["openhands"]["license_state"] = "UNVERIFIED"
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_no_advisory_ids_is_unverified_and_denied(self):
        changed = copy.deepcopy(self.evidence)
        changed["projects"]["letta"]["advisory_ids"] = []
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(changed)

    def test_evidence_license_review_not_approved(self):
        snapshot = guard.status_snapshot()
        self.assertEqual(snapshot["projects"]["openhands"]["license"], "REVIEW")
        self.assertEqual(snapshot["projects"]["letta"]["license"], "REVIEW")
        self.assertEqual(snapshot["projects"]["crewai"]["license"], "UNVERIFIED")
        self.assertEqual(snapshot["projects"]["activepieces"]["license"], "UNVERIFIED")

    def test_ten_provider_free_mock_contracts_still_run(self):
        result = simulate_all(self.catalog, "Safe offline check")
        self.assertEqual(result["adapter_contracts_exercised"], 10)
        self.assertEqual(set(result["blocked_sdk_activation"]), guard.BLOCKED)
        self.assertIsNone(result["selection"]["automation"])
        self.assertFalse(result["selection_is_live"])
        for entry in result["results"]:
            self.assertFalse(entry["vendor_runtime_imported"])
            self.assertFalse(entry["activation_allowed"])

    def test_mock_four_explicitly_blocked(self):
        result = simulate_all(self.catalog, "offline")
        by_id = {x["project"]: x for x in result["results"]}
        for project in guard.BLOCKED:
            self.assertEqual(by_id[project]["security_status"], "BLOCKED_VULNERABILITY")
            self.assertEqual(by_id[project]["status"], "BLOCKED_VULNERABILITY_LOCAL_CONTRACT_ONLY")

    def test_existing_simulation_shape_preserved(self):
        result = simulate_all(self.catalog, "offline")
        by_id = {x["project"]: x for x in result["results"]}
        self.assertFalse(by_id["activepieces"]["artifact"]["published"])
        self.assertFalse(by_id["openhands"]["artifact"]["shell_executed"])
        self.assertEqual(by_id["crewai"]["artifact"]["model_agents_started"], 0)
        self.assertFalse(by_id["letta"]["artifact"]["remote_state_created"])

    def test_missing_lock_dir_is_never_accepted(self):
        with self.assertRaises(guard.SecurityBlock):
            guard.verify_evidence(self.evidence, locks_dir=ROOT / "missing-locks")


if __name__ == "__main__":
    unittest.main()
