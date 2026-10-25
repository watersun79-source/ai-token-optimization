"""Worker execution and HTTP integration tests; never use a live provider API."""
import io
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from real_gateway import execute_role, run_message, make_handler, github_get, REPO, MEMORY_PATH


class GatewayTests(unittest.TestCase):
    def test_normal_chat_skips_workers(self):
        x=run_message('안녕')
        self.assertEqual(x['route'],'DIRECT_CHAT')
        self.assertEqual(x['workers'],[])

    def test_syntax_error_is_executed_as_ast_check(self):
        x=run_message('에러 고쳐',code='print(')
        self.assertEqual(x['status'],'DONE')
        self.assertEqual(x['selected_roles'],['ai-auto-debug'])
        self.assertFalse(x['workers'][0]['evidence']['syntax_valid'])
        self.assertFalse(x['workers'][0]['evidence']['executed_user_code'])

    def test_actual_bounded_syntax_repair(self):
        report = run_message("에러 고쳐", code="print(")
        evidence = report["workers"][0]["evidence"]
        self.assertTrue(evidence["repair_applied"])
        self.assertEqual(evidence["fixed_source"], "print()")
        self.assertTrue(evidence["syntax_valid_after"])
        self.assertNotEqual(evidence["source_sha256"], evidence["fixed_sha256"])
        self.assertFalse(evidence["executed_user_code"])

    def test_unsafe_or_ambiguous_syntax_is_not_repaired(self):
        for source in ["if True", "print((1", "print(\\n1"]:
            report = run_message("에러 고쳐", code=source)
            evidence = report["workers"][0]["evidence"]
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["workers"][0]["status"], "BLOCKED")
            self.assertFalse(evidence["repair_applied"])
            self.assertNotIn("fixed_source", evidence)

    def test_wont_execute_untrusted_source(self):
        code='__import__("os").system("touch /tmp/should_not_exist_AI_GATEWAY")'
        x=run_message('에러 고쳐',code=code)
        self.assertTrue(x['workers'][0]['evidence']['syntax_valid'])
        self.assertFalse(Path('/tmp/should_not_exist_AI_GATEWAY').exists())

    def test_parallel_workers_actual(self):
        x=run_message('예약 ai 로그 확인하고 오류 수정',code='x = 1')
        self.assertEqual(len(x['workers']),2)
        self.assertEqual(x['workers'][0]['status'],'UNVERIFIED')
        self.assertEqual(x['workers'][1]['status'],'DONE')
        self.assertEqual(x['status'],'PARTIAL')

    def test_no_model_calls_or_writes(self):
        x=run_message('오류 고쳐 토큰 최적화',code='def f(): pass')
        self.assertEqual(x['external_llm_calls'],0)
        self.assertEqual(x['production_writes'],0)
        self.assertFalse(x['chatgpt_composer_hook'])

    def test_secret_detection_does_not_echo(self):
        secret='sk-'+ 'a'*27
        r=execute_role('ai-cost-security','비용 검토',code='api_key='+secret)
        self.assertTrue(r['evidence']['suspected_secret_in_code'])
        self.assertNotIn(secret,json.dumps(r))

    def test_optimization_actual_dedup(self):
        r=execute_role('ai-optimization','a. a. b.')
        self.assertEqual(r['evidence']['text_segments'],3)
        self.assertEqual(r['evidence']['unique_text_segments'],2)
        self.assertIsNone(r['evidence']['estimated_tokens'])

    def test_optimization_worker_actually_compacts_and_returns_receipt(self):
        message = "토큰 최적화\n반복\n반복\n유일"
        report = run_message(message)
        self.assertEqual(report["status"], "DONE")
        evidence = report["workers"][0]["evidence"]
        self.assertEqual(evidence["optimized_text"], "토큰 최적화\n반복\n유일")
        self.assertEqual(evidence["duplicate_lines_removed"], 1)
        self.assertGreater(evidence["bytes_saved"], 0)
        self.assertNotEqual(evidence["input_sha256"], evidence["output_sha256"])
        self.assertEqual(evidence["external_model_calls"], 0)

    def test_optimization_worker_blocks_secret_without_echo(self):
        secret = "github_pat_" + "x" * 30
        report = run_message("토큰 최적화\n" + secret)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["workers"][0]["status"], "BLOCKED")
        self.assertNotIn(secret, json.dumps(report))

    def test_natural_language_compression_dispatch_executes(self):
        report = run_message("압축 실행\n중복\n중복")
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["workers"][0]["role"], "ai-optimization")
        self.assertEqual(report["workers"][0]["evidence"]["duplicate_lines_removed"], 1)

    def test_real_gateway_cli_natural_language_command(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "gateway" / "real_gateway.py"),
             "--message", chr(10).join(["압축 실행", "중복", "중복", "유일"])],
            capture_output=True, text=True, timeout=8, check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["selected_roles"], ["ai-optimization"])
        evidence = report["workers"][0]["evidence"]
        self.assertEqual(evidence["optimized_text"], chr(10).join(["압축 실행", "중복", "유일"]))
        self.assertEqual(evidence["duplicate_lines_removed"], 1)
        self.assertGreater(evidence["bytes_saved"], 0)

    def test_explicit_optimization_command_executes(self):
        report = run_message("최적화 실행\n같음\n같음")
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["selected_roles"], ["ai-optimization"])
        self.assertEqual(report["workers"][0]["evidence"]["duplicate_lines_removed"], 1)

    def test_explicit_optimization_cli_receipt(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "gateway" / "real_gateway.py"),
             "--message", chr(10).join(["최적화 실행", "반복", "반복", "유일"])],
            capture_output=True, text=True, timeout=8, check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["selected_roles"], ["ai-optimization"])
        evidence = report["workers"][0]["evidence"]
        self.assertEqual(evidence["optimized_text"], chr(10).join(["최적화 실행", "반복", "유일"]))
        self.assertEqual(evidence["duplicate_lines_removed"], 1)
        self.assertNotEqual(evidence["input_sha256"], evidence["output_sha256"])

    def test_prompt_compression_request_executes(self):
        report = run_message("프롬프트 압축\n같은 줄\n같은 줄")
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["selected_roles"], ["ai-optimization"])
        self.assertEqual(report["workers"][0]["evidence"]["duplicate_lines_removed"], 1)

    def test_automation_plan_not_flow_run(self):
        r=execute_role('ai-automation-design','워크플로 구성')
        self.assertEqual(r['status'],'DONE')
        self.assertEqual(r['evidence']['operational_flows_modified'],0)

    def test_audit_not_falsely_verified(self):
        r=execute_role('ai-scheduled-audit','예약 AI')
        self.assertEqual(r['status'],'UNVERIFIED')

    def test_cross_model_blocked_without_real_models(self):
        r=execute_role('ai-cross-model-review','gemini claude')
        self.assertEqual(r['status'],'BLOCKED')

    def test_missing_code_needs_input(self):
        r=run_message('에러 고쳐')
        self.assertEqual(r['workers'][0]['status'],'NEEDS_INPUT')
        self.assertEqual(r['status'],'BLOCKED')

    def test_invalid_payloads(self):
        for x in ['',[],None,'a'*4001]:
            with self.assertRaises(ValueError):run_message(x)
        with self.assertRaises(ValueError):run_message('에러 고쳐',code='x'*10001)

    def test_network_default_blocked(self):
        for r in ['ai-memory-recovery','ai-code-verification','ai-open-source-research','ai-github-management']:
            self.assertEqual(execute_role(r,'test')['status'],'BLOCKED')

    def test_read_only_memory_success_with_mock(self):
        def stub(path):
            self.assertIn('contents/',path)
            return {'sha':'verified_mock_sha','path':MEMORY_PATH,'html_url':'https://github.com/x'}
        r=execute_role('ai-memory-recovery','기억 복원',network=True,fetch=stub)
        self.assertEqual(r['evidence']['content_sha'],'verified_mock_sha')

    def test_ci_metadata_is_only_partial(self):
        observed = []
        head = 'a'*40
        def stub(path):
            observed.append(path)
            if '/branches/' in path: return {'commit': {'sha':head}}
            return {'workflow_runs':[{'id':42,'conclusion':'success','status':'completed','head_sha':head}]}
        r=execute_role('ai-code-verification','CI 확인',network=True,fetch=stub)
        self.assertEqual(r['status'],'PARTIAL')
        self.assertEqual(r['evidence']['id'],42)
        self.assertTrue(r['evidence']['head_match'])
        self.assertEqual(observed, [
            '/repos/'+REPO+'/branches/ai%2Fr16-v81-fast-full-ci-20261024',
            '/repos/'+REPO+'/actions/runs?branch=ai%2Fr16-v81-fast-full-ci-20261024&per_page=1'])

    def test_ci_stale_success_must_not_verify_current_head(self):
        def stub(path):
            if '/branches/' in path: return {'commit': {'sha':'a'*40}}
            return {'workflow_runs':[{'id':43,'conclusion':'success','status':'completed','head_sha':'b'*40}]}
        r=execute_role('ai-code-verification','CI 확인',network=True,fetch=stub)
        self.assertEqual(r['status'],'UNVERIFIED')
        self.assertFalse(r['evidence']['head_match'])

    def test_ci_incomplete_or_failed_is_not_success(self):
        for state, conclusion, expected in [
            ('in_progress', None, 'UNVERIFIED'),
            ('completed', 'failure', 'FAIL'),
            ('completed', 'cancelled', 'FAIL'),
            ('completed', None, 'UNVERIFIED'),
        ]:
            with self.subTest(state=state, conclusion=conclusion):
                def stub(path):
                    if '/branches/' in path: return {'commit': {'sha':'a'*40}}
                    return {'workflow_runs':[{'id':44,'status':state,'conclusion':conclusion,'head_sha':'a'*40}]}
                r=execute_role('ai-code-verification','CI 확인',network=True,fetch=stub)
                self.assertEqual(r['status'],expected)

    def test_ci_missing_current_sha_fails_closed(self):
        r=execute_role('ai-code-verification','CI 확인',network=True,fetch=lambda _: {'commit': {'sha':'abc'}})
        self.assertEqual(r['status'],'UNVERIFIED')

    def test_repo_info_success(self):
        r=execute_role('ai-github-management','브랜치',network=True,fetch=lambda x:{'full_name':REPO,'default_branch':'main'})
        self.assertEqual(r['status'],'DONE')
        self.assertTrue(r['evidence']['read_only'])

    def test_research_metadata_success(self):
        paths=[]
        def mock_fetch(p):
            paths.append(p)
            return {'html_url':'https://github.com/a/b','license':{'spdx_id':'MIT'},'archived':False}
        r=execute_role('ai-open-source-research','오픈소스',network=True,fetch=mock_fetch)
        self.assertEqual(len(r['evidence']['projects']),3)
        self.assertEqual(len(paths),3)
        self.assertEqual(r['status'],'PARTIAL')

    def test_network_error_no_secret_trace(self):
        def fail(_):raise RuntimeError('secrets-should-not-leak')
        r=execute_role('ai-memory-recovery','기억 복원',network=True,fetch=fail)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertNotIn('secrets-should-not-leak',json.dumps(r))

    def test_github_url_allowlist(self):
        with self.assertRaises(ValueError): github_get('/repos/attacker/private')
        with self.assertRaises(ValueError): github_get('/repos/'+REPO+'/contents/../../../.env')
        with self.assertRaises(ValueError): github_get('/repos/'+REPO+'/actions/runs?per_page=100')
        with self.assertRaises(ValueError):
            github_get('/repos/'+REPO+'/actions/runs?branch=ai%2Ftop10-role-sandbox-2026-10-22&per_page=1')
        with self.assertRaises(ValueError): github_get('/repos/'+REPO+'/branches/main')

    def test_github_read_uses_no_token(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'{"full_name":"watersun79-source/ai-token-optimization"}'
        observed=[]
        def mock(req,timeout):
            observed.append((req.full_url,req.headers,timeout))
            return Resp()
        r=github_get('/repos/'+REPO,request_fn=mock)
        self.assertEqual(r['full_name'],REPO)
        self.assertNotIn('Authorization',observed[0][1])
        self.assertEqual(observed[0][2],7)

    def test_github_response_bound(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'x'*100001
        with self.assertRaises(ValueError):github_get('/repos/'+REPO,request_fn=lambda *a,**kw:Resp())


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler())
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
    def test_health_real_http(self):
        with urlopen(self.url+'/health',timeout=3) as r:
            self.assertTrue(json.load(r)['ok'])
    def test_chat_real_http_exec(self):
        payload=json.dumps({'message':'에러 고쳐','code':'print('}).encode()
        req=Request(self.url+'/api/chat',data=payload,headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=3) as r:
            d=json.load(r)
        self.assertEqual(d['workers'][0]['status'],'DONE')
        self.assertFalse(d['workers'][0]['evidence']['syntax_valid'])
    def test_real_http_optimization_compaction(self):
        payload=json.dumps({'message':'토큰 최적화\n중복\n중복'}).encode()
        req=Request(self.url+'/api/chat',data=payload,headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=3) as r:
            report=json.load(r)
        self.assertEqual(report['status'],'DONE')
        self.assertEqual(report['workers'][0]['evidence']['duplicate_lines_removed'],1)
        self.assertEqual(report['workers'][0]['evidence']['optimized_text'],'토큰 최적화\n중복')

    def test_index_real_http(self):
        with urlopen(self.url+'/',timeout=3) as r:
            self.assertIn('text/html',r.headers['Content-Type'])
            self.assertIn('Python',r.read().decode())
    def test_post_invalid_json(self):
        req=Request(self.url+'/api/chat',data=b'{bad',headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as ctx:urlopen(req,timeout=3)
        self.assertEqual(ctx.exception.code,400)
    def test_post_gigantic_refused(self):
        req=Request(self.url+'/api/chat',data=b'A'*18000,headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as ctx:urlopen(req,timeout=3)
        self.assertEqual(ctx.exception.code,400)
    def test_get_wrong_path(self):
        with self.assertRaises(HTTPError) as ctx:urlopen(self.url+'/secret',timeout=3)
        self.assertEqual(ctx.exception.code,404)


if __name__=='__main__':unittest.main()
