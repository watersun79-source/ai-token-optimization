"""Regression tests for tools.json_output_validator."""
import unittest

from tools.json_output_validator import extract_json, validate


class JsonOutputValidatorTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "checks": [
                {"label": "48*27", "expected": "1296", "actual": "1296", "correct": True},
                {"label": "1296/48", "expected": "27", "actual": "28", "correct": False},
                {"label": "1296/27", "expected": "48", "actual": "48", "correct": True},
            ],
            "error_count": 1,
            "answer": "검증 결과 오류 1개",
            "confidence": "high",
            "search_used": False,
        }

    def test_valid_payload(self):
        self.assertEqual(validate(self.payload), [])

    def test_wrong_verdict_rejected(self):
        self.payload["checks"][2]["correct"] = False
        self.assertTrue(any("verdict_mismatch" in e for e in validate(self.payload)))

    def test_wrong_error_count_rejected(self):
        self.payload["error_count"] = 0
        self.assertTrue(any("error_count_mismatch" in e for e in validate(self.payload)))

    def test_markdown_fence(self):
        import json
        raw = "```json\n" + json.dumps(self.payload) + "\n```"
        self.assertEqual(validate(extract_json(raw)), [])

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            extract_json('{"checks": ')

    def test_unexpected_top_level_field(self):
        self.payload["extra"] = True
        self.assertTrue(any("unexpected_fields" in e for e in validate(self.payload)))

    def test_confidence_array_and_object_rejected_without_exception(self):
        for confidence in ([], {}):
            with self.subTest(confidence=confidence):
                self.payload["confidence"] = confidence
                self.assertIn(
                    "confidence_must_be_low_medium_or_high",
                    validate(self.payload),
                )

    def test_negative_error_count_rejected_as_non_integer(self):
        self.payload["error_count"] = -1
        self.assertIn("error_count_must_be_integer", validate(self.payload))

    def test_boolean_error_count_rejected(self):
        self.payload["error_count"] = True
        self.assertIn("error_count_must_be_integer", validate(self.payload))


if __name__ == "__main__":
    unittest.main()
