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

    def test_explicit_fixture_is_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / 'UtcStrictOracle.java', root / 'UtcStrictOracle.java')
            fixture = root / 'utc_strict_oracle_cases.tsv'
            fixture.write_text('\n'.join(self.rows()) + '\n', encoding='utf8')
            with tempfile.TemporaryDirectory() as outside:
                result = subprocess.run(
                    ['java', str(root / 'UtcStrictOracle.java'), str(fixture)],
                    cwd=outside, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('PASS 20/20', result.stdout)

    def test_explicit_missing_fixture_fails_even_if_default_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / 'UtcStrictOracle.java', root / 'UtcStrictOracle.java')
            (root / 'utc_strict_oracle_cases.tsv').write_text(
                '\n'.join(self.rows()) + '\n', encoding='utf8')
            result = subprocess.run(
                ['java', str(root / 'UtcStrictOracle.java'), str(root / 'missing.tsv')],
                cwd=root, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(0, result.returncode)

    def test_multiple_fixture_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / 'UtcStrictOracle.java', root / 'UtcStrictOracle.java')
            (root / 'utc_strict_oracle_cases.tsv').write_text(
                '\n'.join(self.rows()) + '\n', encoding='utf8')
            result = subprocess.run(
                ['java', str(root / 'UtcStrictOracle.java'),
                 str(root / 'utc_strict_oracle_cases.tsv'), 'unused'],
                cwd=root, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(0, result.returncode)

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


    def test_oversized_fixture_is_rejected_before_parsing(self):
        body = "value\\texpected\\n" + ("x" * 65536) + "\\tFAIL\\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT / 'UtcStrictOracle.java', root / 'UtcStrictOracle.java')
            fixture = root / 'utc_strict_oracle_cases.tsv'
            fixture.write_text(body, encoding='utf8')
            result = subprocess.run(
                ['java', str(root / 'UtcStrictOracle.java'), str(fixture)],
                cwd=root, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Fixture size or type invalid', result.stderr)

    def test_more_than_256_cases_are_rejected(self):
        row = '2026-10-24T05:00:00Z\\tPASS'
        result = self.run_fixture([self.rows()[0]] + [row] * 257)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Too many fixture cases', result.stderr)

    def test_symlink_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = root / 'worker'
            worker.mkdir()
            target = root / 'external.tsv'
            target.write_text(
                'value\\texpected\\n2026-10-24T05:00:00Z\\tPASS\\n',
                encoding='utf8')
            shutil.copyfile(ROOT / 'UtcStrictOracle.java',
                            worker / 'UtcStrictOracle.java')
            fixture = worker / 'utc_strict_oracle_cases.tsv'
            fixture.symlink_to(target)
            result = subprocess.run(
                ['java', str(worker / 'UtcStrictOracle.java'), str(fixture)],
                cwd=worker, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Fixture size or type invalid', result.stderr)


if __name__ == '__main__':
    unittest.main()
