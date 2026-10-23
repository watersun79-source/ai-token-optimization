import tempfile
from pathlib import Path
import unittest
from bot_coordinator import dispatch, select_roles, evaluate_selected_rules


class CoordinatorTests(unittest.TestCase):
    def test_audit_selects_relevant_roles(self):
        self.assertEqual(select_roles("audit"), ("scheduled_audit", "verify"))

    def test_build_selects_review_roles(self):
        self.assertEqual(select_roles("build"), ("research", "build", "verify"))

    def test_missing_role_id_fails_closed(self):
        import json
        from bot_coordinator import verify_role_catalog
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps([{"id": "G01"}]))
            with self.assertRaisesRegex(ValueError, "missing catalog role IDs"):
                verify_role_catalog(path)

    def test_duplicate_role_id_fails_closed(self):
        import json
        from bot_coordinator import verify_role_catalog
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps([{"id": "G01"}, {"id": "G01"}]))
            with self.assertRaisesRegex(ValueError, "duplicate catalog role ID"):
                verify_role_catalog(path)

    def test_selected_audit_executes_only_twenty_rules(self):
        result = evaluate_selected_rules("audit")
        self.assertEqual(result["executed_selected_rule_checks"], 20)
        self.assertEqual(len(result["selected_result_statuses"]), 20)
        self.assertEqual(set(result["selected_statuses"]), {"PASS", "UNVERIFIED"})
        self.assertEqual(result["selected_outcome"], "UNVERIFIED")
        self.assertEqual(result["selected_evidence_scope"],
                         "OFFLINE_SNAPSHOT_NOT_PROVIDER_AUTHENTICATED")
        self.assertEqual(set(item["id"][0] for item in result["selected_result_statuses"]),
                         {"E", "G"})

    def test_selected_verify_executes_ten_rules(self):
        result = evaluate_selected_rules("verify")
        self.assertEqual(result["executed_selected_rule_checks"], 10)
        self.assertEqual(set(item["id"][0] for item in result["selected_result_statuses"]), {"G"})

    def test_selected_tampered_ci_failure_is_not_pass(self):
        import copy
        import json
        from bot_coordinator import RUNTIME_ROOT
        original = json.loads((RUNTIME_ROOT / "evidence.json").read_text())
        tampered = copy.deepcopy(original)
        tampered["github"]["ci_conclusion"] = "failure"
        result = evaluate_selected_rules("audit", evidence=tampered)
        self.assertEqual(result["selected_outcome"], "FAIL")
        self.assertGreaterEqual(result["selected_statuses"].get("FAIL", 0), 1)

    def test_selected_missing_bot_fails_closed(self):
        import json
        from bot_coordinator import RUNTIME_ROOT
        catalog = json.loads((RUNTIME_ROOT / "catalog.json").read_text())
        without_e = [item for item in catalog if item["id"] != "E01"]
        with self.assertRaisesRegex(ValueError, "selected rule ID missing"):
            evaluate_selected_rules("audit", catalog=without_e)

    def test_selected_forged_native_still_unverified(self):
        import copy
        import json
        from bot_coordinator import RUNTIME_ROOT
        evidence = copy.deepcopy(json.loads((RUNTIME_ROOT / "evidence.json").read_text()))
        evidence["native"]["authenticated_run_id"] = "fake"
        evidence["native"]["native_authenticity"] = True
        result = evaluate_selected_rules("audit", evidence=evidence)
        self.assertEqual(result["selected_outcome"], "UNVERIFIED")

    def test_unknown_goal_fails_closed(self):
        with self.assertRaises(ValueError):
            select_roles("other")

    def test_receipt_does_not_claim_scheduled_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "ok.py"
            script.write_text("print('ok')\n")
            result = dispatch("audit", Path(tmp) / "state", script=script)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["kind"], "OFFLINE_ROLE_ROUTING_NOT_NATIVE_SCHEDULED_TOOL_CALL")


if __name__ == "__main__":
    unittest.main()
