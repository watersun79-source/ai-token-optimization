"""Offline safety tests. The fixture executable below is NOT Gemini."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapter import Adapter, Blocked, Config, CLI_SYSTEM_SETTINGS, DENY_POLICY
from server import Server


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cli = self.root / 'offline-fixture-cli'
        self.cli.write_text('#!' + sys.executable + '''
import json, os, pathlib, sys, time
root=pathlib.Path(__file__).parent
if '--version' in sys.argv:
    print('0.66.0')
elif '--help' in sys.argv:
    print('--prompt --output-format --policy --approval-mode')
else:
    incoming=sys.stdin.read()
    controls=json.loads(pathlib.Path(os.environ['GEMINI_CLI_SYSTEM_SETTINGS_PATH']).read_text())
    if controls.get('model',{}).get('maxSessionTurns')!=1: sys.exit(70)
    (root/'runtime-controls').write_text(json.dumps(controls))
    with (root/'calls').open('a') as f: f.write('called\\n')
    mode=(root/'mode').read_text() if (root/'mode').exists() else 'ok'
    if mode=='hang': time.sleep(5)
    if mode=='hold': time.sleep(0.4)
    if mode=='large': print('X'*200000); sys.exit(0)
    if mode=='invalid': print('invalid JSON'); sys.exit(0)
    if mode=='secret': print(json.dumps({'response':'AIza'+'a'*30})); sys.exit(0)
    print('OFFLINE_TEST_STDERR_SENTINEL',file=sys.stderr)
    print(json.dumps({'response':'OFFLINE_TEST_EXECUTABLE_RESPONSE'}))
''')
        self.cli.chmod(0o700)
        self.gate = self.root / 'verified-gate.json'
        self.controls = self.root / 'system-settings.json'
        self.controls.write_text(json.dumps(CLI_SYSTEM_SETTINGS))
        self.controls.chmod(0o600)
        self.config = Config(self.cli, self.root / 'state', self.root / 'cli-home', self.gate, timeout_seconds=2,
                             system_settings_file=self.controls)
        self.clean_env = patch.dict(os.environ, {'PATH': os.environ.get('PATH','')}, clear=True)
        self.clean_env.start()
        # Ordinary test users cannot create root-owned configuration ancestors.
        # Only this OS ownership check is doubled; real files, process I/O and
        # immutable control validation are exercised. The rejection is checked below.
        self.root_checks = patch.object(Adapter,'_root_control_path_is_secure',return_value=True)
        self.root_checks.start()
        self.adapter = Adapter(self.config)

    def tearDown(self):
        self.clean_env.stop()
        self.root_checks.stop()
        self.temp.cleanup()

    def verified_gate(self, **overrides):
        now = datetime.now(timezone.utc)
        data = {'schema':'GEMINI_CLI_VERIFIED_GATE_V2','gate_id':'offline-gate-0001','cli_version':'0.66.0',
                'cli_realpath':str(self.cli.resolve()),'cli_home':str(self.config.cli_home),
                'isolated_cli_configuration_reviewed':True,'max_cli_invocations':1,
                'auth':{'status':'PASS','method':'oauth-personal','source_kind':'official-cli-runtime-verification',
                        'verified_at':now.isoformat(),'evidence_ref':'OFFLINE_TEST_ONLY_NOT_AUTH_EVIDENCE'},
                'quota':{'status':'PASS','source_kind':'gemini-cli-provider-quota','route':'code-assist-personal',
                         'free':True,'paid_billing_enabled':False,'remaining_requests':1,
                         'verified_at':now.isoformat(),'evidence_ref':'OFFLINE_TEST_ONLY_NOT_FREE_QUOTA'},
                'expires_at':(now+timedelta(minutes=5)).isoformat()}
        data.update(overrides)
        self.gate.write_text(json.dumps(data))
        self.gate.chmod(0o600)
        return data

    def calls(self):
        p=self.root/'calls'
        return len(p.read_text().splitlines()) if p.exists() else 0

    def test_missing_gate_never_invokes_model(self):
        with self.assertRaisesRegex(Blocked,'VERIFICATION_GATE_MISSING'):
            self.adapter.review('request-0001','Review this simple public plan.')
        self.assertEqual(self.calls(),0)

    def test_api_key_environment_blocks_and_value_not_returned(self):
        self.verified_gate()
        with patch.dict(os.environ,{'GEMINI_API_KEY':'OFFLINE_DUMMY_DO_NOT_USE'}):
            with self.assertRaisesRegex(Blocked,'PROVIDER_KEY_OR_VERTEX_ENV') as caught:
                self.adapter.review('request-0001','Review this plan.')
        self.assertNotIn('OFFLINE_DUMMY',str(caught.exception))
        self.assertEqual(self.calls(),0)

    def test_web_usage_cannot_establish_cli_quota(self):
        gate=self.verified_gate()
        gate['quota']['source_kind']='gemini-web-usage-display'
        self.verified_gate(quota=gate['quota'])
        with self.assertRaisesRegex(Blocked,'CLI_FREE_QUOTA_UNVERIFIED'):
            self.adapter.review('request-0001','Review this plan.')
        self.assertEqual(self.calls(),0)

    def test_expired_verification_cannot_call(self):
        self.verified_gate(expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        with self.assertRaisesRegex(Blocked,'GATE_EXPIRED'):
            self.adapter.review('request-0001','Review this plan.')
        self.assertEqual(self.calls(),0)

    def test_private_gate_permissions_required(self):
        self.verified_gate()
        self.gate.chmod(0o644)
        with self.assertRaisesRegex(Blocked,'UNSAFE_VERIFICATION_GATE'):
            self.adapter.review('request-0001','Review this plan.')
        self.assertEqual(self.calls(),0)

    def test_boolean_budget_cannot_impersonate_integer_one(self):
        for invalid in [{'max_cli_invocations':True},{'schema':'GEMINI_CLI_VERIFIED_GATE_V1'},
                        {'max_model_calls':1}]:
            self.verified_gate(**invalid)
            with self.assertRaisesRegex(Blocked,'INVALID_VERIFICATION_GATE'):
                self.adapter.review('request-0001','Review this plan.')
        self.assertEqual(self.calls(),0)

    def test_input_secret_and_id_injection_rejected(self):
        for rid,prompt in [('bad id; echo leak','plan'),('request-0001','AIza'+'a'*25),('request-0001','bad\x00input')]:
            with self.assertRaises(Blocked): self.adapter.review(rid,prompt)
        self.assertEqual(self.calls(),0)

    def test_real_subprocess_runner_fixture_and_durable_deduplication(self):
        self.verified_gate()
        first=self.adapter.review('request-0001','Review this public plan.')
        self.assertEqual(first['response'],'OFFLINE_TEST_EXECUTABLE_RESPONSE')
        self.assertNotIn('STDERR_SENTINEL',json.dumps(first))
        controls=json.loads((self.root/'runtime-controls').read_text())
        self.assertEqual(controls['model']['maxSessionTurns'],1)
        self.assertFalse(controls['hooksConfig']['enabled'])
        self.assertFalse(controls['experimental']['autoMemory'])
        self.assertEqual(first['provider_request_count'],'UNVERIFIED')
        self.gate.unlink()
        restarted=Adapter(self.config)
        self.assertEqual(restarted.review('request-0001','Review this public plan.'),first)
        self.assertEqual(self.calls(),1)
        with self.assertRaisesRegex(Blocked,'REQUEST_ID_CONFLICT'):
            restarted.review('request-0001','A different plan.')

    def test_one_cli_invocation_budget_is_consumed_before_execution(self):
        self.verified_gate()
        self.adapter.review('request-0001','Review plan A.')
        with self.assertRaisesRegex(Blocked,'ONE_CLI_INVOCATION_BUDGET_CONSUMED'):
            self.adapter.review('request-0002','Review plan B.')
        self.assertEqual(self.calls(),1)
        status=self.adapter.status()
        self.assertFalse(status['generation_ready'])
        self.assertEqual(status.get('provider_request_count'),'UNVERIFIED')
        self.assertNotIn('one_call_budget_consumed',status)
        self.assertTrue(status['one_cli_invocation_budget_consumed'])

    def test_concurrency_busy_and_duplicate_pending(self):
        self.verified_gate()
        (self.root/'mode').write_text('hold')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.adapter.review,'request-0001','Review plan A.')
            deadline=time.monotonic()+2
            while self.calls()==0 and time.monotonic()<deadline: time.sleep(0.01)
            with self.assertRaisesRegex(Blocked,'PENDING_OR_UNCERTAIN'):
                self.adapter.review('request-0001','Review plan A.')
            with self.assertRaisesRegex(Blocked,'CONCURRENCY_LIMIT'):
                self.adapter.review('request-0002','Review plan B.')
            self.assertEqual(future.result()['status'],'PASS_REAL_CLI_JSON_RESPONSE')
        self.assertEqual(self.calls(),1)

    def test_timeout_is_bounded_and_not_automatically_retried(self):
        self.verified_gate()
        (self.root/'mode').write_text('hang')
        adapter=Adapter(replace(self.config,timeout_seconds=0.15))
        start=time.monotonic()
        first=adapter.review('request-0001','Review this plan.')
        self.assertLess(time.monotonic()-start,2)
        self.assertEqual(first['status'],'BLOCKED_CLI_TIMEOUT')
        self.assertEqual(adapter.review('request-0001','Review this plan.'),first)
        self.assertEqual(self.calls(),1)

    def test_invalid_output_and_secret_output_remain_blocked(self):
        for mode,expected in [('invalid','BLOCKED_CLI_INVALID_JSON'),('secret','BLOCKED_SECRET_LIKE_OUTPUT')]:
            with self.subTest(mode=mode):
                gate_id='offline-gate-'+mode
                self.verified_gate(gate_id=gate_id)
                (self.root/'mode').write_text(mode)
                result=self.adapter.review('request-'+mode,'Review this plan.')
                self.assertEqual(result['status'],expected)
                self.assertIsNone(result['response'])

    def test_output_cap(self):
        self.verified_gate()
        (self.root/'mode').write_text('large')
        adapter=Adapter(replace(self.config,max_output_bytes=1024))
        result=adapter.review('request-0001','Review this plan.')
        self.assertEqual(result['status'],'BLOCKED_CLI_OUTPUT_LIMIT')

    def test_policy_change_blocks_execution(self):
        self.verified_gate()
        self.adapter.policy.write_text('changed')
        with self.assertRaisesRegex(Blocked,'POLICY_CHANGED'):
            self.adapter.review('request-0001','Review this plan.')
        self.adapter.policy.write_text(DENY_POLICY)
        self.controls.write_text(json.dumps({'model':{'maxSessionTurns':-1}}))
        with self.assertRaisesRegex(Blocked,'SYSTEM_CONTROLS_CHANGED'):
            self.adapter.review('request-0001','Review this plan.')
        self.controls.write_text(json.dumps(CLI_SYSTEM_SETTINGS))
        self.root_checks.stop()
        try:
            with self.assertRaisesRegex(Blocked,'UNSAFE_SYSTEM_CONTROLS'):
                self.adapter.review('request-0001','Review this plan.')
        finally:
            self.root_checks.start()
        self.assertEqual(self.calls(),0)

    def test_mcp_handshake_and_strict_tool_arguments(self):
        server=Server(self.adapter)
        self.assertEqual(server.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'})['error']['message'],'Not initialized')
        init=server.handle({'jsonrpc':'2.0','id':2,'method':'initialize','params':{'protocolVersion':'2025-06-18'}})
        self.assertEqual(init['result']['serverInfo']['name'],'gemini-real-cli-mcp')
        names=[t['name'] for t in server.handle({'jsonrpc':'2.0','id':3,'method':'tools/list'})['result']['tools']]
        self.assertEqual(names,['gemini_status','gemini_review'])
        bad=server.handle({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'gemini_review','arguments':{'request_id':'request-0001','prompt':'plan','args':['--yolo']}}})
        self.assertEqual(bad['error']['code'],-32602)
        blocked=server.handle({'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'gemini_review','arguments':{'request_id':'request-0001','prompt':'plan'}}})
        self.assertTrue(blocked['result']['isError'])
        self.assertFalse(blocked['result']['structuredContent']['model_called'])


if __name__=='__main__': unittest.main()
