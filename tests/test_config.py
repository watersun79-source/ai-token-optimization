import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PolicyConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(
            (ROOT / "config" / "policy.json").read_text(encoding="utf-8")
        )

    def test_call_limits_are_positive_and_bounded(self):
        routing = self.policy["routing"]
        simple_calls = routing["simple_question"]["max_ai_calls"]
        complex_calls = routing["complex_question"]["max_ai_calls"]
        self.assertIsInstance(simple_calls, int)
        self.assertGreaterEqual(simple_calls, 1)
        self.assertEqual(simple_calls, 1)
        self.assertIsInstance(complex_calls, int)
        self.assertGreaterEqual(complex_calls, 1)
        self.assertLessEqual(complex_calls, 2)

    def test_output_and_search_limits(self):
        limits = self.policy["limits"]
        self.assertGreater(limits["max_prompt_chars"], 0)
        self.assertGreater(limits["max_output_tokens_default"], 0)
        self.assertGreaterEqual(limits["max_web_search_uses"], 0)
        self.assertLessEqual(limits["max_web_search_uses"], 2)

    def test_secrets_and_execution_claims_protected(self):
        safety = self.policy["safety"]
        self.assertTrue(safety["never_claim_unverified_execution"])
        self.assertTrue(safety["never_commit_secrets"])
        self.assertTrue(safety["distinguish_mock_tests_from_production"])
        self.assertTrue(safety["avoid_duplicate_model_calls"])

    def test_automation_is_enabled_and_protected_from_unapproved_changes(self):
        automation = self.policy["scheduled_automation"]
        self.assertTrue(automation["enabled"])
        actions = automation["on_each_run"]
        self.assertTrue(any("Do not change, disable, delete, or reschedule" in item for item in actions))
        self.assertTrue(any("Report configured, attempted, and verified-success states separately" in item for item in actions))

    def test_independent_review_is_restricted(self):
        review = self.policy["routing"]["independent_third_review"]
        self.assertFalse(review["enabled"])
        self.assertEqual(
            review["allow_only_when"],
            "material_risk_or_high_value_verification",
        )


if __name__ == "__main__":
    unittest.main()
