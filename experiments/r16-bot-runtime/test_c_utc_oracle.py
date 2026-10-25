"""Standalone C11 strict ISO-8601 oracle security checks; fixture is shared by 4 languages."""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class COracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="v81-c-oracle-")
        cls.binary = Path(cls.tmp.name) / "oracle"
        subprocess.run(
            ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-o", str(cls.binary), str(ROOT / "utc_strict_oracle.c")],
            capture_output=True, text=True, check=True, timeout=30,
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_rows(self, entries, header="value\texpected"):
        file = Path(self.tmp.name) / "cases.tsv"
        file.write_text("\n".join([header, *entries]) + "\n", encoding="utf-8")
        return subprocess.run([str(self.binary), str(file)],
                              capture_output=True, text=True, timeout=10, check=False)

    def test_shared_python_java_js_fixture_20_cases(self):
        fixture = ROOT / "utc_strict_oracle_cases.tsv"
        p = subprocess.run([str(self.binary), str(fixture)],
                           capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertRegex(p.stdout, r"^C strict timestamp oracle: PASS 20/20\n$")

    def test_leap_dates_fractions_and_zone_boundaries(self):
        rows = [
            ("2000-02-29T00:00:00Z", "PASS"),
            ("2400-02-29T23:59:59.123456789Z", "PASS"),
            ("1900-02-29T00:00:00Z", "FAIL"),
            ("2025-02-29T00:00:00Z", "FAIL"),
            ("2026-04-31T00:00:00Z", "FAIL"),
            ("2026-01-00T00:00:00Z", "FAIL"),
            ("2026-00-01T00:00:00Z", "FAIL"),
            ("2026-13-01T00:00:00Z", "FAIL"),
            ("2026-10-24T24:00:00Z", "FAIL"),
            ("2026-10-24T00:60:00Z", "FAIL"),
            ("2026-10-24T00:00:60Z", "FAIL"),
            ("2026-10-24T00:00:00.0Z", "PASS"),
            ("2026-10-24T00:00:00.Z", "FAIL"),
            ("2026-10-24T00:00:00.123456789Z", "PASS"),
            ("2026-10-24T00:00:00.1234567890Z", "FAIL"),
            ("2026-10-24T00:00:00+18:00", "PASS"),
            ("2026-10-24T00:00:00-18:00", "PASS"),
            ("2026-10-24T00:00:00+18:01", "FAIL"),
            ("2026-10-24T00:00:00+17:60", "FAIL"),
            ("2026-10-24T00:00:00+19:00", "FAIL"),
            ("2026-10-24T00:00:00+17:59", "PASS"),
            ("9999-12-31T23:59:59.999999999Z", "PASS"),
            ("0000-12-31T23:59:59Z", "FAIL"),
        ]
        p = self.run_rows([f"{v}\t{expected}" for v, expected in rows])
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn(f"PASS {len(rows)}/{len(rows)}", p.stdout)

    def test_unicode_digits_and_non_ascii_separators_rejected(self):
        rows = [
            "٢٠٢٦-١٠-٢٤T00:00:00Z\tFAIL",
            "2026-10-24T０0:00:00Z\tFAIL",
            "2026-10-24t00:00:00Z\tFAIL",
            "2026-10-24T00:00:00z\tFAIL",
            "2026-10-24 00:00:00Z\tFAIL",
            "2026-10-24T00:00:00+09:00Z\tFAIL",
            "2026-10-24T00:00:00+09:00anything\tFAIL",
            "2026-10-24T00:00:00+09:00\tPASS",
        ]
        p = self.run_rows(rows)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn("PASS 8/8", p.stdout)

    def test_wrong_expected_result_fails_closed(self):
        p = self.run_rows(["2026-10-24T00:00:00Z\tFAIL"])
        self.assertEqual(1, p.returncode)
        self.assertIn("oracle mismatch", p.stderr)

    def test_bad_fixture_header_and_empty_fixture_rejected(self):
        for header, rows in (("bad\theader", ["2026-10-24T00:00:00Z\tPASS"]),
                             ("value\texpected", [])):
            p = self.run_rows(rows, header)
            self.assertNotEqual(0, p.returncode)

    def test_malformed_or_oversized_tsv_rejected(self):
        for rows in (["2026-10-24T00:00:00Z\tPASS\textra"],
                     ["2026-10-24T00:00:00Z\tMAYBE"],
                     ["x" * 550 + "\tFAIL"]):
            p = self.run_rows(rows)
            self.assertNotEqual(0, p.returncode)

    def test_nonexistent_fixture_rejected(self):
        p = subprocess.run([str(self.binary), str(Path(self.tmp.name) / "missing.tsv")],
                           capture_output=True, text=True, timeout=10, check=False)
        self.assertNotEqual(0, p.returncode)
        self.assertNotIn("PASS", p.stdout)

    def test_no_external_runtime_dependencies(self):
        source = (ROOT / "utc_strict_oracle.c").read_text(encoding="utf-8")
        for banned in ("system(", "popen(", "fork(", "curl", "wget", "<windows.h>"):
            self.assertNotIn(banned, source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)


if __name__ == "__main__":
    unittest.main()
