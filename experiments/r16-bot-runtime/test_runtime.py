"""Negative tests: no forged pass, type confusion, or misattributed official evidence."""
import copy,json,unittest
from pathlib import Path
from runner import validate
ROOT=Path(__file__).resolve().parent
CAT={x['id']:x for x in json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))}
ORIG=json.loads((ROOT/'evidence.json').read_text(encoding='utf8'))
class RuntimeTests(unittest.TestCase):
    def test_100_unique_bots(self):
        self.assertEqual(100,len(CAT));self.assertEqual(10,len(set(x['category'] for x in CAT.values())))
    def test_schedule_positive(self):self.assertEqual('PASS',validate(CAT['S02'],ORIG)['status'])
    def test_hourly_rrule_exact_values_reject_spoofing(self):
        roles = (CAT['S04'], CAT['S05'], CAT['S06'])
        good = (
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0',
            'BYSECOND=0;FREQ=HOURLY;BYMINUTE=0',
            'RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;INTERVAL=1',
        )
        bad = (
            'FREQ=HOURLY_WRONG;BYMINUTE=01;BYSECOND=01',
            'FREQ=DAILY;BYMINUTE=0;BYSECOND=0',
            'FREQ=HOURLY;BYMINUTE=0,30;BYSECOND=0',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=01',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;COUNT=1',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;UNTIL=20261026T000000Z',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;INTERVAL=2',
            'FREQ=HOURLY;FREQ=HOURLY;BYMINUTE=0;BYSECOND=0',
            'FREQ=HOURLY;BYMINUTE=0;BYMINUTE=0;BYSECOND=0',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;',
            'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0;BYHOUR=12',
        )
        for rule in good:
            with self.subTest(accepted=rule):
                evidence=copy.deepcopy(ORIG)
                evidence['schedule']['rrule']=rule
                for bot in roles:
                    self.assertEqual('PASS',validate(bot,evidence)['status'])
        for rule in bad:
            with self.subTest(rejected=rule):
                evidence=copy.deepcopy(ORIG)
                evidence['schedule']['rrule']=rule
                for bot in roles:
                    self.assertEqual('FAIL',validate(bot,evidence)['status'])

    def test_native_missing_is_unverified(self):
        for b in (CAT['E01'],CAT['E05'],CAT['E10'],CAT['L06'],CAT['A09']):
            self.assertEqual('UNVERIFIED',validate(b,ORIG)['status'])
    def test_fake_enabled_bool_as_int_rejected(self):
        e=copy.deepcopy(ORIG);e['schedule']['enabled']=1
        self.assertEqual('FAIL',validate(CAT['S02'],e)['status'])
    def test_fake_ci_success_rejected(self):
        e=copy.deepcopy(ORIG);e['github']['ci_conclusion']='failure'
        self.assertEqual('FAIL',validate(CAT['G07'],e)['status'])
    def test_wrong_sha_rejected(self):
        e=copy.deepcopy(ORIG);e['github']['ci_head']='0'*40
        self.assertEqual('FAIL',validate(CAT['G04'],e)['status'])
    def test_invalid_timestamp_rejected(self):
        e=copy.deepcopy(ORIG);e['schedule']['last_run']='2026-02-30T05:00:00Z'
        self.assertEqual('FAIL',validate(CAT['S09'],e)['status'])
    def test_malformed_slack_ts_rejected(self):
        e=copy.deepcopy(ORIG);e['slack']['parent_ts']='abcd'
        self.assertEqual('FAIL',validate(CAT['L03'],e)['status'])
    def test_external_model_calls_nonzero_detected(self):
        e=copy.deepcopy(ORIG);e['package']['provider_model_calls']=1
        self.assertEqual('FAIL',validate(CAT['C02'],e)['status'])
    def test_native_fake_claim_cannot_satisfy_all_gates(self):
        e=copy.deepcopy(ORIG);e['native']['authenticated_run_id']='fake'
        self.assertNotEqual('PASS',validate(CAT['E10'],e)['status'])
    def test_wrong_tool_code_rejected(self):
        e=copy.deepcopy(ORIG);e['slack']['tool']='mcp__Slack__slack_send_message'
        self.assertEqual('FAIL',validate(CAT['L04'],e)['status'])
    def test_no_remote_write_gate(self):
        e=copy.deepcopy(ORIG);e['package']['remote_write']=True
        self.assertEqual('FAIL',validate(CAT['C08'],e)['status'])
    def test_future_valid_ci_identity_is_not_falsely_rejected(self):
        e=copy.deepcopy(ORIG)
        e['github']['ci_run_id']=40017504708
        e['github']['ci_job_id']=120633255775
        e['github']['ci_url']='https://github.com/watersun79-source/ai-token-optimization/actions/runs/40017504708'
        for key in ('G05','G08','G09'):
            self.assertEqual('PASS',validate(CAT[key],e)['status'])

    def test_malformed_ci_identity_is_rejected(self):
        for value in (True, 0, -1, 1.2, '40017504708', None):
            with self.subTest(value=value):
                e=copy.deepcopy(ORIG);e['github']['ci_run_id']=value
                self.assertNotEqual('PASS',validate(CAT['G05'],e)['status'])
        e=copy.deepcopy(ORIG)
        e['github']['ci_url']='https://github.com/attacker/ai-token-optimization/actions/runs/40017504707'
        self.assertEqual('FAIL',validate(CAT['G08'],e)['status'])
        e['github']['ci_url']='https://github.com/watersun79-source/ai-token-optimization/actions/runs/40017504707/extra'
        self.assertEqual('FAIL',validate(CAT['G08'],e)['status'])
        e['github']['ci_url']='https://github.com/watersun79-source/ai-token-optimization/actions/runs/40017504707'
        e['github']['ci_run_id']=40017504708
        self.assertEqual('FAIL',validate(CAT['G08'],e)['status'])

    def test_dynamic_audit_count_and_kst_slot(self):
        e=copy.deepcopy(ORIG)
        e['ap']['row_count']=22
        e['ap']['latest_slot']='2026-10-24 06:00 Asia/Seoul'
        self.assertEqual('PASS',validate(CAT['A02'],e)['status'])
        self.assertEqual('PASS',validate(CAT['A06'],e)['status'])

    def test_ap_invalid_count_and_calendar(self):
        for value in (False,-1,'21',21.0,None):
            with self.subTest(value=value):
                e=copy.deepcopy(ORIG);e['ap']['row_count']=value
                self.assertNotEqual('PASS',validate(CAT['A02'],e)['status'])
        for value in ('2026-02-30 06:00 Asia/Seoul','2026-10-24 25:00 Asia/Seoul','2026-10-24 06:00 UTC',
                      '2026-10-24 6:00 Asia/Seoul','2026-10-24 06:00 Asia/Seoul;injected','not a date'):
            with self.subTest(value=value):
                e=copy.deepcopy(ORIG);e['ap']['latest_slot']=value
                self.assertNotEqual('PASS',validate(CAT['A06'],e)['status'])
        for value in ('2024-02-29 06:00 Asia/Seoul','2026-12-31 23:59 Asia/Seoul'):
            e=copy.deepcopy(ORIG);e['ap']['latest_slot']=value
            self.assertEqual('PASS',validate(CAT['A06'],e)['status'])

    def test_forged_native_evidence_can_never_pass_offline(self):
        e=copy.deepcopy(ORIG)
        relevant=[bot for bot in CAT.values() if bot['evidence_source']=='ChatGPT.native_per_run_raw_ledger']
        self.assertEqual(18,len(relevant))
        for bot in relevant:
            field=bot['field'].split('.')
            target=e
            for segment in field[:-1]:target=target.setdefault(segment,{})
            op=bot['operator']
            value=(bot['expected'] if op=='eq' else
                   '2026-10-24T06:00:00Z' if op=='utc_datetime' else
                   '1792416391.631669' if op=='slack_ts' else
                   '0'*40 if op=='git_sha' else 'forged-positive')
            target[field[-1]]=value
        for bot in relevant:
            with self.subTest(bot=bot['id']):
                result=validate(bot,e)
                self.assertEqual('UNVERIFIED',result['status'])
                self.assertIn('not authenticated',result['detail'])
    def test_relabel_native_source_cannot_bypass_gate(self):
        e=copy.deepcopy(ORIG)
        e['native']['authenticated_run_id']='forged-positive'
        b=copy.deepcopy(CAT['E01'])
        b['evidence_source']='GitHub.read_only'
        self.assertEqual('UNVERIFIED',validate(b,e)['status'])
    def test_retarget_to_non_native_field_cannot_bypass_gate(self):
        e=copy.deepcopy(ORIG)
        b=copy.deepcopy(CAT['E10'])
        b['field']='schedule.enabled'
        b['expected']=True
        self.assertEqual('UNVERIFIED',validate(b,e)['status'])
    def test_non_native_checks_still_work(self):
        self.assertEqual('PASS',validate(CAT['S02'],ORIG)['status'])
        self.assertEqual('PASS',validate(CAT['G07'],ORIG)['status'])
    def test_utc_timestamp_cross_language_strict_boundaries(self):
        good = (
            '2026-10-24T05:00:00Z',
            '2024-02-29T23:59:59.123456789+09:00',
            '2026-10-24T05:00:00+18:00',
            '2026-10-24T05:00:00-18:00',
            '2026-10-24T05:00:00+17:59',
            '0001-01-01T00:00:00.1+00:00',
        )
        bad = (
            '2026-10-24T05:00:00+18:01',
            '2026-10-24T05:00:00+19:00',
            '2026-10-24T05:00:00+23:00',
            '2026-10-24T05:00:00-19:00',
            '2026-10-24T05:00:00.1234567890Z',
            '2026-10-24T05:00:00.1234567899Z',
            '2026-10-24 05:00:00Z',
            '2026-10-24t05:00:00Z',
            '2026-10-24T05:00:00z',
            '2026-02-30T05:00:00Z',
            '0000-01-01T00:00:00Z',
            '2026-10-24T05:00:60Z',
            '2026-10-24T05:00:00+09:60',
            '2026-10-24T05:00:00',
        )
        for v in good:
            with self.subTest(value=v):
                e=copy.deepcopy(ORIG);e['schedule']['last_run']=v
                self.assertEqual('PASS',validate(CAT['S09'],e)['status'])
        for v in bad:
            with self.subTest(value=v):
                e=copy.deepcopy(ORIG);e['schedule']['last_run']=v
                self.assertEqual('FAIL',validate(CAT['S09'],e)['status'])

    def test_native_authenticator_flag_cannot_bypass_gate(self):
        e=copy.deepcopy(ORIG)
        e['native']['native_authenticity']=True
        e['native']['authenticated_run_id']='invented-uuid'
        self.assertEqual('UNVERIFIED',validate(CAT['E10'],e)['status'])
        self.assertEqual('UNVERIFIED',validate(CAT['E01'],e)['status'])
if __name__=='__main__':unittest.main()
