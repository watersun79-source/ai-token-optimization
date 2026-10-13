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

    def assert_positive_integer(self, value, field):
        self.assertIsInstance(value, int, f"{field} must be an integer")
        self.assertNotIsInstance(value, bool, f"{field} must not be boolean")
        self.assertGreater(value, 0, f"{field} must be positive")

    def test_call_limits_are_positive_and_bounded(self):
        routing = self.policy["routing"]
        simple_calls = routing["simple_question"]["max_ai_calls"]
        complex_calls = routing["complex_question"]["max_ai_calls"]
        self.assert_positive_integer(simple_calls, "simple_question.max_ai_calls")
        self.assertEqual(simple_calls, 1)
        self.assert_positive_integer(complex_calls, "complex_question.max_ai_calls")
        self.assertLessEqual(complex_calls, 2)

    def test_output_and_search_limits(self):
        limits = self.policy["limits"]
        self.assert_positive_integer(limits["max_prompt_chars"], "max_prompt_chars")
        self.assert_positive_integer(
            limits["max_output_tokens_default"], "max_output_tokens_default"
        )
        search_uses = limits["max_web_search_uses"]
        self.assertIsInstance(search_uses, int, "max_web_search_uses must be an integer")
        self.assertNotIsInstance(search_uses, bool, "max_web_search_uses must not be boolean")
        self.assertGreaterEqual(search_uses, 0)
        self.assertLessEqual(search_uses, 2)

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
        self.assertTrue(
            any("Do not change, disable, delete, or reschedule" in item for item in actions)
        )
        self.assertTrue(
            any(
                "Report configured, attempted, and verified-success states separately" in item
                for item in actions
            )
        )

    def test_research_is_free_first_and_bounded(self):
        routing = self.policy["routing"]
        research = routing["internet_research"]
        self.assertTrue(research["enabled"])
        self.assertTrue(research["free_first"])
        self.assertTrue(research["paid_search_or_api_calls_require_explicit_approval"])
        budget = research["search_budget"]
        self.assertEqual(budget["default_max_searches"], 2)
        self.assertTrue(budget["reuse_results_within_run"])
        self.assertTrue(budget["avoid_duplicate_queries"])
        self.assertLessEqual(self.policy["limits"]["max_web_search_uses"], 2)

    def test_paid_external_ai_calls_are_not_implicitly_allowed(self):
        limits = self.policy["limits"]
        self.assertTrue(
            any("Never call paid external AI APIs unless explicitly approved" in rule
                for rule in limits["token_optimization"])
        )

    def test_independent_review_is_restricted(self):
        review = self.policy["routing"]["independent_third_review"]
        self.assertFalse(review["enabled"])
        self.assertEqual(
            review["allow_only_when"],
            "material_risk_or_high_value_verification",
        )


if __name__ == "__main__":
    unittest.main()
