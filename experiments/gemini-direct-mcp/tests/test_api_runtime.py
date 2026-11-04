"""Offline key-storage, durable-budget and process/TLS boundary checks."""
import dataclasses
import http.client
import json
import os
from pathlib import Path
import signal
import ssl
import sys
import tempfile
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'gemini-real-mcp'))
from adapter import Adapter, Config
from http_server import OwnerBinding
try:
    import api_runtime as api
except ImportError:
    api=None

KEY='offline-fixture-api-key-0000000000000001'
AQ_KEY='AQ.OFFLINE_SYNTHETIC_NOT_A_PROVIDER_CREDENTIAL_0001'
ACTOR='offline-api-owner'
PROJECT='offline-fixture-project'
MODEL='gemini-3.5-flash-lite'


class ApiRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'API runtime is not implemented')
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.adapter=Adapter(Config(None,self.root/'state',self.root/'cli-home'))
        self.owner=OwnerBinding(self.adapter.config.state_dir)
        self.calls=[]
        self.worker_result={'status':'PASS_REAL_GEMINI_API_RESPONSE','response':'OFFLINE_MODEL_RESPONSE',
                            'model':MODEL,'finish_reason':'STOP','usage':{'totalTokenCount':4}}
        def runner(payload):
            self.calls.append(payload)
            return {'status':'API_METADATA_AUTHENTICATED'} if payload['operation']=='metadata' else dict(self.worker_result)
        self.runtime=api.ApiRuntime(self.adapter,self.owner,allowed_project_id=PROJECT,runner=runner)

    def tearDown(self):
        if hasattr(self,'tmp'): self.tmp.cleanup()

    def register(self):
        return self.runtime.register(ACTOR,KEY)

    def evidence(self,**changes):
        now=datetime.now(timezone.utc)
        value={'project_id':PROJECT,'observed_at':now.isoformat(),
               'quota_day_pacific':now.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat(),
               'remaining_requests':1,'evidence_refs':{field:'private:d1/fixture/r1/'+field for field in
               ['auth','project_binding','free_tier','billing','daily_quota']}}
        value.update(changes)
        return value

    def test_registration_is_private_idempotent_and_never_auto_prepares(self):
        result=self.register()
        self.assertEqual(result['status'],'API_KEY_AUTHENTICATED_FREE_EVIDENCE_REQUIRED')
        self.assertIs(result['configured'],True)
        self.assertEqual(self.runtime.key_path.stat().st_mode&0o777,0o600)
        self.assertEqual(self.runtime.register(ACTOR,KEY),result)
        self.assertEqual(len(self.calls),1)
        status=self.runtime.status()
        self.assertEqual(status['free_evidence_status'],'MISSING')
        self.assertFalse(status['generation_ready'])
        self.assertNotIn(KEY,json.dumps([result,status]))
        self.assertNotIn('api_key_sha256',json.dumps([result,status]))

    def test_aq_key_registration_and_evidence_use_offline_doubles_only(self):
        try:
            result=self.runtime.register(ACTOR,AQ_KEY)
        except api.ApiError:
            self.fail('A supported synthetic AQ. key was rejected')
        self.assertEqual(result['status'],'API_KEY_AUTHENTICATED_FREE_EVIDENCE_REQUIRED')
        self.assertEqual(self.runtime._key(),AQ_KEY)
        self.runtime.prepare(ACTOR,self.evidence())
        self.assertTrue(self.runtime.status()['generation_ready'])
        self.assertNotIn(AQ_KEY,json.dumps([result,self.runtime.status()]))
        self.assertEqual([call['operation'] for call in self.calls],['metadata'])

    def test_aq_format_rejects_other_dots_whitespace_controls_and_oversize_before_metadata(self):
        invalid=['AQ.','AQ.'+'O'*15,'AQ.'+'O'*254,'AX.'+'O'*20,
                 AQ_KEY+'.extra',' '+AQ_KEY,AQ_KEY+'\r\n',AQ_KEY+'\t',
                 'AQ.OFFLINE.OTHER_TOKEN_0001','AQ.'+'한'*20]
        for key in invalid:
            with self.subTest(length=len(key)),self.assertRaisesRegex(api.ApiError,'^INVALID_API_KEY_FORMAT$'):
                self.runtime.register(ACTOR,key)
        self.assertEqual(self.calls,[])

    def test_aq_secret_in_evidence_refs_is_rejected_without_saving_or_generation(self):
        self.register()
        args=self.evidence()
        args['evidence_refs']['auth']='private:fixture/'+AQ_KEY
        with self.assertRaisesRegex(api.ApiError,'^INVALID_PRIVATE_API_EVIDENCE_REFS$'):
            self.runtime.prepare(ACTOR,args)
        self.assertFalse((self.runtime.root/'operator-evidence.json').exists())
        with self.runtime._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM consumed_gates').fetchone()[0],0)
        self.assertEqual(self.runtime.status()['free_evidence_status'],'MISSING')
        self.assertEqual([call['operation'] for call in self.calls],['metadata'])

    def test_other_actor_and_unapproved_key_replacement_are_blocked(self):
        self.register()
        with self.assertRaises(Exception): self.runtime.register('another-owner',KEY)
        with self.assertRaisesRegex(api.ApiError,'API_KEY_REPLACEMENT_REQUIRES_EXPLICIT_APPROVAL'):
            self.runtime.register(ACTOR,'offline-different-api-key-0000000000002')
        self.assertEqual(len(self.calls),1)

    def test_key_metadata_failure_never_persists_or_exposes_upstream(self):
        self.runtime.runner=lambda payload:{'status':'unsafe-'+KEY,'upstream':'raw-provider-error'}
        with self.assertRaisesRegex(api.ApiError,'API_METADATA_WORKER_UNVERIFIED') as error:
            self.register()
        self.assertNotIn(KEY,str(error.exception))
        self.assertFalse(self.runtime.key_path.exists())

    def test_registration_records_only_sanitized_failure_and_does_not_configure_or_spend(self):
        self.runtime.runner=lambda payload:{'status':'API_METADATA_AUTH_TYPE_UNSUPPORTED',
                                             'provider_http_status':401,'raw_message':KEY}
        with self.assertRaisesRegex(api.ApiError,'^API_METADATA_AUTH_TYPE_UNSUPPORTED$') as error:
            self.register()
        self.assertEqual(error.exception.http_status,502)
        self.assertEqual(error.exception.provider_http_status,401)
        record=self.runtime._json('api-registration.json')
        self.assertEqual(set(record),{'result','code','provider_http_status','observed_at'})
        self.assertEqual((record['result'],record['code'],record['provider_http_status']),
                         ('FAILED','API_METADATA_AUTH_TYPE_UNSUPPORTED',401))
        self.assertEqual((self.runtime.root/'api-registration.json').stat().st_mode&0o777,0o600)
        for name in ['api-key','api-auth.json','operator-evidence.json']:
            self.assertFalse((self.runtime.root/name).exists())
        with self.runtime._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM consumed_gates').fetchone()[0],0)
        with patch.object(self.runtime,'_key',side_effect=AssertionError('status key read')):
            status=self.runtime.status()
        self.assertEqual(status.get('last_registration'),record)
        self.assertFalse(status['configured'])
        self.assertFalse(status['generation_ready'])
        self.assertNotIn(KEY,json.dumps([record,status]))

    def test_success_registration_record_does_not_issue_free_evidence(self):
        self.register()
        record=self.runtime.status().get('last_registration')
        self.assertIsInstance(record,dict)
        self.assertEqual((record['result'],record['code'],record['provider_http_status']),
                         ('SUCCEEDED','API_METADATA_AUTHENTICATED',200))
        self.assertIsNotNone(datetime.fromisoformat(record['observed_at']).tzinfo)
        self.assertEqual(self.runtime.status()['free_evidence_status'],'MISSING')

    def test_explicit_same_key_registration_can_recover_missing_auth_metadata(self):
        self.register()
        (self.runtime.root/'api-auth.json').unlink()
        self.assertEqual(self.runtime.status()['status'],'API_KEY_AUTH_UNVERIFIED')
        self.assertEqual(self.register()['status'],'API_KEY_AUTHENTICATED_FREE_EVIDENCE_REQUIRED')
        self.assertEqual(len(self.calls),2)
        self.assertFalse(self.runtime.status()['generation_ready'])

    def test_unsafe_key_permissions_and_expired_evidence_block_without_generation(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        record=self.runtime._json('operator-evidence.json')
        record['candidate']['observed_at']=(datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat()
        self.runtime._save_json('operator-evidence.json',record)
        self.assertEqual(self.runtime.status()['free_evidence_status'],'EXPIRED')
        with self.assertRaises(api.ApiError): self.runtime.review(ACTOR,'request-offline-001','Review a plan.')
        self.runtime.key_path.chmod(0o644)
        self.assertFalse(self.runtime.status()['generation_ready'])
        with self.assertRaisesRegex(api.ApiError,'UNSAFE_API_STORAGE'): self.register()
        self.assertEqual(len(self.calls),1)

    def test_real_candidate_worker_accepts_stop_and_discards_incomplete_text(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        candidate=api.candidate_module()
        evidence=self.runtime._evidence(KEY)
        for finish in ['STOP','MAX_TOKENS']:
            evidence=dict(evidence,evidence_id=str(uuid.uuid4()))
            raw=json.dumps({'candidates':[{'finishReason':finish,'content':{'role':'model','parts':[{'text':'OFFLINE_CANDIDATE_TEXT'}]}}],
                            'usageMetadata':{'totalTokenCount':4}}).encode()
            with patch.object(candidate,'_send_once',return_value=raw):
                output=api.worker_dispatch({'operation':'generate','api_key':KEY,'prompt':'Review a public plan.','evidence':evidence})
            if finish=='STOP':
                self.assertEqual(output['status'],'PASS_REAL_GEMINI_API_RESPONSE')
                self.assertEqual(output['response'],'OFFLINE_CANDIDATE_TEXT')
            else:
                self.assertEqual(output,{'status':'UNVERIFIED_GEMINI_API_RESULT'})

    def test_no_allowlisted_project_or_symlinked_key_is_accepted(self):
        self.runtime.allowed_project_id=None
        with self.assertRaisesRegex(api.ApiError,'API_PROJECT_NOT_CONFIGURED'): self.register()
        self.assertEqual(self.calls,[])
        self.runtime.allowed_project_id=PROJECT
        destination=self.root/'unrelated-private-file'
        destination.write_text(KEY)
        self.runtime.key_path.symlink_to(destination)
        with self.assertRaisesRegex(api.ApiError,'UNSAFE_API_STORAGE'): self.register()
        self.assertEqual(destination.read_text(),KEY)
        self.assertEqual(self.calls,[])

    def test_prepare_rejects_unverified_bindings_types_expiry_and_public_refs(self):
        self.register()
        invalid=[{'project_id':'different-project'},{'remaining_requests':True},{'remaining_requests':0},
                 {'remaining_requests':1000001},{'observed_at':(datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat()},
                 {'observed_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()},
                 {'quota_day_pacific':'2000-01-01'},
                 {'evidence_refs':{field:'https://public.invalid/evidence' for field in self.evidence()['evidence_refs']}}]
        for change in invalid:
            with self.subTest(change=change),self.assertRaises(api.ApiError):
                self.runtime.prepare(ACTOR,self.evidence(**change))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.runtime.status()['free_evidence_status'],'MISSING')

    def test_one_evidence_attempt_and_same_request_are_durable_across_restart(self):
        self.register()
        evidence=self.evidence()
        self.runtime.prepare(ACTOR,evidence)
        self.assertTrue(self.runtime.status()['generation_ready'])
        first=self.runtime.review(ACTOR,'request-offline-001','Review this public plan.')
        self.assertEqual(first['status'],'PASS_REAL_GEMINI_API_RESPONSE')
        restarted=api.ApiRuntime(self.adapter,self.owner,allowed_project_id=PROJECT,runner=self.runtime.runner)
        self.assertEqual(restarted.review(ACTOR,'request-offline-001','Review this public plan.'),first)
        with self.assertRaisesRegex(api.ApiError,'BUDGET_CONSUMED'):
            restarted.review(ACTOR,'request-offline-002','Review another plan.')
        with self.assertRaisesRegex(api.ApiError,'BUDGET_CONSUMED'):
            restarted.prepare(ACTOR,evidence)
        refreshed=dict(evidence,observed_at=datetime.now(timezone.utc).isoformat(),remaining_requests=2)
        with self.assertRaisesRegex(api.ApiError,'BUDGET_CONSUMED'):
            restarted.prepare(ACTOR,refreshed)
        self.assertEqual(len(self.calls),2)
        status=restarted.status()
        self.assertEqual(status['free_evidence_status'],'CONSUMED')
        self.assertFalse(status['generation_ready'])
        self.assertEqual(status['last_result_status'],'PASS_REAL_GEMINI_API_RESPONSE')
        self.assertIsNotNone(status['last_response_at'])
        self.assertNotIn('OFFLINE_MODEL_RESPONSE',json.dumps(status))

    def test_concurrent_requests_cannot_double_spend_one_evidence(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        started,release=threading.Event(),threading.Event()
        previous=self.runtime.runner
        def held(payload):
            started.set()
            release.wait(timeout=3)
            return previous(payload)
        self.runtime.runner=held
        with ThreadPoolExecutor(max_workers=2) as pool:
            future=pool.submit(self.runtime.review,ACTOR,'request-offline-001','Review A.')
            self.assertTrue(started.wait(timeout=2))
            with self.assertRaises(api.ApiError): self.runtime.review(ACTOR,'request-offline-002','Review B.')
            self.assertFalse(self.runtime.status()['generation_ready'])
            release.set()
            self.assertEqual(future.result()['status'],'PASS_REAL_GEMINI_API_RESPONSE')
        self.assertEqual(len(self.calls),2)

    def test_incomplete_timeout_and_secret_output_consume_without_success_or_retry(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        self.worker_result['finish_reason']='MAX_TOKENS'
        self.worker_result['response']='sensitive-'+KEY
        result=self.runtime.review(ACTOR,'request-offline-001','Review this public plan.')
        self.assertEqual(result['status'],'UNVERIFIED_GEMINI_API_RESULT')
        self.assertIsNone(result['response'])
        self.assertFalse(result['automatic_retry'])
        self.assertIsNone(self.runtime.status()['last_response_at'])
        self.assertEqual(self.runtime.review(ACTOR,'request-offline-001','Review this public plan.'),result)
        self.assertEqual(len(self.calls),2)
        self.assertNotIn(KEY,json.dumps(result))

    def test_status_never_starts_metadata_or_generation(self):
        self.assertFalse(self.runtime.status()['configured'])
        self.assertEqual(self.calls,[])
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        self.runtime.runner=lambda payload: (_ for _ in ()).throw(AssertionError('status made network call'))
        for _ in range(3): self.assertTrue(self.runtime.status()['generation_ready'])

    def test_status_checks_metadata_without_reading_private_key_contents(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        original_read=self.runtime._read
        def noncredential_read(name):
            self.assertNotEqual(name,'api-key','status read private key contents')
            return original_read(name)
        with (patch.object(self.runtime,'_key',side_effect=AssertionError('status called _key')),
              patch.object(self.runtime,'_read',side_effect=noncredential_read)):
            status=self.runtime.status()
        self.assertTrue(status['configured'])
        self.assertTrue(status['generation_ready'])
        self.assertIsNotNone(status['auth_verified_at'])

    def test_metadata_only_status_cannot_bypass_real_key_binding_at_execution(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        self.runtime.key_path.write_text('offline-different-api-key-0000000000002')
        self.assertTrue(self.runtime.status()['generation_ready'])
        with self.assertRaisesRegex(api.ApiError,'KEY_AUTH_UNVERIFIED'):
            self.runtime.review(ACTOR,'request-offline-001','Review this public plan.')
        self.assertEqual(len(self.calls),1)

    def test_unsafe_metadata_clears_authentication_and_readiness(self):
        self.register()
        self.runtime.prepare(ACTOR,self.evidence())
        (self.runtime.root/'operator-evidence.json').chmod(0o644)
        status=self.runtime.status()
        self.assertEqual(status['status'],'BLOCKED_API_STORAGE')
        self.assertIsNone(status['auth_verified_at'])
        self.assertFalse(status['generation_ready'])

    def test_fifo_key_is_rejected_without_blocking_status(self):
        self.register()
        self.runtime.key_path.unlink()
        os.mkfifo(self.runtime.key_path,0o600)
        done=threading.Event()
        results=[]
        def poll():
            try: results.append(self.runtime.status())
            finally: done.set()
        thread=threading.Thread(target=poll,daemon=True)
        thread.start()
        completed=done.wait(timeout=0.3)
        if not completed:
            descriptor=os.open(self.runtime.key_path,os.O_WRONLY|os.O_NONBLOCK)
            os.close(descriptor)
        thread.join(timeout=1)
        self.assertTrue(completed,'status blocked opening a nonregular key file')
        self.assertEqual(results[0]['status'],'BLOCKED_API_STORAGE')


class ProcessAndMetadataTests(unittest.TestCase):
    def setUp(self): self.assertIsNotNone(api,'API runtime is not implemented')

    def metadata_fixture(self,*,status=200,body=None,headers=None,error=None):
        raw=(json.dumps(body).encode() if not isinstance(body,bytes) else body)
        class Response:
            def __init__(self): self.status=status
            def getheader(self,name,default=None): return (headers or {}).get(name,default)
            def read(self,limit): return raw[:limit]
        class Connection:
            def __init__(self,*args,**kwargs): pass
            def set_debuglevel(self,value): pass
            def request(self,*args,**kwargs):
                if error is not None: raise error
            def getresponse(self): return Response()
            def close(self): pass
        with patch('api_runtime.http.client.HTTPSConnection',Connection):
            return api.metadata_once(KEY)

    def test_metadata_http_statuses_are_static_and_preserve_only_numeric_status(self):
        cases=[(401,'HTTP_UNAUTHENTICATED'),(403,'HTTP_FORBIDDEN'),(404,'MODEL_NOT_FOUND'),
               (429,'RATE_LIMITED'),(500,'PROVIDER_UNAVAILABLE'),(503,'PROVIDER_UNAVAILABLE'),
               (302,'REDIRECT_REJECTED')]
        for status,code in cases:
            with self.subTest(status=status):
                result=self.metadata_fixture(status=status,body={'error':{'message':KEY,'account':'private-account'}})
                self.assertEqual(result,{'status':'API_METADATA_'+code,'provider_http_status':status})
                self.assertNotIn(KEY,json.dumps(result))

    def test_metadata_error_info_reasons_are_exactly_allowlisted(self):
        cases=[(401,'ACCESS_TOKEN_TYPE_UNSUPPORTED','AUTH_TYPE_UNSUPPORTED'),
               (400,'API_KEY_INVALID','KEY_INVALID'),(403,'SERVICE_DISABLED','SERVICE_DISABLED'),
               *[(403,reason,'KEY_RESTRICTED') for reason in ['API_KEY_SERVICE_BLOCKED','HTTP_REFERRER_BLOCKED',
                 'IP_ADDRESS_BLOCKED','ANDROID_APP_BLOCKED','IOS_APP_BLOCKED',
                 'API_KEY_HTTP_REFERRER_BLOCKED','API_KEY_IP_ADDRESS_BLOCKED',
                 'API_KEY_ANDROID_APP_BLOCKED','API_KEY_IOS_APP_BLOCKED']]]
        for status,reason,code in cases:
            with self.subTest(reason=reason):
                body={'error':{'message':KEY,'details':[{'@type':'type.googleapis.com/google.rpc.ErrorInfo',
                      'domain':'googleapis.com','reason':reason,'metadata':{'account':KEY,'consumer':KEY}}]}}
                self.assertEqual(self.metadata_fixture(status=status,body=body),
                                 {'status':'API_METADATA_'+code,'provider_http_status':status})
        body={'error':{'details':[{'@type':'untrusted-type','reason':'ACCESS_TOKEN_TYPE_UNSUPPORTED'}]}}
        self.assertEqual(self.metadata_fixture(status=401,body=body),
                         {'status':'API_METADATA_HTTP_UNAUTHENTICATED','provider_http_status':401})
        body={'error':{'details':[{'@type':'type.googleapis.com/google.rpc.ErrorInfo',
              'domain':'untrusted.invalid','reason':'ACCESS_TOKEN_TYPE_UNSUPPORTED'}]}}
        self.assertEqual(self.metadata_fixture(status=401,body=body),
                         {'status':'API_METADATA_HTTP_UNAUTHENTICATED','provider_http_status':401})

    def test_metadata_invalid_body_model_method_and_transport_failures_are_distinct(self):
        cases=[(b'not JSON '+KEY.encode(),'INVALID_RESPONSE'),([], 'INVALID_RESPONSE'),
               ({'name':'models/wrong-model','supportedGenerationMethods':['generateContent']},'MODEL_MISMATCH'),
               ({'name':'models/'+MODEL,'supportedGenerationMethods':['countTokens']},'METHOD_UNAVAILABLE')]
        for body,code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.metadata_fixture(body=body),{'status':'API_METADATA_'+code,'provider_http_status':200})
        for error,code in [(TimeoutError(KEY),'TIMEOUT'),(ssl.SSLError(KEY),'TLS_ERROR'),(OSError(KEY),'NETWORK_ERROR')]:
            with self.subTest(code=code):
                self.assertEqual(self.metadata_fixture(error=error),{'status':'API_METADATA_'+code,'provider_http_status':None})
        self.assertEqual(self.metadata_fixture(body=b'x'*65537),{'status':'API_METADATA_INVALID_RESPONSE','provider_http_status':200})

    def test_process_receives_secrets_only_through_stdin_and_scrubs_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'offline-worker.py'
            script.write_text('import json,os,sys\np=json.load(sys.stdin)\n'
                              'assert p["api_key"] not in " ".join(sys.argv)\n'
                              'assert "GEMINI_API_KEY" not in os.environ\n'
                              'assert "SSLKEYLOGFILE" not in os.environ\n'
                              'print(json.dumps({"status":"API_METADATA_AUTHENTICATED"}))\n')
            with patch.dict(os.environ,{'GEMINI_API_KEY':KEY,'SSLKEYLOGFILE':'/unused/keylog'}):
                result=api.run_child({'operation':'metadata','api_key':KEY},command=[sys.executable,str(script)])
            self.assertEqual(result,{'status':'API_METADATA_AUTHENTICATED'})

    def test_process_deadline_and_output_limits_kill_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'offline-worker.py'
            pid=Path(folder)/'pid'
            script.write_text('import os,pathlib,time\npathlib.Path('+repr(str(pid))+').write_text(str(os.getpid()))\ntime.sleep(10)\n')
            start=time.monotonic()
            result=api.run_child({'operation':'metadata','api_key':KEY},command=[sys.executable,str(script)],deadline=0.15)
            self.assertLess(time.monotonic()-start,2)
            self.assertEqual(result,{'status':'API_METADATA_TIMEOUT','provider_http_status':None})
            with self.assertRaises(ProcessLookupError): os.kill(int(pid.read_text()),0)
            script.write_text('print("x"*70000)\n')
            self.assertEqual(api.run_child({'operation':'metadata','api_key':KEY},command=[sys.executable,str(script)]),
                             {'status':'API_METADATA_WORKER_UNVERIFIED','provider_http_status':None})
            script.write_text('import sys\nsys.exit(3)\n')
            self.assertEqual(api.run_child({'operation':'metadata','api_key':KEY},command=[sys.executable,str(script)]),
                             {'status':'API_METADATA_WORKER_UNVERIFIED','provider_http_status':None})

    def test_metadata_has_one_fixed_direct_tls_get_and_no_raw_error_output(self):
        seen=[]
        class Response:
            status=200
            def getheader(self,name,default=None): return default
            def read(self,limit):
                return json.dumps({'name':'models/'+MODEL,'supportedGenerationMethods':['generateContent']}).encode()
        class Connection:
            def __init__(self,host,**kwargs):
                seen.append((host,kwargs))
                self.context=kwargs['context']
            def set_debuglevel(self,value): self.debug=value
            def request(self,*args,**kwargs): seen.append((args,kwargs))
            def getresponse(self): return Response()
            def close(self): pass
        with patch('api_runtime.http.client.HTTPSConnection',Connection):
            self.assertEqual(api.metadata_once(KEY),{'status':'API_METADATA_AUTHENTICATED'})
            self.assertEqual(api.metadata_once(AQ_KEY),{'status':'API_METADATA_AUTHENTICATED'})
        self.assertEqual(seen[0][0],'generativelanguage.googleapis.com')
        self.assertTrue(seen[0][1]['context'].check_hostname)
        self.assertEqual(seen[1][0],('GET','/v1beta/models/gemini-3.5-flash-lite'))
        self.assertEqual(seen[1][1]['headers']['x-goog-api-key'],KEY)
        self.assertEqual(seen[3][1]['headers']['x-goog-api-key'],AQ_KEY)
        Response.status=302
        with patch('api_runtime.http.client.HTTPSConnection',Connection):
            self.assertEqual(api.metadata_once(KEY),{'status':'API_METADATA_REDIRECT_REJECTED','provider_http_status':302})


if __name__=='__main__': unittest.main()
