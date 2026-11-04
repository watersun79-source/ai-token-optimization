"""Offline loopback/process-double checks. No Google calls or real credentials."""
import dataclasses
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'gemini-real-mcp'))
from adapter import Config, Blocked
from server import Server
from http_server import (HTTPServer, Handler, Runtime, RequestError, AuthManager,
                         ManualAuthSession, valid_initial_auth_url, make_runtime,
                         OFFICIAL_CLI_OAUTH_CLIENT_ID, probe_cli_auth, OwnerBinding)

KEY = 'fixture-only-bridge-key-not-a-user-secret-0001'
ACTOR = 'site-scoped-test-user'
URL = ('https://accounts.google.com/o/oauth2/v2/auth?'
       'redirect_uri=https%3A%2F%2Fcodeassist.google.com%2Fauthcode&'
       'response_type=code&code_challenge_method=S256&'
       'client_id=' + OFFICIAL_CLI_OAUTH_CLIENT_ID + '&'
       'code_challenge=' + 'a' * 43 + '&state=' + 'b' * 64)


class StubAdapter:
    def __init__(self, root):
        self.config = Config(cli=Path('/unused/official-gemini'), state_dir=root,
                             cli_home=root / 'cli-home')
        self.calls = 0
        self.review_ids = []

    def status(self):
        self.calls += 1
        return {'status': 'OFFLINE_TEST_ADAPTER', 'model_called': False}

    def review(self, request_id, prompt):
        self.review_ids.append(request_id)
        raise Blocked('BLOCKED_VERIFICATION_GATE_MISSING')

    def _system_controls(self):
        return {'status': 'OFFLINE_TEST_ONLY'}


class FakeSession:
    def __init__(self, actor, cli, root, callback, **kwargs):
        self.actor, self.id = actor, 'c' * 48
        self.state = 'WAITING_FOR_AUTH_CODE'
        self.submitted = False
        self.last_verified_at = None
        self._lock = threading.RLock()

    def public(self):
        return {'session_id': self.id, 'status': self.state,
                'authorization_url': URL, 'authenticated': False}

    def finish(self, code):
        if self.submitted:
            raise RequestError(409, 'AUTH_NOT_WAITING')
        self.submitted = True
        self.state = 'VERIFYING'
        return {'session_id': self.id, 'status': self.state, 'authenticated': False}


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.adapter = StubAdapter(Path(self.tmp.name))
        self.runtime = Runtime(self.adapter, Server, KEY, FakeSession)
        self.httpd = HTTPServer(('127.0.0.1', 0), Handler)
        self.httpd.runtime = self.runtime
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, path, body=None, auth=True, actor=ACTOR, method='POST', headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=3)
        h = {'Content-Type': 'application/json'}
        if auth:
            h['Authorization'] = 'Bearer ' + KEY
        if actor is not None:
            h['X-Bridge-Actor'] = actor
        h.update(headers or {})
        c.request(method, path, None if body is None else json.dumps(body), h)
        r = c.getresponse()
        data, status = r.read(), r.status
        c.close()
        return status, json.loads(data)

    def test_health_only_public(self):
        self.assertEqual(self.request('/healthz', auth=False, method='GET')[0], 200)
        for path in ['/mcp', '/auth/start', '/auth/status', '/auth/finish', '/unknown']:
            self.assertEqual(self.request(path, {}, auth=False)[0], 401)
        self.assertEqual(self.adapter.calls, 0)

    def test_discover_and_initialize(self):
        _, discover = self.request('/mcp', {'jsonrpc':'2.0','id':1,'method':'server/discover'})
        self.assertEqual(discover['result']['supportedVersions'], ['2026-07-28'])
        _, init = self.request('/mcp', {'jsonrpc':'2.0','id':2,'method':'initialize','params':{'protocolVersion':'2026-07-28'}})
        self.assertEqual(init['result']['protocolVersion'], '2026-07-28')

    def test_real_server_metadata_and_status_path(self):
        _, tools = self.request('/mcp', {'jsonrpc':'2.0','id':1,'method':'tools/list'}, actor=None)
        self.assertEqual([t['name'] for t in tools['result']['tools']], ['gemini_status','gemini_review'])
        _, status = self.request('/mcp', {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'gemini_status','arguments':{}}}, actor=None)
        self.assertEqual(status['result']['structuredContent']['status'], 'OFFLINE_TEST_ADAPTER')
        self.assertEqual(self.adapter.calls, 1)

    def test_status_authentication_is_unknown_without_a_session(self):
        req={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'gemini_status','arguments':{}}}
        with patch.object(self.runtime.auth,'start',side_effect=AssertionError('must not start authentication')):
            _,reply=self.request('/mcp',req,actor=None)
        status=reply['result']['structuredContent']
        self.assertEqual(status.get('authentication'),{'status':'UNVERIFIED','authenticated':None,'last_verified_at':None})
        self.assertIsNotNone(datetime.fromisoformat(status['observed_at_utc']).tzinfo)
        self.assertEqual(json.loads(reply['result']['content'][0]['text']),status)
        self.assertIsNone(self.runtime.auth.session)

    def test_status_authentication_snapshot_never_exposes_auth_secrets(self):
        self.request('/auth/start',{})
        session=self.runtime.auth.session
        session.authorization_code='OFFLINE_CODE_MUST_NOT_APPEAR'
        session.access_token='OFFLINE_TOKEN_MUST_NOT_APPEAR'
        req={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'gemini_status','arguments':{}}}
        with patch.object(session,'public',side_effect=AssertionError('auth public includes sensitive flow data')):
            _,reply=self.request('/mcp',req,actor='another-user')
        status=reply['result']['structuredContent']
        self.assertEqual(status.get('authentication'),{'status':'WAITING_FOR_AUTH_CODE','authenticated':None,'last_verified_at':None})
        for forbidden in [session.id,URL,'OFFLINE_CODE_MUST_NOT_APPEAR','OFFLINE_TOKEN_MUST_NOT_APPEAR',ACTOR]:
            self.assertNotIn(forbidden,json.dumps(reply))

    def test_status_reports_only_a_timestamped_verified_authentication(self):
        self.request('/auth/start',{})
        session=self.runtime.auth.session
        session.state='CLI_AUTHENTICATED_QUOTA_UNVERIFIED'
        req={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'gemini_status','arguments':{}}}
        _,unverified=self.request('/mcp',req)
        self.assertIsNone(unverified['result']['structuredContent'].get('authentication',{}).get('authenticated'))
        session.last_verified_at='2026-11-04T00:00:00+00:00'
        _,verified=self.request('/mcp',req)
        self.assertEqual(verified['result']['structuredContent'].get('authentication'),{
            'status':'CLI_AUTHENTICATED_QUOTA_UNVERIFIED','authenticated':True,
            'last_verified_at':'2026-11-04T00:00:00+00:00'})
        session.state='AUTH_SESSION_EXPIRED'
        _,expired=self.request('/mcp',req)
        self.assertEqual(expired['result']['structuredContent']['authentication'],{
            'status':'AUTH_SESSION_EXPIRED','authenticated':None,'last_verified_at':None})

    def test_review_requires_actor_and_keeps_verification_gate(self):
        req = {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'gemini_review','arguments':{'request_id':'test-req-1','prompt':'hello'}}}
        self.assertEqual(self.request('/mcp', req, actor=None)[0], 400)
        self.assertEqual(self.request('/mcp', req)[0], 403)
        self.request('/auth/start', {})
        _, result = self.request('/mcp', req)
        self.assertTrue(result['result']['isError'])
        self.assertEqual(result['result']['structuredContent']['status'], 'BLOCKED_VERIFICATION_GATE_MISSING')
        self.assertEqual(self.adapter.review_ids, [hashlib.sha256((ACTOR + '\0test-req-1').encode()).hexdigest()])
        self.assertEqual(self.request('/mcp', req, actor='another-user')[0], 403)

    def test_auth_actor_binding_and_no_code_echo(self):
        _, start = self.request('/auth/start', {})
        sid = start['session_id']
        self.assertEqual(self.request('/auth/status', {'session_id':sid}, actor='another-user')[0], 403)
        self.assertEqual(self.request('/auth/start', {}, actor='another-user')[0], 403)
        code = 'fixture-auth-code-not-a-real-credential'
        status, result = self.request('/auth/finish', {'session_id':sid,'authorization_code':code})
        self.assertEqual(status, 200)
        self.assertNotIn(code, json.dumps(result))
        self.assertEqual(result['status'], 'VERIFYING')
        self.assertEqual(self.request('/auth/finish', {'session_id':sid,'authorization_code':code})[0], 409)

    def test_extra_auth_fields_and_query_code_rejected(self):
        self.assertEqual(self.request('/auth/start', {'actor':ACTOR})[0], 404)
        self.assertEqual(self.request('/auth/finish?authorization_code=not-used', {})[0], 404)
        self.assertEqual(self.request('/mcp', ['not','an','object'])[0], 400)

    def test_no_credential_fields_in_mcp_schema(self):
        _, tools = self.request('/mcp', {'jsonrpc':'2.0','id':1,'method':'tools/list'})
        content = json.dumps(tools['result']['tools'])
        self.assertNotIn('authorization_code', content)
        self.assertNotIn('access_token', content)
        self.assertNotIn(KEY, content)

    def test_unsupported_method_requires_auth(self):
        self.assertEqual(self.request('/mcp', auth=False, method='OPTIONS')[0], 401)
        self.assertEqual(self.request('/mcp', method='OPTIONS')[0], 405)

    def test_owner_binding_persists_and_other_actor_cannot_activate_home(self):
        self.request('/auth/start', {})
        owner = OwnerBinding(self.adapter.config.state_dir)
        self.assertEqual(owner.require(ACTOR), ACTOR)
        self.assertEqual(owner.path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(RequestError) as cm:
            self.runtime.activate_home('another-user', Path(self.tmp.name) / 'auth-attempts' / 'new')
        self.assertEqual(cm.exception.code, 'ACTOR_NOT_OWNER')

    def test_auth_start_requires_system_controls_before_binding(self):
        self.adapter._system_controls = lambda: (_ for _ in ()).throw(Blocked('fixture-control-error'))
        status, result = self.request('/auth/start', {})
        self.assertEqual(status, 503)
        self.assertEqual(result['error'], 'BLOCKED_AUTH_SYSTEM_CONTROLS')
        self.assertIsNone(self.runtime.owner.actor)

    def test_new_authentication_does_not_inherit_existing_quota_gate(self):
        self.request('/auth/start', {})
        self.adapter.config = dataclasses.replace(self.adapter.config, gate_file=Path('/unused/older-proof'))
        home = self.adapter.config.state_dir / 'auth-attempts' / 'new-private-home'
        home.mkdir(mode=0o700)
        self.runtime.activate_home(ACTOR, home)
        self.assertIsNone(self.adapter.config.gate_file)
        self.assertEqual(self.adapter.config.cli_home, home)


class SessionTests(unittest.TestCase):
    def session(self):
        s = ManualAuthSession.__new__(ManualAuthSession)
        s.actor, s.id, s.deadline = ACTOR, 'a' * 48, time.monotonic() + 300
        s.state, s.url, s.submitted = 'STARTING', None, False
        s.last_verified_at = None
        s._buffer, s._trust_handled, s._google_handled = bytearray(), False, False
        s._output_count = 0
        s._lock, s._stopped = threading.RLock(), threading.Event()
        s.home = Path('/unused/private-cli-home')
        s.controls, s.callbacks = [], []
        s._write_control = s.controls.append
        s._on_success = s.callbacks.append
        return s

    def test_official_url_only(self):
        self.assertTrue(valid_initial_auth_url(URL))
        self.assertFalse(valid_initial_auth_url(URL.replace('accounts.google.com', 'evil.invalid')))
        self.assertFalse(valid_initial_auth_url(URL.replace('codeassist.google.com%2Fauthcode', 'evil.invalid%2Fcollect')))
        self.assertFalse(valid_initial_auth_url(URL + '&access_token=fixture'))
        self.assertFalse(valid_initial_auth_url(URL.replace(OFFICIAL_CLI_OAUTH_CLIENT_ID, 'unapproved-client')))

    def test_prelude_state_machine_controls_are_fixed(self):
        s = self.session()
        s._observe(b"Do you trust the files in this folder? 3. Don't trust")
        self.assertEqual(s.controls, [b'\x1b[B\x1b[B\r'])
        s._observe(b'How would you like to authenticate? 1. Sign in with Google')
        self.assertEqual(s.controls[-1], b'\r')
        s._observe(URL.encode() + b'\nEnter the authorization code: ')
        self.assertEqual(s.state, 'WAITING_FOR_AUTH_CODE')
        self.assertEqual(s.public()['authorization_url'], URL)
        self.assertEqual(s._buffer, b'')

    def test_post_code_success_text_is_not_authentication_evidence(self):
        s = self.session()
        s.submitted, s.state = True, 'VERIFYING'
        s._observe(b'Authentication suc')
        s._observe(b'ceeded\nprivate-account-data-ignored')
        self.assertEqual(s.state, 'VERIFYING')
        self.assertFalse(s.public()['authenticated'])
        self.assertNotIn('authorization_url', s.public())
        self.assertEqual(s._buffer, b'')
        self.assertEqual(s.callbacks, [])

    def test_post_code_output_limit_fails_closed(self):
        s = self.session()
        s.submitted, s.state = True, 'VERIFYING'
        s._observe(b'x' * 65_537)
        self.assertEqual(s.state, 'BLOCKED_AUTH_OUTPUT_LIMIT')
        self.assertEqual(s._buffer, b'')

    def test_expired_session_does_not_accept_code(self):
        s = self.session()
        s.state, s.deadline = 'WAITING_FOR_AUTH_CODE', time.monotonic() - 1
        with self.assertRaises(RequestError) as cm:
            s.finish('fixture-code-not-a-real-credential')
        self.assertEqual(cm.exception.code, 'AUTH_SESSION_EXPIRED')
        self.assertFalse(s.submitted)

    def test_no_key_no_start(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            make_runtime()

    def test_verified_acp_probe_calls_actor_bound_callback(self):
        s = self.session()
        s.submitted, s.state = True, 'VERIFYING'
        s.cli, s.work = Path('/unused/official-cli'), Path('/unused/empty-work')
        s.system_settings_path = Path('/etc/gemini-cli/settings.json')
        calls = []
        s.probe = lambda *a, **kw: calls.append((a,kw)) or True
        s._on_success = lambda actor,home: s.callbacks.append((actor,home))
        with patch.object(s._stopped, 'wait', return_value=False):
            s._verify_authentication()
        self.assertEqual(s.state, 'CLI_AUTHENTICATED_QUOTA_UNVERIFIED')
        self.assertEqual(s.callbacks, [(ACTOR,s.home)])
        self.assertEqual(len(calls), 1)
        self.assertFalse(s.public()['model_called'])
        self.assertEqual(s.public()['quota'], 'UNVERIFIED')
        self.assertIsNotNone(s.last_verified_at)
        self.assertIsNotNone(datetime.fromisoformat(s.last_verified_at).tzinfo)

    def test_failed_acp_probes_are_bounded_to_three(self):
        s = self.session()
        s.submitted, s.state = True, 'VERIFYING'
        s.cli, s.work = Path('/unused/official-cli'), Path('/unused/empty-work')
        s.system_settings_path = Path('/etc/gemini-cli/settings.json')
        calls=[]
        s.probe = lambda *a, **kw: calls.append(1) or False
        with patch.object(s._stopped, 'wait', return_value=False):
            s._verify_authentication()
        self.assertEqual(len(calls), 3)
        self.assertEqual(s.state, 'CLI_AUTH_RESULT_UNVERIFIED')
        self.assertEqual(s.callbacks, [])
        self.assertIsNone(s.last_verified_at)


class ACPProbeTests(unittest.TestCase):
    def fixture(self, root, behavior='success'):
        cli = root / 'fixture-cli'
        source = '''#!/usr/bin/env python3
import json,sys,time
from pathlib import Path
for line in sys.stdin:
    request=json.loads(line)
    with Path('probe-methods.jsonl').open('a') as f:
        f.write(json.dumps({'method':request['method'],'params':request.get('params',{})})+'\\n')
    if request['id']==1:
        result={'protocolVersion':1}
        reply={'jsonrpc':'2.0','id':1,'result':result}
    else:
        BEHAVIOR
    print(json.dumps(reply),flush=True)
'''
        if behavior == 'success':
            action = "reply={'jsonrpc':'2.0','id':2,'result':{'sessionId':'fixture-session-id'}}"
        elif behavior == 'unauthenticated':
            action = "reply={'jsonrpc':'2.0','id':2,'error':{'code':-32000,'message':'fixture sensitive message must not escape'}}"
        elif behavior == 'timeout':
            action = "time.sleep(10); reply={'jsonrpc':'2.0','id':2,'result':{'sessionId':'late'}}"
        else:
            action = "print('x'*70000,flush=True); time.sleep(10); reply={}"
        cli.write_text(source.replace('BEHAVIOR', action))
        cli.chmod(0o700)
        return cli

    def test_probe_sends_only_initialize_and_session_new(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cli=self.fixture(root)
            self.assertTrue(probe_cli_auth(cli, root, root, root/'unused-controls', timeout=2))
            calls=[json.loads(line) for line in (root/'probe-methods.jsonl').read_text().splitlines()]
            self.assertEqual([c['method'] for c in calls], ['initialize','session/new'])
            self.assertEqual(calls[1]['params'], {'cwd':str(root),'mcpServers':[]})
            self.assertNotIn('session/prompt', (root/'probe-methods.jsonl').read_text())

    def test_unauthenticated_probe_is_false_not_response_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertIs(probe_cli_auth(self.fixture(root,'unauthenticated'), root, root, root/'unused-controls', timeout=2), False)

    def test_probe_timeout_and_output_limit_fail_closed(self):
        for behavior in ('timeout','overflow'):
            with self.subTest(behavior=behavior), tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                self.assertFalse(probe_cli_auth(self.fixture(root,behavior), root, root, root/'unused-controls', timeout=0.3))


if __name__ == '__main__':
    unittest.main()
