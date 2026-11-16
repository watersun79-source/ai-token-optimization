"""No SDK installation, GitHub writes, network access, or mutation of originals."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'experiments' / 'oss-top10-safe-adoption' / 'native_run_cooldown_guard.py'
spec = importlib.util.spec_from_file_location('native_run_cooldown_guard', SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SAMPLE = json.loads((ROOT / 'sample' / 'native_cooldown_sample.json').read_text(encoding='utf-8'))


class NativeIntegrityTests(unittest.TestCase):
    def check(self, mut=None):
        case = copy.deepcopy(SAMPLE)
        if mut:
            mut(case)
        return guard.audit(case)

    def test_normal_kst_ids_and_negative_offset(self):
        out = self.check()['native']
        self.assertEqual(out['status'], 'PASS')
        self.assertEqual(out['start_offset_seconds'], -11.11)
        self.assertTrue(out['id_equal'])

    def test_wrong_result_id(self):
        out = self.check(lambda d: d['latest_result'].update(run_id='other'))
        self.assertIn('RUN_RESULT_ID_MISMATCH', out['native']['finding_codes'])
        self.assertEqual(out['native']['status'], 'FAIL')

    def test_missing_id_fail_closed(self):
        self.assertEqual(self.check(lambda d:d['last_run'].pop('id'))['native']['status'], 'FAIL')

    def test_different_scheduled_for(self):
        out = self.check(lambda d:d['latest_result'].update(scheduled_for='2026-11-15T03:00:00Z'))
        self.assertIn('SCHEDULED_FOR_MISMATCH', out['native']['finding_codes'])

    def test_equivalent_iso_offset_accepted(self):
        out = self.check(lambda d:d['latest_result'].update(scheduled_for='2026-11-15T11:00:00+09:00'))
        self.assertEqual(out['native']['status'], 'PASS')

    def test_result_after_completed_rejected(self):
        out=self.check(lambda d:d['latest_result'].update(created_at='2026-11-15T03:00:00Z'))
        self.assertEqual(out['native']['status'], 'FAIL')

    def test_result_before_started_rejected(self):
        out=self.check(lambda d:d['latest_result'].update(created_at='2026-11-15T00:00:00Z'))
        self.assertEqual(out['native']['status'], 'FAIL')

    def test_naive_timestamp_unverified(self):
        out=self.check(lambda d:d['last_run'].update(scheduled_for='2026-11-15T02:00:00'))
        self.assertEqual(out['native']['status'], 'UNVERIFIED')

    def test_missing_result_unverified(self):
        self.assertEqual(guard.check_native(SAMPLE['last_run'], {})['status'], 'UNVERIFIED')

    def test_report_title_wrong_hour(self):
        out=self.check(lambda d:d['latest_result'].update(content_text='진화하는 AI · 2026년 11월 15일 오전 10시'))
        self.assertIn('KST_TITLE_MISMATCH',out['native']['finding_codes'])

    def test_report_title_missing_unverified(self):
        out=self.check(lambda d:d['latest_result'].update(content_text='NO_UPDATE'))
        self.assertEqual(out['native']['status'], 'UNVERIFIED')

    def test_title_mentioned_below_not_proof(self):
        out=self.check(lambda d:d['latest_result'].update(content_text='NO_UPDATE\n2026년 11월 15일 오전 11시'))
        self.assertEqual(out['native']['status'], 'UNVERIFIED')

    def test_title_mentioned_inline_is_not_heading(self):
        out = self.check(lambda d: d['latest_result'].update(
            content_text='NO_UPDATE. Not a verified heading: 2026년 11월 15일 오전 11시'))
        self.assertEqual(out['native']['status'], 'UNVERIFIED')
        self.assertIsNone(out['native']['title_equal'])

    def test_in_progress_not_completed(self):
        out=self.check(lambda d:d['last_run'].update(recorded_status='in_progress'))
        self.assertEqual(out['native']['status'], 'UNVERIFIED')

    def test_noon_am_pm(self):
        d=copy.deepcopy(SAMPLE)
        d['last_run']['scheduled_for']='2026-11-15T03:00:00Z'
        d['latest_result']['scheduled_for']='2026-11-15T03:00:00Z'
        d['latest_result']['content_text']='2026년 11월 15일 오후 12시'
        self.assertTrue(guard.audit(d)['native']['title_equal'])

    def test_midnight_am_pm(self):
        d=copy.deepcopy(SAMPLE)
        d['last_run']['scheduled_for']='2026-11-15T15:00:00Z'
        d['latest_result']['scheduled_for']='2026-11-15T15:00:00Z'
        d['latest_result']['content_text']='2026년 11월 16일 오전 12시'
        self.assertTrue(guard.audit(d)['native']['title_equal'])

    def test_title_explicit_wrong_minute(self):
        out=self.check(lambda d:d['latest_result'].update(content_text='2026년 11월 15일 오전 11시 1분'))
        self.assertEqual(out['native']['status'], 'FAIL')


class CooldownTests(unittest.TestCase):
    def test_cooldown_receipt_pass_is_blocked(self):
        out=guard.audit(SAMPLE)
        self.assertEqual(out['cycle']['status'], 'BLOCKED')
        self.assertTrue(out['cycle']['receipt_pass'])
        self.assertFalse(out['cycle']['allow_write'])
        self.assertFalse(out['cycle']['allow_retry'])

    def test_no_cooldown_automatic_retry(self):
        d=copy.deepcopy(SAMPLE)
        d['evolution_cycle'].update(status='PASS', debug={'status':'PASS','reason':'NO_CHANGE'})
        self.assertFalse(guard.audit(d)['cycle']['allow_retry'])

    def test_403_denied_even_if_claimed_pass(self):
        d=copy.deepcopy(SAMPLE)
        d['evolution_cycle'].update(status='PASS',debug={'reason':'HTTP_403','status':'PASS'})
        self.assertEqual(guard.audit(d)['cycle']['status'], 'BLOCKED')

    def test_unverified_when_only_server_receipt(self):
        d=copy.deepcopy(SAMPLE)
        d['evolution_cycle'].update(status='PASS', debug={'reason':'NO_CHANGE'})
        self.assertEqual(guard.audit(d)['cycle']['status'], 'UNVERIFIED')

    def test_no_update_does_not_write(self):
        d=copy.deepcopy(SAMPLE)
        d['evolution_cycle'].update(status='NO_UPDATE',debug={'status':'PASS','reason':'SAME_HEAD'})
        out=guard.audit(d)
        self.assertEqual(out['cycle']['status'], 'NO_UPDATE')
        self.assertEqual(out['external_mutations'],0)
        self.assertFalse(out['cycle']['allow_write'])

    def test_missing_cycle_unverified(self):
        self.assertEqual(guard.check_cycle(None)['status'],'UNVERIFIED')
        self.assertFalse(guard.check_cycle(None)['allow_retry'])

    def test_upstream_backoff_blocks(self):
        d=copy.deepcopy(SAMPLE)
        d['evolution_cycle'].update(status='BLOCKED',debug={'reason':'UPSTREAM_BACKOFF'})
        self.assertEqual(guard.audit(d)['cycle']['status'],'BLOCKED')

    def test_native_failure_is_not_masked_by_no_update(self):
        d=copy.deepcopy(SAMPLE)
        d['latest_result']['run_id']='different'
        d['evolution_cycle'].update(status='NO_UPDATE', debug={'reason':'SAME_HEAD'})
        self.assertEqual(guard.audit(d)['overall'],'FAIL')

    def test_native_id_failure_not_hidden_by_cooldown(self):
        d = copy.deepcopy(SAMPLE)
        d['latest_result']['run_id'] = 'wrong-id'
        out = guard.audit(d)
        self.assertEqual(out['native']['status'], 'FAIL')
        self.assertEqual(out['cycle']['status'], 'BLOCKED')
        self.assertEqual(out['overall'], 'FAIL')
        self.assertFalse(out['cycle']['allow_retry'])
        self.assertFalse(out['cycle']['allow_write'])

    def test_explicit_no_side_effects(self):
        before=copy.deepcopy(SAMPLE)
        self.assertEqual(guard.audit(SAMPLE)['external_mutations'],0)
        self.assertEqual(SAMPLE,before)



class SiteGithub403NewRegressionTests(unittest.TestCase):
    """Novel fail-closed Site 403 cases. No Site or GitHub calls."""

    def case(self, status, reason):
        result = guard.check_cycle({
            'status': status,
            'debug': {'status': 'PASS', 'reason': reason},
            'mcp_receipt': {'status': 'PASS'},
        })
        self.assertFalse(result['allow_retry'])
        self.assertFalse(result['allow_write'])
        return result

    def test_site_github_403_claimed_pass_is_blocked(self):
        self.assertEqual(self.case('PASS', 'GITHUB_HTTP_403')['status'], 'BLOCKED')

    def test_site_github_403_claimed_no_update_is_blocked(self):
        self.assertEqual(self.case('NO_UPDATE', 'GITHUB_HTTP_403')['status'], 'BLOCKED')

    def test_site_github_403_receipt_does_not_override_block(self):
        outcome = self.case('PASS', 'GITHUB_HTTP_403')
        self.assertTrue(outcome['receipt_pass'])
        self.assertEqual(outcome['status'], 'BLOCKED')

    def test_legacy_http_403_still_blocked(self):
        self.assertEqual(self.case('PASS', 'HTTP_403')['status'], 'BLOCKED')

    def test_same_head_no_update_stays_no_update(self):
        self.assertEqual(self.case('NO_UPDATE', 'SAME_HEAD')['status'], 'NO_UPDATE')

    def test_missing_cycle_never_permits_writes_or_retry(self):
        result = guard.check_cycle(None)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertFalse(result['allow_retry'])
        self.assertFalse(result['allow_write'])



def _site403_native_v2():
    return {
        'last_run': {'id': 'run-a', 'recorded_status': 'completed',
                     'scheduled_for': '2026-11-17T00:00:00Z',
                     'started_at': '2026-11-17T00:00:01Z',
                     'completed_at': '2026-11-17T00:00:04Z'},
        'latest_result': {'run_id': 'run-a', 'scheduled_for': '2026-11-17T00:00:00Z',
                          'created_at': '2026-11-17T00:00:03Z',
                          'content_text': '진화하는 AI · 2026년 11월 17일 오전 9시'},
    }


class SiteGithub403AdditionalRegressions(unittest.TestCase):
    """Only new PR #31 Site 403 fail-closed cases; no external calls."""

    def check(self, status='PASS', reason='GITHUB_HTTP_403'):
        cycle = {'status': status, 'debug': {'reason': reason},
                 'mcp_receipt': {'status': 'PASS'}}
        before = copy.deepcopy(cycle)
        verdict = guard.check_cycle(cycle)
        self.assertEqual(cycle, before)
        self.assertFalse(verdict['allow_retry'])
        self.assertFalse(verdict['allow_write'])
        return verdict

    def test_leading_trailing_whitespace_403(self):
        self.assertEqual(self.check(reason='  GITHUB_HTTP_403  ')['status'], 'BLOCKED')

    def test_colon_detail_403(self):
        self.assertEqual(self.check(reason='GITHUB_HTTP_403: denied by upstream')['status'], 'BLOCKED')

    def test_colon_detail_overrides_no_update(self):
        self.assertEqual(self.check(status='NO_UPDATE', reason='GITHUB_HTTP_403: forbidden')['status'], 'BLOCKED')

    def test_padded_colon_403(self):
        self.assertEqual(self.check(reason=' GITHUB_HTTP_403 : denied ')['status'], 'BLOCKED')

    def test_missing_reason_no_update_unverified(self):
        out = guard.check_cycle({'status': 'NO_UPDATE', 'debug': {}, 'mcp_receipt': {'status': 'PASS'}})
        self.assertEqual(out['status'], 'UNVERIFIED')
        self.assertFalse(out['allow_write'])
        self.assertFalse(out['allow_retry'])

    def test_blank_reason_no_update_unverified(self):
        self.assertEqual(self.check(status='NO_UPDATE', reason='  ')['status'], 'UNVERIFIED')

    def test_none_reason_no_update_unverified(self):
        self.assertEqual(self.check(status='NO_UPDATE', reason=None)['status'], 'UNVERIFIED')

    def test_nonstring_reason_no_update_unverified(self):
        self.assertEqual(self.check(status='NO_UPDATE', reason={'detail': 'GITHUB_HTTP_403'})['status'], 'UNVERIFIED')

    def test_similar_prefix_not_false_positive(self):
        self.assertEqual(self.check(reason='GITHUB_HTTP_403X: denied')['status'], 'UNVERIFIED')

    def test_embedded_reason_not_false_positive(self):
        self.assertEqual(self.check(reason='NOT_GITHUB_HTTP_403: denied')['status'], 'UNVERIFIED')

    def test_verified_same_head_preserves_no_update(self):
        self.assertEqual(self.check(status='NO_UPDATE', reason='SAME_HEAD')['status'], 'NO_UPDATE')

    def test_audit_overall_blocked_for_detailed_403(self):
        data = _site403_native_v2()
        data['evolution_cycle'] = {'status': 'NO_UPDATE', 'debug': {'reason': ' GITHUB_HTTP_403: forbidden'}}
        out = guard.audit(data)
        self.assertEqual(out['native']['status'], 'PASS')
        self.assertEqual(out['cycle']['status'], 'BLOCKED')
        self.assertEqual(out['overall'], 'BLOCKED')
        self.assertEqual(out['external_mutations'], 0)

    def test_audit_overall_unverified_for_missing_reason(self):
        data = _site403_native_v2()
        data['evolution_cycle'] = {'status': 'NO_UPDATE', 'debug': {}}
        out = guard.audit(data)
        self.assertEqual(out['native']['status'], 'PASS')
        self.assertEqual(out['cycle']['status'], 'UNVERIFIED')
        self.assertEqual(out['overall'], 'UNVERIFIED')
        self.assertEqual(out['external_mutations'], 0)


if __name__ == '__main__':
    unittest.main()
