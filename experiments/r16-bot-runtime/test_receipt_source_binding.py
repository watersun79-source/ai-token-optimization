"""Real filesystem changes must invalidate an earlier local test receipt."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import runner


class ReceiptSourceBindingTests(unittest.TestCase):
    def test_each_execution_input_change_invalidates_receipt(self):
        for name in ('runner.py', 'catalog.json', 'utc_strict_oracle_cases.tsv',
                     'measure_runtime.py'):
            with self.subTest(changed=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for source in runner.ROOT.iterdir():
                    if source.is_file():
                        shutil.copyfile(source, root / source.name)
                file = root / name
                file.write_bytes(file.read_bytes() + b'\n')
                with patch.object(runner, 'ROOT', root):
                    receipt, reason = runner.read_runtime_receipt()
                self.assertIsNone(receipt, name + ': stale receipt accepted')

    def test_changed_evidence_input_invalidates_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for source in runner.ROOT.iterdir():
                if source.is_file():
                    shutil.copyfile(source, root / source.name)
            p = root / 'evidence.json'
            evidence = json.loads(p.read_text())
            evidence['schedule']['enabled'] = False
            p.write_text(json.dumps(evidence))
            with patch.object(runner, 'ROOT', root):
                self.assertIsNone(runner.read_runtime_receipt()[0])

    def test_legacy_receipt_cannot_claim_complete_source_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for source in runner.ROOT.iterdir():
                if source.is_file():
                    shutil.copyfile(source, root / source.name)
            p = root / 'runtime_proof.json'
            receipt = json.loads(p.read_text())
            receipt['format'] = 'LOCAL_TEST_RECEIPT_V5'
            p.write_text(json.dumps(receipt))
            with patch.object(runner, 'ROOT', root):
                self.assertIsNone(runner.read_runtime_receipt()[0])


if __name__ == '__main__':
    unittest.main()
