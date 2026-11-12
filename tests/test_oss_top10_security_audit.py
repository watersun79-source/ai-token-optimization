"""Static and offline fail-closed tests for official advisory CI."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/".github/security/oss_top10_audit.py"
WF=ROOT/".github/workflows/oss-top10-dependency-audit.yml"
spec=importlib.util.spec_from_file_location("oss_audit", SRC)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wf=WF.read_text(encoding="utf-8")
    def test_public_advisory_sources(self):
        self.assertIn("pip_audit --no-deps --disable-pip",self.wf)
        self.assertIn("npm audit --json --package-lock-only",self.wf)
    def test_readonly_no_secrets_no_schedule(self):
        self.assertIn("contents: read",self.wf)
        self.assertIn("persist-credentials: false",self.wf)
        for x in ("pull_request_target:","workflow_dispatch:","schedule:","secrets."):
            self.assertNotIn(x,self.wf)
    def test_nine_matrix_items(self):
        self.assertEqual(self.wf.count("          - { id: "),9)
    def test_unverified_not_pass(self):
        src=SRC.read_text(encoding="utf-8")
        self.assertIn("if a.exit_code not in (0, 1):",src)
        self.assertIn("official advisory coverage incomplete",src)
        self.assertIn("METADATA_ONLY_NOT_LEGAL_APPROVAL",src)
    def test_no_lock_rewriting(self):
        self.assertNotIn("npm audit fix",self.wf)
        self.assertNotIn("pip-audit --fix",self.wf)
        self.assertIn("npm ci --ignore-scripts",self.wf)
    def test_flowise_excluded(self):
        self.assertNotIn("- { id: flowise",self.wf)
    def test_license_classifier(self):
        self.assertEqual(audit.classification(["MIT"]),"DECLARED")
        self.assertEqual(audit.classification(["GPL-3.0"]),"REVIEW")
        self.assertEqual(audit.classification([]),"UNVERIFIED")
    def test_strict_pin_validation(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            p=Path(d)/"lock.txt"
            p.write_text("unsafe>=1.0\n")
            with self.assertRaises(ValueError):
                audit.analyze_python(p,{"dependencies":[]})

if __name__=="__main__":
    unittest.main()
