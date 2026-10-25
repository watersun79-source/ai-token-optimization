"""Negative and positive byte-level provenance checks; no external service calls."""
import hashlib
import json
import zipfile
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
        for filename in ("evidence.json", "utc_strict_oracle_cases.tsv"):
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
                         "utc_strict_oracle.js", "test_runtime.py", "measure_runtime.py",
                         "replacement_bots.py", "fixture_SYNTHETIC.json"):
            with self.subTest(filename=filename):
                self.assertEqual("DIFFERENT", report["files"][filename]["status"])

    def test_public_fixture_not_original_bytes(self):
        report = parity.compare()
        self.assertEqual("DIFFERENT", report["files"]["fixture_SYNTHETIC.json"]["status"])
        self.assertIn("fixture_SYNTHETIC.json", report["reviewed_differences"])
        self.assertFalse(report["verbatim_source_match"])

    def test_reviewed_hardening_differences_do_not_claim_exact(self):
        report = parity.compare()
        for filename in ("runner.py", "test_runtime.py", "utc_strict_oracle.js",
                         "measure_runtime.py", "UtcStrictOracle.java", "catalog.json",
                         "replacement_bots.py", "fixture_SYNTHETIC.json"):
            with self.subTest(filename=filename):
                self.assertEqual("DIFFERENT", report["files"][filename]["status"])
                self.assertEqual(
                    "KEEP_BRANCH_HARDENING",
                    report["reviewed_differences"][filename]["disposition"],
                )
        self.assertEqual(8, report["reviewed_difference_count"])
        self.assertEqual(0, report["unresolved_difference_count"])
        self.assertFalse(report["verbatim_source_match"])
        self.assertFalse(report["full_v81_deployed"])

    def test_reviewed_catalog_hardening_stays_non_verbatim(self):
        # No private original catalog is committed to the public CI runner.
        rules = json.loads((parity.ROOT / "catalog.json").read_text(encoding="utf-8"))
        roles = {r["id"]: r for r in rules}
        self.assertEqual(100, len(rules))
        self.assertEqual(100, len(roles))
        for role_id in ("S04", "S05", "S06"):
            with self.subTest(strict_rrule=role_id):
                self.assertEqual("rrule_part", roles[role_id]["operator"])
                self.assertEqual("schedule.rrule", roles[role_id]["field"])
        native_ids = ({f"L{i:02d}" for i in range(6, 11)}
                      | {f"A{i:02d}" for i in range(7, 10)}
                      | {f"E{i:02d}" for i in range(1, 11)})
        actual_native = {r["id"] for r in rules
                         if r["evidence_source"] == "ChatGPT.native_per_run_raw_ledger"}
        self.assertEqual(native_ids, actual_native)
        for role_id in sorted(native_ids):
            with self.subTest(native_role=role_id):
                self.assertTrue(roles[role_id]["field"].startswith("native."))
                self.assertNotEqual("offline_replacement", roles[role_id]["operator"])
                self.assertEqual("offline_evidence_rule", roles[role_id]["scope"])
        report = parity.compare()
        self.assertEqual("DIFFERENT", report["files"]["catalog.json"]["status"])
        self.assertEqual(
            "KEEP_BRANCH_HARDENING",
            report["reviewed_differences"]["catalog.json"]["disposition"],
        )
        self.assertFalse(report["verbatim_source_match"])
        self.assertFalse(report["full_v81_deployed"])

    def test_missing_reviewed_file_must_stay_unresolved(self):
        # Previously reviewed hardening applies only while its source file exists.
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "runner.py").write_bytes(b"isolated modified source")
            report = parity.compare(root)
            self.assertEqual("DIFFERENT", report["files"]["runner.py"]["status"])
            self.assertIn("runner.py", report["reviewed_differences"])
            self.assertEqual(1, report["reviewed_difference_count"])
            self.assertEqual(9, report["unresolved_difference_count"])
            for name in ("test_runtime.py", "utc_strict_oracle.js", "measure_runtime.py",
                         "UtcStrictOracle.java", "replacement_bots.py"):
                with self.subTest(absent=name):
                    self.assertEqual("ABSENT", report["files"][name]["status"])
                    self.assertNotIn(name, report["reviewed_differences"])
                    self.assertIn(name, report["unresolved_difference_files"])
            self.assertFalse(report["verbatim_source_match"])
            self.assertFalse(report["full_v81_deployed"])

    def test_public_bridge_is_not_original_source_or_native_proof(self):
        report = parity.compare()
        self.assertEqual("DIFFERENT", report["files"]["replacement_bots.py"]["status"])
        self.assertIn("replacement_bots.py", report["reviewed_differences"])
        self.assertEqual([], report["unresolved_difference_files"])
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
            self.assertEqual(0, result["reviewed_difference_count"])
            self.assertEqual(10, result["unresolved_difference_count"])
            self.assertFalse(result["verbatim_source_match"])
            self.assertFalse(result["native_chatgpt_scheduled_calls_verified"])
            self.assertEqual(0, result["external_llm_calls"])


    @staticmethod
    def _fake_archive(root, members):
        path = root / "only-local.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, content in members:
                z.writestr(name, content)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_local_private_zip_synthetic_happy_path_without_leak(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source = b"private synthetic fake contents"
            z, digest = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/runner.py", source)])
            report = parity.verify_private_zip_local(
                z, expected_zip_sha256=digest,
                expected_hashes={"runner.py": hashlib.sha256(source).hexdigest()})
            self.assertEqual("PASS", report["status"])
            self.assertEqual(1, report["member_sha256_verified"])
            self.assertFalse(report["private_bytes_published"])
            self.assertFalse(report["native_chatgpt_run_verified"])
            self.assertFalse(report["full_v81_deployed"])
            self.assertNotIn(source.decode(), str(report))

    def test_local_private_zip_rejects_wrong_archive_sha(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            z, _ = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/runner.py", b"test")])
            with self.assertRaisesRegex(ValueError, "PRIVATE_ZIP_SHA256_MISMATCH"):
                parity.verify_private_zip_local(z)

    def test_local_private_zip_rejects_member_sha_mismatch(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            z, digest = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/runner.py", b"altered")])
            with self.assertRaisesRegex(ValueError, "PRIVATE_ZIP_MEMBER_SHA256_MISMATCH"):
                parity.verify_private_zip_local(
                    z, expected_zip_sha256=digest,
                    expected_hashes={"runner.py": hashlib.sha256(b"real").hexdigest()})

    def test_local_private_zip_rejects_missing_expected_source(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            z, digest = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/other.py", b"test")])
            with self.assertRaisesRegex(ValueError, "PRIVATE_ZIP_EXPECTED_FILE_MISSING"):
                parity.verify_private_zip_local(
                    z, expected_zip_sha256=digest,
                    expected_hashes={"runner.py": hashlib.sha256(b"test").hexdigest()})

    def test_local_private_zip_rejects_duplicate_and_traversal_entries(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            for suffix, entry in enumerate((
                    "AI_R16_100_BOT_v8/../runner.py",
                    "/AI_R16_100_BOT_v8/runner.py",
                    "AI_R16_100_BOT_v8\\runner.py")):
                z, digest = self._fake_archive(
                    root, [("AI_R16_100_BOT_v8/runner.py", b"test"),
                           (entry, b"bad")])
                with self.subTest(suffix=suffix), self.assertRaisesRegex(
                        ValueError, "PRIVATE_ZIP_UNSAFE_ENTRY"):
                    parity.verify_private_zip_local(
                        z, expected_zip_sha256=digest,
                        expected_hashes={"runner.py": hashlib.sha256(b"test").hexdigest()})
            z, digest = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/runner.py", b"one"),
                       ("AI_R16_100_BOT_v8/runner.py", b"two")])
            with self.assertRaisesRegex(ValueError, "PRIVATE_ZIP_UNSAFE_ENTRY"):
                parity.verify_private_zip_local(
                    z, expected_zip_sha256=digest,
                    expected_hashes={"runner.py": hashlib.sha256(b"one").hexdigest()})

    def test_local_private_zip_rejects_symlink_archive(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            z, digest = self._fake_archive(
                root, [("AI_R16_100_BOT_v8/runner.py", b"test")])
            link = root / "linked.zip"
            link.symlink_to(z)
            with self.assertRaisesRegex(ValueError, "PRIVATE_ZIP_NOT_REGULAR_FILE"):
                parity.verify_private_zip_local(
                    link, expected_zip_sha256=digest,
                    expected_hashes={"runner.py": hashlib.sha256(b"test").hexdigest()})

    def test_local_private_zip_cli_fails_closed_without_source(self):
        with TemporaryDirectory() as d:
            missing = Path(d) / "unavailable-private.zip"
            import contextlib
            import io
            from unittest.mock import patch
            with patch("sys.argv", ["v81_source_parity.py", "--verify-private-zip-local",
                                    str(missing)]), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(2, parity.main())
            self.assertIn('"status": "UNVERIFIED"', out.getvalue())
            self.assertNotIn(str(missing), out.getvalue())


if __name__ == "__main__":
    unittest.main()
