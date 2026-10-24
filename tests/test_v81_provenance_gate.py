import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'scripts'/'v81_provenance_gate.py')
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def example():
    rows=[]
    for key in sorted(gate.EXPECTED_IDS):
        row={'id':key,'status':'PASS'}
        if key in gate.REPLACEMENTS:
            row.update(scope='LOCAL_FIXTURE_ONLY',source='SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE')
        rows.append(row)
    return {
        'kind':'LOCAL_RULE_CHECK_REPORT_NOT_NATIVE_SCHEDULE_ATTESTATION',
        'goal':'all','catalog_total':100,'executed_rules':100,
        'executed_independent_llms':0,'official_same_run_github_slack_verified':False,
        'deployed_to_chatgpt_scheduler':False,'scheduled_task_changed':False,
        'official_same_run_raw_ledger':'NOT_PROVIDED',
        'rule_statuses':{'PASS':100},'results':rows,
        'input_sha256':{p:'a'*64 for p in ('runner.py','replacement_bots.py','catalog.json','evidence.json','fixture_SYNTHETIC.json')}
    }

class GateTest(unittest.TestCase):
    def test_valid_local_100_is_not_native(self):
        r=gate.inspect_local_report(example())
        self.assertEqual(100,r['rule_count'])
        self.assertEqual('UNVERIFIED',r['chatgpt_native_run'])
    def test_fake_native_success_rejected(self):
        x=example();x['official_same_run_github_slack_verified']=True
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_fake_scheduler_deploy_rejected(self):
        x=example();x['deployed_to_chatgpt_scheduler']=True
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_duplicate_role_rejected(self):
        x=example();x['results'][0]['id']=x['results'][1]['id']
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_rule_failure_rejected(self):
        x=example();x['results'][0]['status']='FAIL'
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_synthetic_scope_forgery_rejected(self):
        x=example();next(r for r in x['results'] if r['id']=='E01')['scope']='OFFICIAL_CHATGPT_RUN'
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_fake_native_raw_ledger_rejected(self):
        x=example()
        x['official_same_run_raw_ledger']='PROVIDED'
        with self.assertRaises(gate.EvidenceError):
            gate.inspect_local_report(x)
    def test_missing_hash_rejected(self):
        x=example();x['input_sha256'].pop('catalog.json')
        with self.assertRaises(gate.EvidenceError):gate.inspect_local_report(x)
    def test_schedule_metadata_remains_not_native(self):
        sha='f'*40
        x={'id':40047176721,'event':'schedule','head_sha':sha,'status':'completed','conclusion':'success','path':'.github/workflows/ai-r16-hourly.yml'}
        r=gate.inspect_schedule_run(x,sha)
        self.assertEqual('UNVERIFIED',r['chatgpt_native_run'])
    def test_push_not_schedule(self):
        sha='f'*40
        x={'id':123,'event':'push','head_sha':sha,'status':'completed','conclusion':'success','path':'.github/workflows/ai-r16-hourly.yml'}
        with self.assertRaises(gate.EvidenceError):gate.inspect_schedule_run(x,sha)
    def test_wrong_sha_rejected(self):
        x={'id':123,'event':'schedule','head_sha':'e'*40,'status':'completed','conclusion':'success','path':'.github/workflows/ai-r16-hourly.yml'}
        with self.assertRaises(gate.EvidenceError):gate.inspect_schedule_run(x,'f'*40)

if __name__=='__main__':unittest.main()
