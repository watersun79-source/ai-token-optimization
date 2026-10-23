"""Fail-closed tests for installed offline BOT wrapper integrity."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
FILES = ("batch_validate_100.py", "install_local.py", "runner.py",
         "catalog.json", "evidence.json", "runtime_proof.json",
         "test_runtime.py", "UtcStrictOracle.java", "utc_strict_oracle.js",
         "measure_runtime.py", "utc_strict_oracle_cases.tsv")


class WrapperIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in FILES:
            shutil.copyfile(ROOT / name, self.root / name)
        result = subprocess.run([sys.executable, "install_local.py"], cwd=self.root,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_check(self):
        return subprocess.run([sys.executable, "batch_validate_100.py"], cwd=self.root,
                              capture_output=True, text=True, timeout=20)

    def test_normal_wrappers_pass(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"executed_rule_checks": 100', result.stdout)

    def test_modified_wrapper_fails(self):
        wrapper = self.root / ".local_install/bin/ai-bot-M01"
        wrapper.write_bytes(wrapper.read_bytes() + b"\n# modified\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLI wrapper content mismatch", result.stderr)

    def test_replaced_symlink_fails(self):
        wrapper = self.root / ".local_install/bin/ai-bot-M01"
        wrapper.unlink()
        wrapper.symlink_to("ai-bot-M02")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLI wrapper content mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
