"""Run the real Java oracle against resized/malformed fixture files."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class JavaFixtureCoverageTests(unittest.TestCase):
    def run_fixture(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / 'UtcStrictOracle.java', root / 'UtcStrictOracle.java')
            (root / 'utc_strict_oracle_cases.tsv').write_text(
                '\n'.join(rows) + '\n', encoding='utf8')
            return subprocess.run(['java', str(root / 'UtcStrictOracle.java')],
                                  cwd=root, capture_output=True, text=True, timeout=30)

    def rows(self):
        return (ROOT / 'utc_strict_oracle_cases.tsv').read_text().splitlines()

    def test_added_failing_case_cannot_be_silently_ignored(self):
        result = self.run_fixture(self.rows() + ['not-a-date\tPASS'])
        self.assertNotEqual(0, result.returncode, result.stdout)

    def test_added_passing_case_is_in_measured_total(self):
        result = self.run_fixture(self.rows() + ['2026-10-24T05:00:00Z\tPASS'])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('PASS 21/21', result.stdout)

    def test_smaller_valid_fixture_uses_its_actual_size(self):
        result = self.run_fixture([self.rows()[0], '2026-10-24T05:00:00Z\tPASS'])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('PASS 1/1', result.stdout)

    def test_no_cases_cannot_emit_success(self):
        result = self.run_fixture([self.rows()[0]])
        self.assertNotEqual(0, result.returncode, result.stdout)

    def test_malformed_appended_case_cannot_be_ignored(self):
        result = self.run_fixture(self.rows() + ['not-a-date\tFAIL\textra'])
        self.assertNotEqual(0, result.returncode, result.stdout)


if __name__ == '__main__':
    unittest.main()
