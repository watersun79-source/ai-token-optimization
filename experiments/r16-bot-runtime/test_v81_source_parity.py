"""Negative and positive byte-level provenance checks; no external service calls."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import v81_source_parity as parity


class SourceParityTests(unittest.TestCase):
    def test_original_zip_sha_is_bound(self):
        self.assertEqual(64, len(parity.LOCAL_V81_ZIP_SHA256))
        self.assertEqual(10, len(parity.ORIGINAL_SHA256))

    def test_exact_anchor_files(self):
        report = parity.compare()
        for filename in ("evidence.json", "measure_runtime.py", "utc_strict_oracle_cases.tsv"):
            with self.subTest(filename=filename):
                self.assertEqual("EXACT", report["files"][filename]["status"])

    def test_mismatch_is_not_reported_as_verbatim(self):
        report = parity.compare()
        self.assertFalse(report["verbatim_source_match"])
        self.assertFalse(report["full_v81_deployed"])
        self.assertEqual("PARTIAL_NOT_VERBATIM", report["report_status"])

    def test_expected_difference_is_visible(self):
        report = parity.compare()
        for filename in ("runner.py", "catalog.json", "UtcStrictOracle.java",
                         "utc_strict_oracle.js", "test_runtime.py"):
            with self.subTest(filename=filename):
                self.assertEqual("DIFFERENT", report["files"][filename]["status"])

    def test_absent_original_replacement_is_visible(self):
        report = parity.compare()
        for filename in ("replacement_bots.py", "fixture_SYNTHETIC.json"):
            with self.subTest(filename=filename):
                self.assertEqual("ABSENT", report["files"][filename]["status"])

    def test_runner_difference_is_reviewed_without_claiming_exact(self):
        report = parity.compare()
        self.assertEqual("DIFFERENT", report["files"]["runner.py"]["status"])
        self.assertEqual(1, report["reviewed_difference_count"])
        self.assertEqual(6, report["unresolved_difference_count"])
        self.assertEqual(
            "KEEP_BRANCH_HARDENING",
            report["reviewed_differences"]["runner.py"]["disposition"],
        )
        self.assertFalse(report["verbatim_source_match"])
        self.assertFalse(report["full_v81_deployed"])

    def test_false_claim_of_verbatim_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "fail-closed"):
            parity.require_verbatim(parity.compare())

    def test_mutating_shared_source_changes_exact_to_different(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            original = parity.ROOT / "evidence.json"
            (root / "evidence.json").write_bytes(original.read_bytes() + b" ")
            result = parity.compare(root)
            self.assertEqual("DIFFERENT", result["files"]["evidence.json"]["status"])
            self.assertFalse(result["verbatim_source_match"])

    def test_honest_label_for_missing_data(self):
        with TemporaryDirectory() as d:
            result = parity.compare(Path(d))
            self.assertEqual(10, result["counts"]["ABSENT"])
            self.assertFalse(result["verbatim_source_match"])
            self.assertFalse(result["native_chatgpt_scheduled_calls_verified"])
            self.assertEqual(0, result["external_llm_calls"])


if __name__ == "__main__":
    unittest.main()
