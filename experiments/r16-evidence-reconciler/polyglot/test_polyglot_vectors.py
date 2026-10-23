"""Compare R16's real Python evidence-format decision with language-neutral cases.

These are synthetic test inputs; they are never authenticated scheduler records.
"""
import csv
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_v2 import AUTOMATION_ID, REQUIRED, check

HERE = Path(__file__).resolve().parent
ROWS = [row for row in csv.reader((line for line in
        (HERE / 'time_vectors.tsv').read_text(encoding='utf-8').splitlines()
        if line and not line.startswith('#')), delimiter='|')]


class SharedTimeVectorTests(unittest.TestCase):
    def test_vector_table_not_empty(self):
        self.assertGreaterEqual(len(ROWS), 10)

    def test_all_time_boundaries_match(self):
        for name, slot, started, completed, observed, expected in ROWS:
            with self.subTest(case=name):
                run_id = 'SYNTHETIC-NOT-A-CHATGPT-RUN'
                payload = {
                    'target_slot': slot,
                    'schedule': {
                        'id': AUTOMATION_ID, 'is_enabled': True,
                        'last_run_time': '2026-10-23T01:00:35Z',
                    },
                    'native_run': {
                        'origin': 'official_task_run_details',
                        'run_id': run_id,
                        'automation_id': AUTOMATION_ID,
                        'scheduled_for': slot,
                        'started_at': started, 'completed_at': completed,
                        'status': 'completed',
                    },
                    'tool_calls': [
                        {'origin': 'official_task_tool_call',
                         'run_id': run_id, 'target': target,
                         'tool': tool, 'locator': locator,
                         'success': True, 'observed_at': observed,
                         'version': 'a' * 40 if kind == 'sha' else '1792416391.631669',
                         'invocation_id': 'SYNTHETIC-' + target}
                        for target, (tool, locator, kind) in REQUIRED.items()
                    ],
                }
                result = check(payload)
                self.assertEqual(
                    result['status'].startswith('형식 통과'), expected == 'PASS',
                    f'{name}: {result}',
                )
                self.assertFalse(result['official_success_verified'])


if __name__ == '__main__':
    unittest.main()
