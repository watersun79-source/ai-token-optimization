"""Reject Python-normalized timestamps before accepting evidence structure."""
import copy
import unittest

from audit_v2 import check, parsed_time, parsed_time_ns
from test_audit_v2 import BASE, CALLS, RUN


class StrictOffsetMinutesTests(unittest.TestCase):
    def make(self):
        return {**copy.deepcopy(BASE), 'native_run': copy.deepcopy(RUN),
                'tool_calls': copy.deepcopy(CALLS)}

    def test_offset_minute_overflow_cannot_satisfy_run_window(self):
        # +08:60 and -00:60 normalize to real instants in Python but are
        # malformed under the project's strict timestamp contract.
        for bad in ('2026-10-22T22:01:47+08:60',
                    '2026-10-22T12:01:47-00:60'):
            with self.subTest(value=bad):
                p = self.make()
                p['native_run']['started_at'] = bad
                result = check(p)
                self.assertEqual('미검증', result['status'])
                self.assertEqual([], result['verified_targets'])
                self.assertFalse(result['official_success_verified'])

    def test_overflow_tool_offset_does_not_satisfy_required_target(self):
        p = self.make()
        p['tool_calls'][0]['observed_at'] = '2026-10-22T22:02:00+08:60'
        result = check(p)
        self.assertIn('current_handoff', result['missing'])
        self.assertEqual(['slack_thread'], result['verified_targets'])

    def test_timestamp_metadata_requires_exact_supported_syntax(self):
        for bad in ('2026-10-22 13:01:47Z', '2026-10-22t13:01:47Z',
                    '2026-10-22T13:01:47.1234567890Z',
                    '2026-10-22T22:01:47+08:60'):
            with self.subTest(value=bad):
                self.assertIsNone(parsed_time(bad))
                p = copy.deepcopy(BASE)
                p['schedule']['last_run_time'] = bad
                self.assertIn('회차 실행 여부 확인 불가', check(p)['trigger'])

    def test_valid_offset_and_nano_boundary_preserved(self):
        same = parsed_time_ns('2026-10-22T22:01:47.123456789+09:00')
        self.assertEqual(parsed_time_ns('2026-10-22T13:01:47.123456789Z'), same)
        self.assertEqual(789, same[1])
        for suffix in ('+18:00', '-18:00', '+17:59', '-00:59'):
            self.assertIsNotNone(parsed_time('2026-10-22T22:01:47' + suffix))
        self.assertTrue(check(self.make())['status'].startswith('형식 통과'))


if __name__ == '__main__':
    unittest.main()
