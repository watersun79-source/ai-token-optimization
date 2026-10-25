"""Offline swarm real local grouping and independent fail-closed verification."""
import json
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import v81_swarm as swarm

ROOT = Path(__file__).resolve().parent


def sources():
    return (json.loads((ROOT / "catalog.json").read_text(encoding="utf8")),
            json.loads((ROOT / "evidence.json").read_text(encoding="utf8")))


class SwarmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog, cls.evidence = sources()

    def test_fast_twenty_roles_with_independent_oracle(self):
        report = swarm.collaborate(self.catalog, self.evidence)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(20, report["selected_roles"])
        self.assertEqual(2, report["group_count"])
        self.assertEqual(2, report["effective_worker_cap"])
        self.assertEqual(["E", "S"], report["category_groups"])
        self.assertTrue(report["independent_serial_oracle_match"])
        self.assertEqual({"PASS": 20}, report["status_counts"])
        self.assertFalse(report["native_chatgpt_run_verified"])

    def test_all_hundred_groups_are_sharded_with_oracle(self):
        report = swarm.collaborate(self.catalog, self.evidence, "all")
        self.assertEqual(100, report["selected_roles"])
        self.assertEqual(10, report["group_count"])
        self.assertEqual(4, report["effective_worker_cap"])
        self.assertEqual(18, report["replacements_fixture_only"])
        self.assertTrue(report["independent_serial_oracle_match"])
        self.assertIn(report["status"], ("PASS", "UNVERIFIED", "FAIL"))
        self.assertFalse(report["original_v81_source_deployed"])

    def test_input_order_does_not_change_role_statuses(self):
        a = swarm.collaborate(self.catalog, self.evidence, "audit", 1)
        b = swarm.collaborate(list(reversed(self.catalog)), self.evidence, "audit", 4)
        self.assertEqual(a["status_counts"], b["status_counts"])
        self.assertTrue(b["independent_serial_oracle_match"])
        self.assertNotEqual(a["input_sha256"], b["input_sha256"])

    def test_local_parallelism_peak_measured_and_bounded(self):
        original = swarm._category
        active, peak = 0, 0
        lock = threading.Lock()
        def measured(group, evidence, fixture):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.012)
                return original(group, evidence, fixture)
            finally:
                with lock:
                    active -= 1
        with patch.object(swarm, "_category", measured):
            report = swarm.collaborate(self.catalog, self.evidence, "all", 4)
        self.assertTrue(report["independent_serial_oracle_match"])
        self.assertGreaterEqual(peak, 2)
        self.assertLessEqual(peak, 4)

    def test_fake_native_fields_never_earn_native_proof(self):
        changed = json.loads(json.dumps(self.evidence))
        changed["native"] = {"official_run_id": "FAKE", "status": "success"}
        result = swarm.collaborate(self.catalog, changed)
        self.assertFalse(result["native_chatgpt_run_verified"])
        self.assertFalse(result["same_run_github_slack_proven"])
        self.assertEqual(0, result["external_provider_calls"])

    def test_real_failed_role_stays_fail(self):
        changed = json.loads(json.dumps(self.evidence))
        changed["schedule"]["enabled"] = False
        result = swarm.collaborate(self.catalog, changed)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("S02", result["failed_or_unknown_roles"])

    def test_corrupt_parallel_result_blocks_even_with_pass_count(self):
        original = swarm._category
        def corrupt(group, evidence, fixture):
            rows = original(group, evidence, fixture)
            if rows[0]["id"] == "S01":
                rows[0]["status"] = "FAIL"
            return rows
        with patch.object(swarm, "_category", corrupt):
            result = swarm.collaborate(self.catalog, self.evidence)
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual("INDEPENDENT_ORACLE_MISMATCH", result["reason"])

    def test_worker_error_is_redacted_and_never_retried(self):
        calls = []
        def error(group, evidence, fixture):
            calls.append(group[0])
            raise RuntimeError("PRIVATE-CREDENTIAL-MUST-NOT-LEAK")
        with patch.object(swarm, "_category", error):
            result = swarm.collaborate(self.catalog, self.evidence)
        self.assertEqual("BLOCKED", result["status"])
        self.assertNotIn("PRIVATE-CREDENTIAL", str(result))
        self.assertLessEqual(len(calls), 2)

    def test_limits_and_catalog_shape_fail_closed(self):
        for n in (0, -1, 5, True, "4"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                swarm.collaborate(self.catalog, self.evidence, max_workers=n)
        with self.assertRaises(ValueError):
            swarm.collaborate(self.catalog[:99], self.evidence)
        with self.assertRaises(ValueError):
            swarm.collaborate(self.catalog, self.evidence, mode="remote")
        with self.assertRaises(ValueError):
            swarm.collaborate(self.catalog, [])
        with self.assertRaises(ValueError):
            swarm.collaborate(self.catalog, self.evidence, fixture=[])

    def test_redefined_rule_with_same_100_ids_is_blocked(self):
        forged = json.loads(json.dumps(self.catalog))
        next(x for x in forged if x["id"] == "S02")["expected"] = False
        with self.assertRaisesRegex(ValueError, "catalog"):
            swarm.collaborate(forged, self.evidence, "audit")

    def test_wrong_native_role_metadata_is_blocked(self):
        forged = json.loads(json.dumps(self.catalog))
        role = next(x for x in forged if x["id"] == "E10")
        role.update(field="schedule.enabled", operator="eq",
                    expected=True, evidence_source="automations.peek")
        with self.assertRaisesRegex(ValueError, "catalog"):
            swarm.collaborate(forged, self.evidence, "all")

    def test_provider_and_operational_side_effects_remain_zero(self):
        result = swarm.collaborate(self.catalog, self.evidence)
        self.assertEqual("ISOLATED_OFFLINE_SWARM_NOT_NATIVE", result["kind"])
        self.assertEqual(0, result["external_model_calls"])
        self.assertEqual(0, result["external_provider_calls"])
        self.assertEqual(0, result["production_changes"])


if __name__ == "__main__":
    unittest.main()
