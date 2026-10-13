"""Regression tests driven by the same fixtures as the JavaScript validator."""
import json
import unittest
from pathlib import Path

from tools.json_output_validator import validate


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "json_validator_cases.json"


class JsonOutputValidatorSharedFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_all_shared_cases_match_expected_errors(self):
        for case in self.fixtures["cases"]:
            with self.subTest(case=case["id"]):
                if "raw_input" in case:
                    from tools.json_output_validator import extract_json
                    try:
                        value = extract_json(case["raw_input"])
                        errors = validate(value)
                    except ValueError:
                        errors = ["invalid_json"]
                else:
                    errors = validate(case["input"])
                self.assertEqual(errors, case["expected_errors"])


if __name__ == "__main__":
    unittest.main()
