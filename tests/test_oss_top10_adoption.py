"""Offline tests runnable from repository root without third-party dependencies."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "oss-top10-safe-adoption" / "safe_adoption.py"
CATALOG = MODULE.with_name("catalog.json")
spec = importlib.util.spec_from_file_location("safe_adoption", MODULE)
safe_adoption = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safe_adoption)


class TestOssTop10Adoption(unittest.TestCase):
    def setUp(self):
        self.catalog = safe_adoption.load_catalog(CATALOG)

    def test_all_ten_official_projects_reviewed(self):
        plan = safe_adoption.create_plan(self.catalog)
        self.assertEqual(plan["reviewed_count"], 10)
        self.assertEqual(len(plan["decision"]), 10)

    def test_zero_imports_calls_cost_and_writes(self):
        plan = safe_adoption.create_plan(self.catalog)
        for key in ("installed_upstream_packages", "runtime_upstream_integrations_verified", "external_ai_calls", "production_writes"):
            self.assertEqual(plan[key], 0)

    def test_flowise_blocked_due_to_end_of_life(self):
        plan = safe_adoption.create_plan(self.catalog)
        match = next(p for p in plan["decision"] if p["id"] == "flowise")
        self.assertEqual(match["status"], "BLOCKED_EOL")

    def test_archived_must_not_be_candidate(self):
        bad = copy.deepcopy(self.catalog)
        next(p for p in bad["projects"] if p["id"] == "flowise")["mode"] = "primary_candidate"
        with self.assertRaises(safe_adoption.SafetyBlock):
            safe_adoption.create_plan(bad)

    def test_license_and_enterprise_separation(self):
        self.assertIn("commercial", next(p for p in self.catalog["projects"] if p["id"] == "activepieces")["license"].lower())
        self.assertIn("EE", next(p for p in self.catalog["projects"] if p["id"] == "langfuse")["license"])

    def test_all_write_install_api_guards_are_false(self):
        self.assertTrue(all(v is False for v in self.catalog["guard_policy"].values()))

    def test_guard_cannot_be_relaxed(self):
        for key in self.catalog["guard_policy"]:
            with self.subTest(key=key):
                bad = copy.deepcopy(self.catalog)
                bad["guard_policy"][key] = True
                with self.assertRaises(safe_adoption.SafetyBlock):
                    safe_adoption.create_plan(bad)

    def test_guard_cannot_be_removed(self):
        bad = copy.deepcopy(self.catalog)
        del bad["guard_policy"]["allow_paid_api"]
        with self.assertRaises(safe_adoption.SafetyBlock):
            safe_adoption.create_plan(bad)

    def test_conflicting_primary_orchestrators_rejected(self):
        bad = copy.deepcopy(self.catalog)
        next(p for p in bad["projects"] if p["id"] == "crewai")["mode"] = "primary_candidate"
        with self.assertRaises(safe_adoption.SafetyBlock):
            safe_adoption.create_plan(bad)

    def test_conflicting_primary_memory_rejected(self):
        bad = copy.deepcopy(self.catalog)
        next(p for p in bad["projects"] if p["id"] == "letta")["mode"] = "primary_candidate"
        with self.assertRaises(safe_adoption.SafetyBlock):
            safe_adoption.create_plan(bad)

    def test_extra_and_missing_project_rejected(self):
        for alter in (lambda x: x.pop(), lambda x: x.append(copy.deepcopy(x[0]))):
            with self.subTest(alter=alter):
                bad = copy.deepcopy(self.catalog)
                alter(bad["projects"])
                with self.assertRaises(safe_adoption.SafetyBlock):
                    safe_adoption.create_plan(bad)

    def test_non_plan_actions_fail_closed(self):
        for action in (*sorted(safe_adoption.RESTRICTED_ACTIONS), "anything_else"):
            with self.subTest(action=action):
                with self.assertRaises(safe_adoption.SafetyBlock):
                    safe_adoption.create_plan(self.catalog, action=action)

    def test_deterministic_plan(self):
        self.assertEqual(safe_adoption.create_plan(self.catalog), safe_adoption.create_plan(copy.deepcopy(self.catalog)))


if __name__ == "__main__":
    unittest.main()
