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
        self.assertLessEqual(search_uses, 3)

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
        self.assertFalse(research["paid_search_or_api_calls_allowed"])
        self.assertNotIn("paid_search_or_api_calls_require_explicit_approval", research)
        budget = research["search_budget"]
        self.assertEqual(budget["default_max_searches"], 2)
        self.assertTrue(budget["reuse_results_within_run"])
        self.assertTrue(budget["avoid_duplicate_queries"])
        self.assertEqual(self.policy["limits"]["max_web_search_uses"], 3)
        self.assertLessEqual(
            budget["default_max_searches"],
            self.policy["limits"]["max_web_search_uses"],
            "default search budget must not exceed the hard global limit",
        )

    def test_source_priority_covers_required_research_sources(self):
        research = self.policy["routing"]["internet_research"]
        sources = " ".join(research["source_priority"]).lower()
        self.assertIn("official documentation and release notes", sources)
        self.assertIn("target repository, tests, issues, pull requests, and ci runs", sources)
        self.assertIn("official github repositories and changelogs", sources)
        self.assertIn("web search and exa", sources)

    def test_token_optimization_deduplicates_and_stops_after_verification(self):
        rules = " ".join(self.policy["limits"]["token_optimization"]).lower()
        self.assertIn("deduplicate results", rules)
        self.assertIn("stop once decision-critical facts are verified", rules)

    def test_scheduled_search_limit_matches_configured_budget(self):
        research = self.policy["routing"]["internet_research"]
        budget = research["search_budget"]["default_max_searches"]
        actions = " ".join(self.policy["scheduled_automation"]["on_each_run"]).lower()
        self.assertEqual(budget, 2)
        self.assertIn("default to at most two searches", actions)
        self.assertIn("use a third only when sources conflict", actions)
        self.assertIn("never exceed three", actions)
        self.assertNotIn("default to at most three searches", actions)

    def test_paid_external_ai_calls_are_prohibited(self):
        limits = self.policy["limits"]
        rules = limits["token_optimization"]
        self.assertTrue(any(
            "Never call paid external AI APIs;" in rule
            for rule in rules
        ))
        self.assertFalse(any(
            "paid external AI APIs unless explicitly approved" in rule
            for rule in rules
        ))
        self.assertTrue(any("Never create paid caches;" in rule for rule in rules))
        self.assertFalse(any(
            "paid caches without explicit approval" in rule
            for rule in rules
        ))
        self.assertTrue(any("zero external AI API calls" in rule for rule in rules))
        self.assertTrue(any("separate token-count API request" in rule for rule in rules))

    def test_scheduled_automation_prohibits_paid_search_and_api_calls(self):
        actions = self.policy["scheduled_automation"]["on_each_run"]
        self.assertTrue(any(
            "Never make paid search/API/model calls" in rule
            for rule in actions
        ))
        self.assertFalse(any(
            "paid search/API/model calls require explicit approval" in rule
            for rule in actions
        ))

    def test_paid_or_unverified_provider_calls_are_blocked(self):
        guard = self.policy["cost_guard"]
        self.assertFalse(guard["paid_model_api_calls_allowed"])
        self.assertTrue(guard["provider_call_requires_verified_free_quota"])
        self.assertEqual(guard["unknown_quota_action"], "block")
        self.assertTrue(guard["provider_connection_is_not_quota_evidence"])
        self.assertTrue(guard["record_actual_provider_calls_and_costs"])
    def test_independent_review_is_restricted(self):
        review = self.policy["routing"]["independent_third_review"]
        self.assertFalse(review["enabled"])
        self.assertEqual(
            review["allow_only_when"],
            "material_risk_or_high_value_verification",
        )


if __name__ == "__main__":
    unittest.main()
