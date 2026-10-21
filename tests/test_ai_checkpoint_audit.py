"""Offline checkpoint regression, no third-party packages or network access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'ai_checkpoint_audit.py'
_spec = importlib.util.spec_from_file_location('checkpoint_audit', SOURCE)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def record(slot='2026-10-22 01:00 Asia/Seoul', when='2026-10-21T16:01:36.792Z', rid='first'):
    return {'id': rid, 'cells': {
        'automationId': 'test-automation', 'scheduledSlotKst': slot,
        'observedAtUtc': when, 'officialRunId': 'unverified-self-claim',
        'githubIndexSha': 'a' * 40, 'githubProtocolSha': 'b' * 40,
        'githubReportSha': 'c' * 40,
        'slackParentTs': '1792416391.631669', 'slackLatestMessageTs': '1792593557.131679',
        'readResult': 'SUCCESS: all claimed sources', 'evidenceLevel': audit.SELF_REPORTED,
    }}


class CheckpointAuditTests(unittest.TestCase):
    def test_valid_time_remains_only_self_reported(self):
        result = audit.check({'records': [record()]})
        self.assertEqual(result['status'], 'CHECKPOINTS_CONSISTENT_NOT_INDEPENDENTLY_PROVEN')
        self.assertFalse(result['official_run_proven'])
        self.assertEqual(result['rows'][0]['observation_offset_seconds'], 96.792)

    def test_early_midnight_slot_rejected(self):
        v = record('2026-10-22 00:00 Asia/Seoul', '2026-10-21T14:58:21.033Z')
        result = audit.check({'records': [v]})
        self.assertEqual(result['rows'][0]['observation_offset_seconds'], -98.967)
        self.assertEqual(result['errors'][0]['issue'], 'observation_precedes_declared_slot')
        self.assertEqual(result['status'], 'CHECKPOINT_ANOMALY')

    def test_duplicate_slot_rejected(self):
        result = audit.check({'records': [record(), record(rid='duplicate')]})
        self.assertIn('duplicate_automation_slot', [e['issue'] for e in result['errors']])

    def test_outside_hour_rejected(self):
        r = record(when='2026-10-21T17:00:01Z')
        self.assertIn('observation_outside_declared_slot_hour', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_bad_and_naive_timestamps_fail_closed(self):
        for val in ('2026-10-21T16:01:36', 'unknown', ''):
            with self.subTest(value=val):
                r = record(when=val)
                self.assertIn('invalid_or_missing_utc_observation', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_unknown_slot_not_pass(self):
        r = record(slot='UNKNOWN')
        self.assertIn('invalid_or_unknown_slot', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_wrong_sha_cannot_pass(self):
        r = record()
        r['cells']['githubIndexSha'] = 'invalid'
        self.assertIn('githubIndexSha_invalid', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_missing_source_with_success_claim_rejected(self):
        r = record()
        r['cells']['slackLatestMessageTs'] = ''
        self.assertIn('claimed_success_missing_source_fingerprint', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_wrong_evidence_level_rejected(self):
        r = record()
        r['cells']['evidenceLevel'] = 'VERIFIED_PLATFORM'
        self.assertIn('unsupported_evidence_level', audit.check({'records':[r]})['rows'][0]['issues'])

    def test_empty_export_not_success(self):
        self.assertEqual(audit.check({'records': []})['status'], 'CHECKPOINT_ANOMALY')

    def test_cli_errors_exit_nonzero_and_preserves_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'check.json'
            path.write_text(json.dumps({'records':[record('2026-10-22 00:00 Asia/Seoul', '2026-10-21T14:58:21.033Z')]}))
            p = subprocess.run([sys.executable, str(SOURCE), str(path)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)['status'], 'CHECKPOINT_ANOMALY')

    def test_cli_valid_exits_zero_without_claiming_official_proof(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'check.json'
            path.write_text(json.dumps({'records':[record()]}))
            p = subprocess.run([sys.executable, str(SOURCE), str(path)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)
            self.assertFalse(json.loads(p.stdout)['official_run_proven'])


if __name__ == '__main__':
    unittest.main()
