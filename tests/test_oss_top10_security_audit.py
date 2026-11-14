"""Static and offline fail-closed tests for official advisory CI."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
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
        with TemporaryDirectory() as d:
            p=Path(d)/"lock.txt"
            p.write_text("unsafe>=1.0\n")
            with self.assertRaises(ValueError):
                audit.analyze_python(p,{"dependencies":[]})

    def test_verified_advisory_gate_precedes_each_install(self):
        for job, install in (("python-security", 'pip install --index-url https://pypi.org/simple --only-binary=:all: --no-deps'),
                             ("npm-security", "npm ci --ignore-scripts")):
            with self.subTest(job=job):
                section = self.wf.split(f"  {job}:", 1)[1].split("  npm-security:", 1)[0]
                self.assertLess(section.index("--advisory-only"), section.index(install))

    def test_advisory_gate_exits_before_license_collection(self):
        cases = (
            ("python", 0, {"dependencies": [{"name": "sample-sdk", "version": "1", "vulns": []}]}, 0),
            ("python", 0, {"dependencies": []}, 2),
            ("python", 0, {"dependencies": [{"name": "sample-sdk", "version": "1"}]}, 2),
            ("python", 1, {"dependencies": [{"name": "sample-sdk", "version": "1", "vulns": [{"id": "PYSEC-TEST"}]}]}, 1),
            ("npm", 0, {"vulnerabilities": {}}, 2),
            ("npm", 0, {"vulnerabilities": {}, "metadata": {"vulnerabilities": {"total": 0},
                                                          "dependencies": {"total": 0}}}, 2),
            ("npm", 0, {"vulnerabilities": {}, "metadata": {"vulnerabilities": {"total": 0},
                                                          "dependencies": {"total": 1}}}, 0),
            ("npm", 1, {"vulnerabilities": {"sample-sdk": {"severity": "high", "nodes": ["node_modules/sample-sdk"]}},
                        "metadata": {"vulnerabilities": {"total": 1}, "dependencies": {"total": 1}}}, 1),
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock"
            report = root / "report.json"
            for kind, audit_code, payload, expected_code in cases:
                with self.subTest(kind=kind, payload=payload):
                    document = json.dumps({"packages": {"": {}, "node_modules/sample-sdk": {"version": "1"}}})
                    lock.write_text("sample-sdk==1\n" if kind == "python" else document, encoding="utf-8")
                    report.write_text(json.dumps(payload), encoding="utf-8")
                    run = subprocess.run([sys.executable, str(SRC), "--kind", kind, "--lock", str(lock),
                                          "--audit", str(report), "--exit-code", str(audit_code),
                                          "--advisory-only"], cwd=root, capture_output=True, text=True, check=False)
                    self.assertEqual(run.returncode, expected_code, run.stderr or run.stdout)
                    if expected_code != 2:
                        receipt = json.loads(run.stdout.split("=", 1)[1])
                        self.assertEqual(receipt["license_scope"], "NOT_COLLECTED")
                        self.assertNotIn("license_declared", receipt)

if __name__=="__main__":
    unittest.main()
