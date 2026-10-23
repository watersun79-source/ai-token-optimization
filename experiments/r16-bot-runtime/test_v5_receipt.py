"""New targeted tests for version-accurate offline regression proof."""
import copy,json,unittest
from pathlib import Path
from runner import ROOT,validate,read_runtime_receipt
CAT={x['id']:x for x in json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))}
EVIDENCE=json.loads((ROOT/'evidence.json').read_text(encoding='utf8'))

class V5ReceiptTests(unittest.TestCase):
    def test_runtime_counts_measured(self):
        receipt,reason=read_runtime_receipt()
        self.assertIsNotNone(receipt,reason)
        for key in ('M01','M02','M03','M04'):
            with self.subTest(key=key):
                self.assertEqual('PASS',validate(CAT[key],EVIDENCE)['status'])

    def test_stale_regression_count_is_caught(self):
        modified=copy.deepcopy(EVIDENCE)
        modified['polyglot'].update(python_passed=21,java_passed=21,js_passed=21,total_passed=63)
        for key in ('M01','M02','M03','M04'):
            with self.subTest(key=key):
                self.assertEqual('FAIL',validate(CAT[key],modified)['status'])

    def test_source_edit_is_not_accepted(self):
        import unittest.mock as mock
        with mock.patch('runner.ROOT',Path('/nonexistent-r16-receipt')):
            self.assertEqual('UNVERIFIED',validate(CAT['M01'],EVIDENCE)['status'])

    def test_wrong_or_missing_proof_cannot_pass(self):
        import tempfile,unittest.mock as mock
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            (directory/'runtime_proof.json').write_text('[]',encoding='utf8')
            with mock.patch('runner.ROOT',directory):
                self.assertEqual('UNVERIFIED',validate(CAT['M01'],EVIDENCE)['status'])

    def test_receipt_is_not_official_scheduler_proof(self):
        self.assertEqual('UNVERIFIED',validate(CAT['E10'],EVIDENCE)['status'])
        self.assertEqual('UNVERIFIED',validate(CAT['L06'],EVIDENCE)['status'])

if __name__=='__main__':unittest.main()
