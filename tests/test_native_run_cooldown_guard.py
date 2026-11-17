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
        cycle = {'status': status, 'debug': {'status': 'PASS', 'reason': reason},
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



class SiteGithub403StrictNoUpdateRegressions(unittest.TestCase):
    """New standalone fail-closed cases; no network, SDK or privileged operation."""

    def check(self, reason, expected, status='NO_UPDATE'):
        cycle = {'status': status, 'debug': {'status': 'PASS', 'reason': reason},
                 'mcp_receipt': {'status': 'PASS'}}
        before = copy.deepcopy(cycle)
        result = guard.check_cycle(cycle)
        self.assertEqual(result['status'], expected)
        self.assertFalse(result['allow_retry'])
        self.assertFalse(result['allow_write'])
        self.assertEqual(cycle, before)

    def test_space_separated_github_403(self):
        self.check('GITHUB_HTTP_403 denied', 'BLOCKED')

    def test_padded_space_separated_github_403(self):
        self.check(' GITHUB_HTTP_403   denied upstream', 'BLOCKED', 'PASS')

    def test_space_separated_legacy_403(self):
        self.check('HTTP_403 forbidden', 'BLOCKED')

    def test_space_separated_429(self):
        self.check('HTTP_429 wait', 'BLOCKED')

    def test_unrecognized_github_http_503(self):
        self.check('GITHUB_HTTP_503: upstream failure', 'BLOCKED')

    def test_unrecognized_http_502(self):
        self.check('HTTP_502 bad gateway', 'BLOCKED')

    def test_unrecognized_http_500(self):
        self.check('HTTP_500', 'BLOCKED', 'PASS')

    def test_unknown_error_is_not_no_update(self):
        self.check('NEW_UPSTREAM_ERROR', 'UNVERIFIED')

    def test_unknown_nonerror_is_not_no_update(self):
        self.check('RETRY_LATER', 'UNVERIFIED')

    def test_same_head_with_details_not_whitelisted(self):
        self.check('SAME_HEAD: not independently verified', 'UNVERIFIED')

    def test_exact_same_head_preserves_no_update(self):
        self.check('SAME_HEAD', 'NO_UPDATE')

    def test_whitespace_trimmed_same_head_preserves_no_update(self):
        self.check('  SAME_HEAD  ', 'NO_UPDATE')

    def test_spoofed_error_code_suffix_not_blocked_as_exact(self):
        self.check('GITHUB_HTTP_403X denied', 'UNVERIFIED')

    def test_embedded_error_code_not_blocked_as_exact(self):
        self.check('NOT_GITHUB_HTTP_403 denied', 'UNVERIFIED')

    def test_overall_propagates_space_403(self):
        payload = _site403_native_v2()
        payload['evolution_cycle'] = {'status':'NO_UPDATE','debug':{'reason':'GITHUB_HTTP_403 denied'}}
        out = guard.audit(payload)
        self.assertEqual(out['native']['status'], 'PASS')
        self.assertEqual(out['cycle']['status'], 'BLOCKED')
        self.assertEqual(out['overall'], 'BLOCKED')
        self.assertEqual(out['external_mutations'], 0)

    def test_overall_propagates_new_http_error(self):
        payload = _site403_native_v2()
        payload['evolution_cycle'] = {'status':'NO_UPDATE','debug':{'reason':'GITHUB_HTTP_503: fail'}}
        out = guard.audit(payload)
        self.assertEqual(out['native']['status'], 'PASS')
        self.assertEqual(out['cycle']['status'], 'BLOCKED')
        self.assertEqual(out['overall'], 'BLOCKED')

    def test_overall_unknown_reason_unverified(self):
        payload = _site403_native_v2()
        payload['evolution_cycle'] = {'status':'NO_UPDATE','debug':{'reason':'NEW_UPSTREAM_ERROR'}}
        out = guard.audit(payload)
        self.assertEqual(out['native']['status'], 'PASS')
        self.assertEqual(out['cycle']['status'], 'UNVERIFIED')
        self.assertEqual(out['overall'], 'UNVERIFIED')



def input_cycle():
    return {'status': 'NO_UPDATE', 'debug': {'status': 'PASS', 'reason': 'SAME_HEAD'},
            'fix': {'status': 'SKIP'}, 'update': {'status': 'SKIP'},
            'mcp_receipt': {'status': 'PASS'}}


def native_payload(cycle):
    return {'last_run': {'id': 'run-1', 'recorded_status': 'completed',
                         'scheduled_for': '2026-11-17T00:00:00Z',
                         'started_at': '2026-11-17T00:00:01Z',
                         'completed_at': '2026-11-17T00:00:05Z'},
            'latest_result': {'run_id':'run-1','scheduled_for':'2026-11-17T00:00:00Z',
                              'created_at':'2026-11-17T00:00:04Z',
                              'content_text':'진화하는 AI · 2026년 11월 17일 오전 9시'},
            'evolution_cycle':cycle}


class StageStatusV4(unittest.TestCase):
    """Fail-closed stage-status regressions; isolated, zero external calls."""

    def check(self, status, stage=None, value=None):
        c=input_cycle()
        if stage is not None: c[stage]={'status': value}
        if stage=='debug': c['debug']['reason']='SAME_HEAD'
        previous=copy.deepcopy(c)
        out=guard.check_cycle(c)
        self.assertEqual(previous,c)
        self.assertFalse(out['allow_retry']); self.assertFalse(out['allow_write'])
        self.assertEqual(out['status'],status)
        return out

    def test_debug_fail_blocks(self): self.check('BLOCKED','debug','FAIL')
    def test_fix_fail_blocks(self): self.check('BLOCKED','fix','FAIL')
    def test_update_fail_blocks(self): self.check('BLOCKED','update','FAIL')
    def test_debug_blocked_blocks(self): self.check('BLOCKED','debug','BLOCKED')
    def test_fix_blocked_blocks(self): self.check('BLOCKED','fix','BLOCKED')
    def test_update_blocked_blocks(self): self.check('BLOCKED','update','BLOCKED')
    def test_debug_unverified_blocks_no_update(self): self.check('UNVERIFIED','debug','UNVERIFIED')
    def test_fix_unverified_blocks_no_update(self): self.check('UNVERIFIED','fix','UNVERIFIED')
    def test_update_unverified_blocks_no_update(self): self.check('UNVERIFIED','update','UNVERIFIED')
    def test_failure_takes_precedence_over_unverified(self):
        c=input_cycle();c['debug']['status']='UNVERIFIED';c['update']['status']='FAIL'
        self.assertEqual(guard.check_cycle(c)['status'],'BLOCKED')
    def test_inprogress_is_not_no_update(self): self.check('UNVERIFIED','fix','IN_PROGRESS')
    def test_none_status_is_not_no_update(self): self.check('UNVERIFIED','fix',None)
    def test_invalid_stage_is_unverified(self):
        c=input_cycle();c['fix']='FAIL'
        self.assertEqual(guard.check_cycle(c)['status'],'UNVERIFIED')
    def test_same_head_pass_and_skip_preserved(self): self.check('NO_UPDATE')
    def test_same_head_all_pass_preserved(self):
        c=input_cycle();c['fix']['status']='PASS';c['update']['status']='PASS'
        self.assertEqual(guard.check_cycle(c)['status'],'NO_UPDATE')
    def test_same_head_optional_stages_absent_preserved(self):
        c={'status':'NO_UPDATE','debug': {'status':'PASS', 'reason':'SAME_HEAD'}}
        self.assertEqual(guard.check_cycle(c)['status'],'NO_UPDATE')
    def test_same_head_explicit_no_update_stage_preserved(self): self.check('NO_UPDATE','fix','NO_UPDATE')
    def test_audit_overall_fail_stage_blocked(self):
        c=input_cycle();c['fix']['status']='FAIL';v=guard.audit(native_payload(c))
        self.assertEqual(v['native']['status'],'PASS')
        self.assertEqual(v['cycle']['status'],'BLOCKED')
        self.assertEqual(v['overall'],'BLOCKED');self.assertEqual(v['external_mutations'],0)
    def test_audit_overall_unverified_stage(self):
        c=input_cycle();c['update']['status']='UNVERIFIED';v=guard.audit(native_payload(c))
        self.assertEqual(v['native']['status'],'PASS')
        self.assertEqual(v['cycle']['status'],'UNVERIFIED')
        self.assertEqual(v['overall'],'UNVERIFIED');self.assertEqual(v['external_mutations'],0)



def safe_cycle():
    return {'status':'NO_UPDATE',
            'debug':{'status':'PASS','reason':'SAME_HEAD'},
            'fix':{'status':'SKIP'},
            'update':{'status':'SKIP'},
            'mcp_receipt':{'status':'PASS'}}


class MissingStageStatusV5(unittest.TestCase):
    """New standalone status-field omission regressions."""

    def expect(self, expected, transform):
        cycle=safe_cycle()
        transform(cycle)
        unchanged=copy.deepcopy(cycle)
        result=guard.check_cycle(cycle)
        self.assertEqual(expected,result['status'])
        self.assertEqual(unchanged,cycle)
        self.assertFalse(result['allow_retry'])
        self.assertFalse(result['allow_write'])
        return result

    def test_missing_debug_status(self):
        self.expect('UNVERIFIED',lambda c:c['debug'].pop('status'))

    def test_missing_fix_status(self):
        self.expect('UNVERIFIED',lambda c:c['fix'].pop('status'))

    def test_missing_update_status(self):
        self.expect('UNVERIFIED',lambda c:c['update'].pop('status'))

    def test_all_present_but_empty_status(self):
        self.expect('UNVERIFIED',lambda c:(c['debug'].pop('status'), c['fix'].pop('status'), c['update'].pop('status')))

    def test_empty_fix_object_is_not_absence(self):
        self.expect('UNVERIFIED',lambda c:c.update(fix={}))

    def test_empty_update_object_is_not_absence(self):
        self.expect('UNVERIFIED',lambda c:c.update(update={}))

    def test_debug_reason_only_not_enough(self):
        self.expect('UNVERIFIED',lambda c:c.update(debug={'reason':'SAME_HEAD'}))

    def test_failure_overrides_missing_stage(self):
        self.expect('BLOCKED',lambda c:(c.update(fix={}), c['update'].update(status='FAIL')))

    def test_blocked_overrides_missing_stage(self):
        self.expect('BLOCKED',lambda c:(c.update(update={}), c['fix'].update(status='BLOCKED')))

    def test_valid_optional_stages_absent(self):
        self.expect('NO_UPDATE',lambda c:(c.pop('fix'),c.pop('update')))

    def test_all_valid_stages_still_no_update(self):
        self.expect('NO_UPDATE',lambda c:None)

    def test_explicit_nonvalidated_status_stays_unverified(self):
        self.expect('UNVERIFIED',lambda c:c['fix'].update(status='IN_PROGRESS'))

    def test_audit_overall_missing_fix_unverified(self):
        c=safe_cycle(); c.update(fix={})
        out=guard.audit(native_payload(c))
        self.assertEqual(out['native']['status'],'PASS')
        self.assertEqual(out['cycle']['status'],'UNVERIFIED')
        self.assertEqual(out['overall'],'UNVERIFIED')
        self.assertEqual(out['external_mutations'],0)

    def test_audit_overall_missing_debug_unverified(self):
        c=safe_cycle(); c['debug'].pop('status')
        out=guard.audit(native_payload(c))
        self.assertEqual(out['native']['status'],'PASS')
        self.assertEqual(out['overall'],'UNVERIFIED')

    def test_audit_failure_priority_for_native_mismatch(self):
        c=safe_cycle(); c.update(fix={})
        data=native_payload(c);data['latest_result']['run_id']='wrong'
        self.assertEqual(guard.audit(data)['overall'],'FAIL')

    def test_existing_403_still_blocked_even_when_stage_missing(self):
        c=safe_cycle(); c.update(fix={}); c['debug']['reason']='GITHUB_HTTP_403'
        self.assertEqual(guard.check_cycle(c)['status'],'BLOCKED')



class SiteGithub403IntakeCLIRegressions(unittest.TestCase):
    """Real executable stdin/stdout boundary, no external Site or GitHub operations."""

    def _event(self, reason="GITHUB_HTTP_403", status="NO_UPDATE"):
        cycle={"status":status,"debug":{"status":"PASS","reason":reason},
               "fix":{"status":"SKIP"},"update":{"status":"SKIP"},
               "mcp_receipt":{"status":"PASS"}}
        return native_payload(cycle)

    def _invoke(self, payload, expected_exit=2, *, raw=False):
        import subprocess, sys
        script=ROOT / "experiments" / "oss-top10-safe-adoption" / "site_github403_intake.py"
        stdin=payload if raw else json.dumps(payload,ensure_ascii=False).encode("utf-8")
        proc=subprocess.run([sys.executable,"-B",str(script)],input=stdin,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
        self.assertEqual(proc.returncode,expected_exit,proc.stderr.decode("utf-8","replace"))
        self.assertEqual(proc.stderr,b"")
        result=json.loads(proc.stdout.decode("utf-8"))
        self.assertFalse(result["allow_retry"])
        self.assertFalse(result["allow_write"])
        self.assertEqual(result["external_requests"],0)
        self.assertEqual(result["external_mutations"],0)
        self.assertEqual(result["site_source_authentication"],"UNVERIFIED")
        self.assertEqual(result["site_runtime_integration"],"UNVERIFIED")
        self.assertEqual(result["operational_clearance"],"BLOCKED")
        return result,proc.stdout.decode("utf-8")

    def test_exec_403_blocks_claimed_no_update(self):
        result,_=self._invoke(self._event())
        self.assertEqual(result["classification"],"BLOCKED")

    def test_exec_403_blocks_claimed_pass(self):
        result,_=self._invoke(self._event(status="PASS"))
        self.assertEqual(result["classification"],"BLOCKED")

    def test_exec_normal_no_update_is_noop(self):
        result,_=self._invoke(self._event("SAME_HEAD"),0)
        self.assertEqual(result["classification"],"NO_UPDATE")

    def test_exec_missing_stage_status_unverified(self):
        data=self._event("SAME_HEAD");data["evolution_cycle"]["fix"]={}
        result,_=self._invoke(data)
        self.assertEqual(result["classification"],"UNVERIFIED")

    def test_exec_absent_optional_stage_preserved(self):
        data=self._event("SAME_HEAD");data["evolution_cycle"].pop("fix")
        data["evolution_cycle"].pop("update")
        result,_=self._invoke(data,0)
        self.assertEqual(result["classification"],"NO_UPDATE")

    def test_exec_unverified_when_native_missing(self):
        result,_=self._invoke({"evolution_cycle":self._event("SAME_HEAD")["evolution_cycle"]})
        self.assertEqual(result["classification"],"UNVERIFIED")

    def test_exec_native_mismatch_fails(self):
        data=self._event("SAME_HEAD");data["latest_result"]["run_id"]="wrong"
        result,_=self._invoke(data)
        self.assertEqual(result["classification"],"FAIL")

    def test_exec_bad_json_is_blocked_sanitized(self):
        result,printed=self._invoke(b'{"bad":oops sk-proj-hiddentoken123}',raw=True)
        self.assertEqual(result["reason_code"],"INPUT_INVALID")
        self.assertNotIn("hiddentoken",printed)

    def test_exec_duplicate_json_keys_denied(self):
        result,_=self._invoke(b'{"x":1,"x":2}',raw=True)
        self.assertEqual(result["reason_code"],"INPUT_INVALID")

    def test_exec_oversized_json_denied(self):
        result,_=self._invoke(b"x"*65537,raw=True)
        self.assertEqual(result["reason_code"],"INPUT_INVALID")

    def test_exec_secret_in_reason_not_echoed(self):
        data=self._event("GITHUB_HTTP_403: sk-proj-ultrasecret987654321")
        result,printed=self._invoke(data)
        self.assertEqual(result["classification"],"BLOCKED")
        self.assertNotIn("ultrasecret",printed)

    def test_exec_invalid_utf8_denied(self):
        result,_=self._invoke(b'\xff\xfe',raw=True)
        self.assertEqual(result["reason_code"],"INPUT_INVALID")



class SiteOfficialBridgeRegressions(unittest.TestCase):
    """New bridge CLI only; no official Site reader or remote operations."""

    def event(self):
        return {"schema": "SITE_GITHUB403_OBSERVATION_INPUT_V1",
                "project_id": "appgprj_6ae20fb4b2b08191b0f4b44438fc0237",
                "collector": {"http_status": 403, "error_code": "GITHUB_HTTP_403",
                              "execution_id": "run-20261117-A", "observed_at_utc": "2026-11-17T00:00:00Z"}}

    def invoke(self, event, reason, cycle="UNVERIFIED", raw=False):
        import subprocess, sys
        script = ROOT / "experiments" / "oss-top10-safe-adoption" / "site_github403_evidence_bridge.py"
        value = event if raw else json.dumps(event).encode("utf-8")
        proc = subprocess.run([sys.executable, "-B", str(script)], input=value,
                              capture_output=True, timeout=8)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(proc.stderr)
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["reason_code"], reason)
        self.assertEqual(out["observed_cycle_status"], cycle)
        self.assertEqual(out["classification"], "UNVERIFIED")
        self.assertEqual(out["source_authentication"], "UNVERIFIED")
        self.assertEqual(out["github_authentication"], "UNVERIFIED")
        self.assertEqual(out["site_runtime_integration"], "UNVERIFIED")
        self.assertEqual(out["operational_clearance"], "BLOCKED")
        self.assertFalse(out["allow_retry"])
        self.assertFalse(out["allow_write"])
        self.assertEqual(out["external_requests"], 0)
        self.assertEqual(out["external_mutations"], 0)
        return proc.stdout.decode("utf-8")

    def test_no_official_source(self):
        self.invoke(None, "MISSING_OFFICIAL_SOURCE")

    def test_403_claim_diagnostic_block_no_auth(self):
        self.invoke(self.event(), "UNAUTHENTICATED_SITE_OBSERVATION", "BLOCKED")

    def test_spoofed_pass_cannot_authenticate(self):
        x = self.event(); x["collector"]["auth_status"] = "PASS"; x["signature"] = "FAKE"
        self.invoke(x, "UNAUTHENTICATED_SITE_OBSERVATION", "BLOCKED")

    def test_wrong_project(self):
        x = self.event(); x["project_id"] = "other"
        self.invoke(x, "PROJECT_ID_MISMATCH")

    def test_non403_report_is_not_claimed_as_403(self):
        x = self.event(); x["collector"]["http_status"] = 200
        self.invoke(x, "HTTP_EVIDENCE_MISMATCH")

    def test_403_reason_code_mismatch(self):
        x = self.event(); x["collector"]["error_code"] = "SAME_HEAD"
        self.invoke(x, "HTTP_EVIDENCE_MISMATCH")

    def test_missing_execution_id(self):
        x = self.event(); x["collector"].pop("execution_id")
        self.invoke(x, "SOURCE_INCOMPLETE")

    def test_timestamp_without_timezone(self):
        x = self.event(); x["collector"]["observed_at_utc"] = "2026-11-17T00:00:00"
        self.invoke(x, "SOURCE_INCOMPLETE")

    def test_collector_missing(self):
        x = self.event(); x.pop("collector")
        self.invoke(x, "SOURCE_INCOMPLETE")

    def test_native_part_missing(self):
        x = self.event(); x["native"] = {"last_run": {"id": "a"}}
        self.invoke(x, "NATIVE_EVIDENCE_PARTIAL")

    def test_claimed_native_result_never_promotes(self):
        x = self.event(); x["native"] = {"last_run": {}, "latest_result": {}}
        self.invoke(x, "UNAUTHENTICATED_SITE_OBSERVATION", "BLOCKED")

    def test_wrong_local_schema(self):
        x = self.event(); x["schema"] = "UNKNOWN"
        self.invoke(x, "INPUT_INVALID")

    def test_duplicate_keys(self):
        self.invoke(b'{"schema":"A","schema":"B"}', "INPUT_INVALID", raw=True)

    def test_oversized_input(self):
        self.invoke(b"x" * 65537, "INPUT_INVALID", raw=True)

    def test_secret_never_echoed(self):
        x = self.event(); x["collector"]["error_detail"] = "sk-proj-supersecret987654321"
        text = self.invoke(x, "UNAUTHENTICATED_SITE_OBSERVATION", "BLOCKED")
        self.assertNotIn("supersecret", text)

    def test_invalid_utf8(self):
        self.invoke(b"\xff\xfe", "INPUT_INVALID", raw=True)


if __name__ == '__main__':
    unittest.main()
