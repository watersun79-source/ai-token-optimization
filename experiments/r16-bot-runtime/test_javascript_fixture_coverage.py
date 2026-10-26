"""Exercise the real JavaScript oracle against altered fixture files."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class JavaScriptFixtureCoverageTests(unittest.TestCase):
    def run_fixture(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / "utc_strict_oracle.js", root / "utc_strict_oracle.js")
            (root / "utc_strict_oracle_cases.tsv").write_text(
                "\n".join(rows) + "\n", encoding="utf8")
            return subprocess.run(["node", "utc_strict_oracle.js"], cwd=root,
                                  capture_output=True, text=True, timeout=30)

    def rows(self):
        return (ROOT / "utc_strict_oracle_cases.tsv").read_text(encoding="utf8").splitlines()

    def test_script_reads_fixture_relative_to_its_own_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / "utc_strict_oracle.js", root / "utc_strict_oracle.js")
            (root / "utc_strict_oracle_cases.tsv").write_text(
                "\n".join(self.rows()) + "\n", encoding="utf8")
            with tempfile.TemporaryDirectory() as other_dir:
                result = subprocess.run(
                    ["node", str(root / "utc_strict_oracle.js")],
                    cwd=other_dir, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS 20/20", result.stdout)

    def test_added_passing_case_is_counted(self):
        result = self.run_fixture(self.rows() + ["2026-10-24T05:00:00Z\tPASS"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS 21/21", result.stdout)

    def test_bad_expected_result_fails(self):
        result = self.run_fixture(self.rows() + ["not-a-date\tPASS"])
        self.assertNotEqual(result.returncode, 0)

    def test_extra_column_fails(self):
        result = self.run_fixture(self.rows() + ["not-a-date\tFAIL\textra"])
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_header_fails(self):
        result = self.run_fixture(["invalid\theader"] + self.rows()[1:])
        self.assertNotEqual(result.returncode, 0)

    def test_blank_case_fails(self):
        result = self.run_fixture(self.rows() + [""])
        self.assertNotEqual(result.returncode, 0)

    def test_bounded_case_count_rejects_257_but_allows_256(self):
        row = "2026-10-24T05:00:00Z\tPASS"
        accepted = self.run_fixture(["value\texpected"] + [row] * 256)
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        self.assertIn("PASS 256/256", accepted.stdout)
        rejected = self.run_fixture(["value\texpected"] + [row] * 257)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("too many fixture cases", rejected.stderr)
        self.assertNotIn("PASS", rejected.stdout)

    def test_oversized_fixture_is_rejected_before_evaluation(self):
        # 64 KiB is the maximum accepted fixture size; never print user data.
        oversized = "X" * 70000
        result = self.run_fixture(["value\texpected", oversized + "\tFAIL"])
        self.assertNotEqual(0, result.returncode)
        self.assertIn("fixture size or type invalid", result.stderr)
        self.assertNotIn("PASS", result.stdout)

    def test_symlink_fixture_to_external_path_is_refused(self):
        # Refuse a linked fixture even if its target contains valid rows.
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            worker = parent / "worker"
            worker.mkdir()
            external = parent / "external.tsv"
            external.write_text(
                "value\\texpected\\n2026-10-24T05:00:00Z\\tPASS\\n",
                encoding="utf-8")
            shutil.copyfile(ROOT / "utc_strict_oracle.js",
                            worker / "utc_strict_oracle.js")
            (worker / "utc_strict_oracle_cases.tsv").symlink_to(external)
            proc = subprocess.run(
                ["node", str(worker / "utc_strict_oracle.js")],
                cwd=worker, capture_output=True, text=True, timeout=8)
            self.assertNotEqual(0, proc.returncode)
            self.assertNotIn("PASS", proc.stdout)

    def test_failed_case_never_prints_untrusted_fixture_value(self):
        # Negative fixture values might contain private data; avoid CI log leaks.
        marker = "PRIVATE_FIXTURE_CANARY_MUST_NOT_APPEAR_20261027"
        result = self.run_fixture([self.rows()[0], marker + "\tPASS"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(marker, result.stdout + result.stderr)
        self.assertIn("case 1 result mismatch", result.stderr)

    def test_no_cases_fails(self):
        result = self.run_fixture([self.rows()[0]])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
