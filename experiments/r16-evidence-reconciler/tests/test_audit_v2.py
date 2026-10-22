import copy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_v2 import AUTOMATION_ID, REQUIRED, check

BASE = {
    'target_slot': '2026-10-22T22:00:00+09:00',
    'schedule': {'id': AUTOMATION_ID, 'is_enabled': True, 'last_run_time': '2026-10-22T13:01:47.915363Z'},
}
RUN = {
    'origin': 'official_task_run_details', 'automation_id': AUTOMATION_ID,
    'run_id': 'EXAMPLE-ONLY-NOT-A-REAL-RUN-ID', 'scheduled_for': BASE['target_slot'],
    'started_at': '2026-10-22T22:01:47+09:00',
    'completed_at': '2026-10-22T22:02:30+09:00', 'status': 'completed',
}
CALLS = [{
    'origin':'official_task_tool_call', 'run_id':RUN['run_id'],
    'target': target, 'tool': tool, 'locator': locator, 'success': True,
    'observed_at':'2026-10-22T22:02:00+09:00', 'version': 'a'*40 if vt=='sha' else '1792416391.631669',
    'invocation_id': f'EXAMPLE-{i}',
} for i, (target,(tool,locator,vt)) in enumerate(REQUIRED.items())]


class AuditV2Tests(unittest.TestCase):
    def make(self):
        return {**copy.deepcopy(BASE), 'native_run':copy.deepcopy(RUN), 'tool_calls':copy.deepcopy(CALLS)}
    def test_metadata_only_never_success(self):
        r=check(BASE);self.assertEqual(r['status'],'미검증');self.assertIn('공식 개별 회차',r['reason'])
    def test_valid_synthetic_format_not_authenticity(self):
        r=check(self.make());self.assertTrue(r['status'].startswith('형식 통과'));self.assertIn('별도 확인',r['authenticity'])
    def test_wrong_original_task(self):
        p=self.make();p['schedule']['id']='different';self.assertEqual(check(p)['status'],'미검증')
    def test_disabled_task(self):
        p=self.make();p['schedule']['is_enabled']=False;self.assertEqual(check(p)['status'],'미검증')
    def test_old_last_run_does_not_claim_metadata_evidence(self):
        p=copy.deepcopy(BASE);p['schedule']['last_run_time']='2026-10-22T12:01:47Z'
        result=check(p)
        self.assertEqual(result['status'],'미검증')
        self.assertIn('원본 로그 미제공',result['reason'])
        self.assertIn('회차 실행 여부 확인 불가',result['trigger'])
    def test_historical_official_run_still_checks_after_later_slot(self):
        p=self.make();p['schedule']['last_run_time']='2026-10-22T14:00:27.196513Z'
        result=check(p)
        self.assertTrue(result['status'].startswith('형식 통과'))
        self.assertIn('원본 진위',result['authenticity'])
    def test_historical_metadata_alone_is_not_evidence(self):
        p=copy.deepcopy(BASE);p['schedule']['last_run_time']='2026-10-22T14:00:27.196513Z'
        result=check(p)
        self.assertEqual(result['status'],'미검증')
        self.assertIsNone(result['native_run_id'])
    def test_self_reported_source_invalid(self):
        p=self.make();p['native_run']['origin']='activepieces_self_report';self.assertEqual(check(p)['status'],'미검증')
    def test_missing_official_run_id(self):
        p=self.make();p['native_run']['run_id']=None;self.assertIn('ID 미제공',check(p)['reason'])
    def test_wrong_slot(self):
        p=self.make();p['native_run']['scheduled_for']='2026-10-22T21:00:00+09:00';self.assertIn('슬롯 불일치',check(p)['reason'])
    def test_wrong_automation_id_in_native(self):
        p=self.make();p['native_run']['automation_id']='x';self.assertEqual(check(p)['status'],'미검증')
    def test_wrong_status(self):
        p=self.make();p['native_run']['status']='failed';self.assertIn('종료 성공',check(p)['reason'])
    def test_late_tool_call(self):
        p=self.make();p['tool_calls'][0]['observed_at']='2026-10-22T22:05:00+09:00';self.assertIn('current_handoff',check(p)['missing'])
    def test_cross_run_tool_call(self):
        p=self.make();p['tool_calls'][0]['run_id']='other';self.assertIn('current_handoff',check(p)['missing'])
    def test_duplicate_invocation(self):
        p=self.make();p['tool_calls'][1]['invocation_id']=p['tool_calls'][0]['invocation_id'];self.assertIn('slack_thread',check(p)['missing'])
    def test_wrong_tool_name(self):
        p=self.make();p['tool_calls'][0]['tool']='fabricated';self.assertIn('current_handoff',check(p)['missing'])
    def test_wrong_locator(self):
        p=self.make();p['tool_calls'][0]['locator']='other-file';self.assertIn('current_handoff',check(p)['missing'])
    def test_wrong_sha(self):
        p=self.make();p['tool_calls'][0]['version']='not-a-sha';self.assertIn('current_handoff',check(p)['missing'])
    def test_slack_ts_invalid(self):
        p=self.make();p['tool_calls'][1]['version']='hello';self.assertIn('slack_thread',check(p)['missing'])
    def test_manual_tool_call_is_not_scheduled(self):
        p=self.make();p['tool_calls'][0]['origin']='manual_chat';self.assertIn('current_handoff',check(p)['missing'])
    def test_missing_one_required_call(self):
        p=self.make();p['tool_calls']=p['tool_calls'][:-1];self.assertIn('slack_thread',check(p)['missing'])
    def test_r16_handoff_is_required(self):
        p=self.make()
        p['tool_calls']=[c for c in p['tool_calls'] if c['target']!='current_handoff']
        r=check(p)
        self.assertEqual(r['status'],'미검증')
        self.assertIn('current_handoff',r['missing'])
    def test_r13_legacy_docs_cannot_replace_r16_handoff(self):
        p=self.make()
        p['tool_calls'][0]['target']='memory_index'
        p['tool_calls'][0]['locator']='docs/ai/PROJECT_MEMORY_INDEX.md'
        r=check(p)
        self.assertIn('current_handoff',r['missing'])
    def test_r16_handoff_slack_sufficient_for_format(self):
        p=self.make()
        r=check(p)
        self.assertTrue(r['status'].startswith('형식 통과'))
        self.assertEqual(r['missing'],[])
        self.assertIn('실제 업무 목표 수행',r['reason'])
    def test_r16_slack_target_remains_required(self):
        p=self.make()
        p['tool_calls']=[c for c in p['tool_calls'] if c['target']!='slack_thread']
        self.assertIn('slack_thread',check(p)['missing'])
    def test_naive_time_rejected(self):
        p=self.make();p['target_slot']='2026-10-22T22:00:00';self.assertEqual(check(p)['status'],'미검증')
    def test_out_of_order_run(self):
        p=self.make();p['native_run']['completed_at']='2026-10-22T22:01:00+09:00';self.assertIn('시각 불일치',check(p)['reason'])


    def test_fractional_hour_slot_rejected(self):
        p=self.make()
        fractional='2026-10-22T22:00:00.500000+09:00'
        p['target_slot']=fractional
        p['native_run']['scheduled_for']=fractional
        r=check(p)
        self.assertEqual(r['status'],'미검증')
        self.assertIn('정각 슬롯',r['reason'])

    def test_unhashable_target_does_not_crash(self):
        p=self.make()
        p['tool_calls'].insert(0,{'target': []})
        r=check(p)
        self.assertTrue(r['status'].startswith('형식 통과'))

    def test_unhashable_tool_does_not_crash(self):
        p=self.make()
        p['tool_calls'][0]['tool']=[]
        r=check(p)
        self.assertEqual(r['status'],'미검증')
        self.assertIn('current_handoff',r['missing'])

    def test_oversized_tool_call_list_rejected(self):
        p=self.make()
        p['tool_calls'].extend([{'target':'irrelevant'} for _ in range(15)])
        r=check(p)
        self.assertEqual(r['status'],'미검증')
        self.assertIn('16건 초과',r['reason'])

if __name__=='__main__':unittest.main()
