import tempfile
from pathlib import Path
import unittest
from bot_coordinator import dispatch, select_roles


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
