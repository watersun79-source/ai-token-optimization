"""Shared conformance vectors for Python/JavaScript/Java timestamp evidence.

Design inspired by JSON Schema's multilingual conformance fixtures and Temporal's
per-run identity separation. No dependency, provider API, network, or real run ID.
"""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from audit_v2 import AUTOMATION_ID, check

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'time_cases.tsv'


class R16PolyglotTimestampFixtures(unittest.TestCase):
    def test_all_shared_vectors(self):
        with FIXTURES.open(encoding='utf-8', newline='') as f:
            cases = list(csv.DictReader(f, delimiter='\t'))
        self.assertGreaterEqual(len(cases), 12)
        for case in cases:
            with self.subTest(case=case['case']):
                sample_id = 'SYNTHETIC-CROSS-LANGUAGE-NOT-OFFICIAL'
                calls = [
                    dict(origin='official_task_tool_call', run_id=sample_id,
                         target='current_handoff', tool='mcp__GitHub__fetch_file',
                         locator='docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md',
                         version='a' * 40, success=True, observed_at=case['observed_at'],
                         invocation_id='SYNTHETIC-1'),
                    dict(origin='official_task_tool_call', run_id=sample_id,
                         target='slack_thread', tool='mcp__Slack__slack_read_thread',
                         locator='C0C9649RQAZ/1792416391.631669',
                         version='1792416391.631669', success=True,
                         observed_at=case['observed_at'], invocation_id='SYNTHETIC-2'),
                ]
                payload = {
                    'target_slot': case['scheduled_for'],
                    'schedule': {'id': AUTOMATION_ID, 'is_enabled': True,
                                 'last_run_time': '2026-10-23T02:06:18.531665Z'},
                    'native_run': {'origin': 'official_task_run_details',
                                   'automation_id': AUTOMATION_ID, 'run_id': sample_id,
                                   'scheduled_for': case['scheduled_for'],
                                   'started_at': case['started_at'],
                                   'completed_at': case['completed_at'], 'status': 'completed'},
                    'tool_calls': calls,
                }
                result = check(payload)
                actual = 'FORMAT' if result['status'].startswith('형식 통과') else 'REJECT'
                self.assertEqual(actual, case['expected'])
                self.assertIs(result['official_success_verified'], False)


if __name__ == '__main__':
    unittest.main()
