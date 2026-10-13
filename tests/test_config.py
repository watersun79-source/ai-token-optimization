import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PolicyConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "config" / "policy.json").read_text(encoding="utf-8"))

    def test_call_limits_are_positive(self):
        routing = self.policy["routing"]
        self.assertEqual(routing["simple_question"]["max_ai_calls"], 1)
        self.assertLessEqual(routing["complex_question"]["max_ai_calls"], 2)

    def test_output_and_search_limits(self):
        limits = self.policy["limits"]
        self.assertGreater(limits["max_output_tokens_default"], 0)
        self.assertLessEqual(limits["max_web_search_uses"], 2)

    def test_secrets_and_execution_claims_protected(self):
        safety = self.policy["safety"]
        self.assertTrue(safety["never_claim_unverified_execution"])
        self.assertTrue(safety["never_commit_secrets"])
        self.assertTrue(safety["distinguish_mock_tests_from_production"])

if __name__ == "__main__":
    unittest.main()
