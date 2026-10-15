"""Run the shared validator fixtures against the Python implementation."""
import json
from pathlib import Path
import unittest

from tools.json_output_validator import extract_json, validate


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "json_validator_cases.json"


class SharedFixtureParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"]

    def test_all_shared_fixtures_match_expected_errors(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                if "raw_input" in case:
                    try:
                        value = extract_json(case["raw_input"])
                    except ValueError:
                        actual_errors = ["invalid_json"]
                    else:
                        actual_errors = validate(value)
                else:
                    actual_errors = validate(case["input"])
                self.assertEqual(actual_errors, case["expected_errors"])


if __name__ == "__main__":
    unittest.main()
