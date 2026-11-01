"""Offline synthetic GitHub 403 diagnostic regression tests.

All inputs are fabricated; no token, Site, network request, or scheduler.
"""
import unittest
from tools.isolated_github_403_diagnostics_v8510 import diagnose_github_http, VERSION

NOW = "2026-11-01T00:19:00Z"


def classify(status=403, headers=None, **kwargs):
    return diagnose_github_http(status, {} if headers is None else headers, NOW, **kwargs)


class GitHub403DiagnosticsTests(unittest.TestCase):
    def test_primary_limit_waits_for_reset_even_if_retry_after_short(self):
        result = classify(headers={
            "X-Ratelimit-Remaining": "0", "x-ratelimit-reset": "1793493000",
            "Retry-After": "30",
        })
        self.assertEqual(result["schema"], VERSION)
        self.assertEqual(result["classification"], "PRIMARY_RATE_LIMIT")
        self.assertEqual(result["retry_not_before_utc"], "2026-11-01T00:30:00Z")
        self.assertFalse(result["requires_review"])

    def test_primary_no_reset_fails_closed_and_requires_review(self):
        result = classify(headers={"x-ratelimit-remaining": "0"})
        self.assertEqual(result["classification"], "PRIMARY_RATE_LIMIT")
        self.assertTrue(result["requires_review"])
        self.assertEqual(result["retry_not_before_utc"], "2026-11-01T00:20:00Z")

    def test_secondary_backs_off_at_least_one_minute(self):
        result = classify(headers={"x-ratelimit-remaining": "20"},
                          secondary_limit_signaled=True)
        self.assertEqual(result["classification"], "SECONDARY_RATE_LIMIT")
        self.assertEqual(result["retry_not_before_utc"], "2026-11-01T00:20:00Z")

    def test_repeated_secondary_exponential_capped(self):
        result = classify(429, {"x-ratelimit-remaining": "20"},
                          secondary_limit_signaled=True,
                          repeated_secondary_failures=8)
        self.assertEqual(result["retry_not_before_utc"], "2026-11-01T01:19:00Z")

    def test_retry_after_only_is_not_permission_claim(self):
        result = classify(headers={"retry-after": "180"})
        self.assertEqual(result["classification"], "RATE_LIMIT_RETRY_AFTER")
        self.assertEqual(result["retry_not_before_utc"], "2026-11-01T00:22:00Z")

    def test_403_with_no_headers_remains_unknown(self):
        result = classify()
        self.assertEqual(result["classification"], "PERMISSION_OR_UNKNOWN_LIMIT")
        self.assertIsNone(result["retry_not_before_utc"])
        self.assertTrue(result["requires_review"])

    def test_invalid_header_never_promotes_success(self):
        result = classify(headers={"Retry-After": "https://example.com/secret"})
        self.assertEqual(result["classification"], "INCOMPLETE_OR_INVALID_LIMIT_EVIDENCE")
        self.assertTrue(result["requires_review"])
        self.assertIsNone(result["retry_not_before_utc"])

    def test_no_token_or_raw_header_data_emitted(self):
        marker = "synthetic_private_marker_DO_NOT_RETURN"
        result = classify(headers={"authorization": marker, "x-unknown": marker})
        self.assertNotIn(marker, repr(result))
        self.assertFalse(result["automatic_request_performed"])
        self.assertFalse(result["original_access_restored"])
        self.assertFalse(result["native_run_verified"])

    def test_401_is_authentication_review_not_auto_retry(self):
        result = classify(401, headers={"retry-after": "5"})
        self.assertEqual(result["classification"], "AUTHENTICATION_REVIEW")
        self.assertTrue(result["requires_review"])
        self.assertIsNone(result["retry_not_before_utc"])

    def test_200_has_no_retry_or_restored_access_claim(self):
        result = classify(200, headers={"x-ratelimit-remaining": "40"})
        self.assertEqual(result["classification"], "NOT_RATE_LIMIT_ERROR")
        self.assertIsNone(result["retry_not_before_utc"])
        self.assertFalse(result["original_access_restored"])

    def test_boolean_status_and_failure_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_STATUS"):
            classify(True)
        with self.assertRaisesRegex(ValueError, "INVALID_FAILURE_COUNT"):
            classify(repeated_secondary_failures=True)
        with self.assertRaisesRegex(ValueError, "INVALID_FAILURE_COUNT"):
            classify(repeated_secondary_failures=9)

    def test_naive_time_and_duplicate_case_insensitive_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "NAIVE_OBSERVATION_TIME"):
            diagnose_github_http(403, {}, "2026-11-01T00:19:00")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_HEADER"):
            classify(headers={"Retry-After": "1", "retry-after": "3"})

    def test_malformed_reset_stays_review(self):
        result = classify(headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "bad"})
        self.assertEqual(result["classification"], "INCOMPLETE_OR_INVALID_LIMIT_EVIDENCE")
        self.assertTrue(result["requires_review"])


if __name__ == "__main__":
    unittest.main()
