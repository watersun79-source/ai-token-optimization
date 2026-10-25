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

    def test_no_cases_fails(self):
        result = self.run_fixture([self.rows()[0]])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
