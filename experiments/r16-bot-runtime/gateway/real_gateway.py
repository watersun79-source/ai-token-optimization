"""Executable, read-only multi-worker gateway.

The HTTP chat interface triggers worker functions on every submitted message.
It is NOT a hook into the official ChatGPT iOS/web composer.
Provider generation API calls: NONE. Optional GitHub metadata is read-only.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import threading
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from auto_dispatch import dispatch
from task_executor import SECRET, QUOTED_SECRET, QUOTED_AUTH, compact

REPO = "watersun79-source/ai-token-optimization"
MEMORY_REF = "ai/continuation-readonly-audit-2026-10-18"
MEMORY_PATH = "docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md"
OSS_ALLOWLIST = {"langgraph":"langchain-ai/langgraph", "crewai":"crewAIInc/crewAI", "agent_framework":"microsoft/agent-framework"}
APPROVED_CI_WORKFLOWS = frozenset((
    ".github/workflows/r16-v81-guard-fast.yml",
    ".github/workflows/v81-fast-full-isolated.yml",
))
MAX_MESSAGE, MAX_CODE = 4000, 10000


def _contains_credential(source: str) -> bool:
    """Use every centralized secret signature before inspecting or echoing code."""
    return any(pattern.search(source) for pattern in (SECRET, QUOTED_SECRET, QUOTED_AUTH))


def github_get(path: str, *, request_fn: Callable[..., Any] = urlopen) -> dict:
    """Allowlist paths for trusted GitHub public REST reads; never send a token."""
    allowed = (
        rf"/repos/{re.escape(REPO)}/contents/{re.escape(MEMORY_PATH)}\?ref=ai%2Fcontinuation-readonly-audit-2026-10-18",
        rf"/repos/{re.escape(REPO)}/actions/runs\?branch=ai%2Fr16-v81-fast-full-ci-20261024&per_page=10",
        rf"/repos/{re.escape(REPO)}/branches/ai/r16-v81-fast-full-ci-20261024",
        rf"/repos/{re.escape(REPO)}",
    )
    oss_allowed = tuple(rf"/repos/{re.escape(repo)}" for repo in OSS_ALLOWLIST.values())
    if not any(re.fullmatch(p, path) for p in (*allowed, *oss_allowed)):
        raise ValueError("unapproved GitHub REST read path")
    req = Request("https://api.github.com" + path, headers={"Accept":"application/vnd.github+json", "User-Agent":"AI-ReadOnly-BotTeam/0.1"})
    with request_fn(req, timeout=7) as res:
        blob = res.read(100001)
    if len(blob) > 100000:
        raise ValueError("GitHub response too large")
    obj = json.loads(blob)
    if not isinstance(obj, dict):
        raise ValueError("GitHub response must be JSON object")
    return obj


def _result(role: str, status: str, *, evidence: dict | None = None, note: str = "") -> dict:
    return {"role": role, "status": status, "evidence": evidence or {}, "note": note}


def execute_role(role: str, message: str, *, code: str = "", network: bool = False,
                 fetch: Callable[[str], dict] = github_get) -> dict:
    """Perform a real bounded operation when possible, otherwise report blocked/unverified."""
    if role == "ai-auto-debug":
        if not code:
            return _result(role,"NEEDS_INPUT",note="Provide Python source separately to analyze; no code executed")
        # Do not return an auto-repaired source containing GitHub/API tokens.
        # Reuse the bounded worker's centralized credential detector.
        if _contains_credential(code):
            return _result(role,"BLOCKED",
                           evidence={"suspected_secret": True,
                                     "executed_user_code": False,
                                     "repair_applied": False},
                           note="Credential-like source refused; no source returned")
        try:
            ast.parse(code)
            return _result(role,"DONE",evidence={"syntax_valid":True,"source_sha256":sha256(code.encode()).hexdigest(),"executed_user_code":False})
        except SyntaxError as exc:
            evidence = {"syntax_valid":False,"line":exc.lineno,
                        "exception_type":"SyntaxError","executed_user_code":False,
                        "source_sha256":sha256(code.encode()).hexdigest(),
                        "repair_applied":False}
            # Only repair a uniquely identified missing final ')' on a print call.
            # Do not evaluate user source, touch files, or guess arbitrary syntax.
            if re.fullmatch(r"print\([^()\n]*", code):
                fixed = code + ")"
                try:
                    ast.parse(fixed)
                except SyntaxError:
                    pass
                else:
                    evidence.update({"repair_applied":True,"fixed_source":fixed,
                                     "fixed_sha256":sha256(fixed.encode()).hexdigest(),
                                     "syntax_valid_after":True})
            if evidence["repair_applied"]:
                return _result(role,"DONE",evidence=evidence,
                               note="Bounded AST-verified source repair; no user code executed or files modified")
            return _result(role,"BLOCKED",evidence=evidence,
                           note="SyntaxError detected; no safe repair applied; user code not executed")
    if role == "ai-cost-security":
        unsafe = _contains_credential(code)
        return _result(role,"DONE",evidence={"suspected_secret_in_code":unsafe,"external_model_calls":0,"billing_used":False},note="No secret contents returned")
    if role == "ai-optimization":
        chunks = [s.strip() for s in re.split(r"[.!?\n]+",message) if s.strip()]
        try:
            receipt = compact(message)
        except ValueError:
            return _result(role,"BLOCKED",note="Input rejected by bounded compactor (invalid size or suspected credential)")
        return _result(role,"DONE",evidence={
            "text_segments":len(chunks),"unique_text_segments":len(set(chunks)),
            "estimated_tokens":None,"input_sha256":receipt["input_sha256"],
            "output_sha256":receipt["output_sha256"],
            "original_bytes":receipt["original_bytes"],"output_bytes":receipt["output_bytes"],
            "bytes_saved":receipt["bytes_saved"],
            "duplicate_lines_removed":receipt["duplicate_lines_removed"],
            "optimized_text":receipt["output"],"external_model_calls":0,
        },note="Executed real bounded text compaction; not LLM inference or measured token usage")
    if role == "ai-automation-design":
        steps = ["triage", "research", "bounded_action", "verify", "report"]
        return _result(role,"DONE",evidence={"plan_steps":steps,"operational_flows_modified":0},note="Drafted workflow only; no existing Activepieces flow executed")
    if role == "ai-operator-continuation":
        # A genuine bounded Python task on the local SHA-bound queue, not
        # a native ChatGPT execution or remote deployment.
        try:
            from queued_task_worker import QUEUE_PATH, execute
            payload = QUEUE_PATH.read_bytes()
            if len(payload) > 4096:
                raise ValueError("queued task exceeds size limit")
            receipt = execute(json.loads(payload))
            if (receipt.get("kind") != "REAL_ISOLATED_GITHUB_HOSTED_PYTHON_TASK_NOT_NATIVE_CHATGPT"
                    or receipt.get("status") != "PASS"
                    or receipt.get("native_chatgpt_run_verified") is not False):
                raise ValueError("invalid offline execution receipt")
        except (OSError, ValueError, TypeError, ImportError):
            return _result(role,"BLOCKED",note="Approved SHA-bound offline task unavailable or invalid")
        return _result(role,"DONE",evidence=receipt,
                       note="Executed bounded SHA-checked offline worker; native scheduled execution not verified")
    if role == "ai-scheduled-audit":
        return _result(role,"UNVERIFIED",note="This gateway has no ChatGPT official scheduled-run ID or original invocation logs")
    if role == "ai-cross-model-review":
        return _result(role,"BLOCKED",note="No verified zero-cost independent LLM providers connected; no simulated comparisons")
    if role == "ai-memory-recovery":
        if not network:
            return _result(role,"BLOCKED",note="Run with --allow-github-read for authenticated/public repository read")
        try:
            d=fetch(f"/repos/{REPO}/contents/{MEMORY_PATH}?ref=ai%2Fcontinuation-readonly-audit-2026-10-18")
            return _result(role,"DONE",evidence={"content_sha":d.get("sha"),"path":d.get("path"),"html_url":d.get("html_url"),"read_only":True},note="GitHub Contents API metadata; not a verified ChatGPT memory injection")
        except Exception as exc:
            return _result(role,"BLOCKED",note="GitHub read failed (access/network/size): "+type(exc).__name__)
    if role == "ai-code-verification":
        if not network:
            return _result(role,"BLOCKED",note="Run with --allow-github-read to inspect last remote CI metadata")
        try:
            branch=fetch(f"/repos/{REPO}/branches/ai/r16-v81-fast-full-ci-20261024")
            current_sha=(branch.get("commit") or {}).get("sha")
            if not isinstance(current_sha,str) or not re.fullmatch(r"[0-9a-f]{40}",current_sha):
                return _result(role,"UNVERIFIED",note="Current branch HEAD SHA unavailable or invalid")
            data=fetch(f"/repos/{REPO}/actions/runs?branch=ai%2Fr16-v81-fast-full-ci-20261024&per_page=10")
            runs=data.get("workflow_runs") if isinstance(data, dict) else None
            if not isinstance(runs,list) or not runs or len(runs)>10:
                return _result(role,"UNVERIFIED",note="No bounded current-branch CI run page")
            matching=[
                run for run in runs
                if (isinstance(run,dict)
                    and type(run.get("id")) is int and run["id"]>0
                    and run.get("head_sha")==current_sha
                    and run.get("event")=="push"
                    and run.get("path") in APPROVED_CI_WORKFLOWS)
            ]
            receipt={
                "branch_head_sha":current_sha,
                "head_match":bool(matching),
                "verified_workflow_count":len(matching),
                "runs":[{
                    "id":run["id"],"path":run["path"],
                    "status":run.get("status"),
                    "conclusion":run.get("conclusion"),
                    "head_sha":run["head_sha"],
                    "event":run["event"],"html_url":run.get("html_url"),
                } for run in matching],
                "native_chatgpt_run_verified":False,
                "source":"GITHUB_RUN_METADATA_ONLY_NO_JOB_LOGS",
            }
            if not matching:
                return _result(role,"UNVERIFIED",evidence=receipt,
                               note="No approved push workflow at current HEAD in recent runs")
            newest=matching[0]
            receipt.update(id=newest["id"],status=newest.get("status"),
                           conclusion=newest.get("conclusion"),
                           head_sha=newest["head_sha"],html_url=newest.get("html_url"))
            if any(run.get("status")=="completed" and
                   run.get("conclusion") in ("failure","timed_out","cancelled")
                   for run in matching):
                return _result(role,"FAIL",evidence=receipt,
                               note="Approved current-SHA workflow failed; inspect job/raw logs")
            if any(run.get("status")!="completed" or
                   run.get("conclusion")!="success" for run in matching):
                return _result(role,"UNVERIFIED",evidence=receipt,
                               note="Approved current-SHA workflows incomplete or not proven")
            return _result(role,"PARTIAL",evidence=receipt,
                           note="Approved current-SHA workflow metadata succeeded; raw logs unverified")
        except Exception as exc:
            return _result(role,"BLOCKED",note="CI metadata read failed: "+type(exc).__name__)
    if role == "ai-github-management":
        if not network:return _result(role,"BLOCKED",note="Run with --allow-github-read for repository metadata")
        try:
            d=fetch(f"/repos/{REPO}")
            return _result(role,"DONE",evidence={"full_name":d.get("full_name"),"default_branch":d.get("default_branch"),"html_url":d.get("html_url"),"read_only":True})
        except Exception as exc:
            return _result(role,"BLOCKED",note="Repository read failed: "+type(exc).__name__)
    if role == "ai-open-source-research":
        if not network:return _result(role,"BLOCKED",note="Run with --allow-github-read for approved project metadata")
        try:
            # Only known and explicit GitHub projects; never arbitrary URL from a prompt.
            out=[]
            for slug,repo in OSS_ALLOWLIST.items():
                d=fetch(f"/repos/{repo}")
                out.append({"repo":repo,"license":(d.get("license") or {}).get("spdx_id"),"html_url":d.get("html_url"),"archived":d.get("archived")})
            return _result(role,"PARTIAL",evidence={"projects":out},note="Metadata checked; complete suitability review not executed")
        except Exception as exc:
            return _result(role,"BLOCKED",note="Source metadata read failed: "+type(exc).__name__)
    return _result(role,"BLOCKED",note="Unsupported role (no process spawned)")


def run_message(message: str, *, code: str = "", network: bool = False,
                fetch: Callable[[str],dict] = github_get,
                project_context: bool = False) -> dict:
    if not isinstance(message,str) or not message.strip() or len(message)>MAX_MESSAGE:
        raise ValueError("message must have 1–4000 characters")
    if not isinstance(code,str) or len(code)>MAX_CODE:
        raise ValueError("code must have at most 10000 characters")
    choice=dispatch(message,max_roles=3,project_context=project_context)
    roles=choice["roles"]
    if choice["route"]=="DIRECT_CHAT":
        return {"route":"DIRECT_CHAT","workers":[],"status":"DIRECT", "message":"이 메시지는 일반 대화야. 전문 봇 실행이 필요하지 않아.","chatgpt_composer_hook":False}
    if not roles:
        roles=["ai-memory-recovery","ai-code-verification"]
    if choice["requires_action_permission_review"]:
        # no writes exist, but avoid untrusted remote tasks
        pass
    with ThreadPoolExecutor(max_workers=min(3,len(roles))) as pool:
        jobs=[pool.submit(execute_role,r,message,code=code,network=network,fetch=fetch) for r in roles]
        results=[job.result() for job in jobs]
    ok=sum(x["status"] in ("DONE","PARTIAL") for x in results)
    return {"route":"SPECIALISTS","selected_roles":roles,"workers":results,
            "status":"DONE" if ok==len(roles) else "PARTIAL" if ok else "BLOCKED",
            "external_llm_calls":0,"production_writes":0,"chatgpt_composer_hook":False,
            "source":"real_python_workers_executed_locally_not_native_chatgpt_hook"}


_PAGE="""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AI 실제 봇 실행</title><style>body{font:16px system-ui;max-width:760px;margin:auto;padding:20px;background:#fafafa;color:#181818}textarea{width:100%;min-height:80px;box-sizing:border-box}button{padding:10px 20px;margin:10px 0}pre{white-space:pre-wrap;word-wrap:break-word;background:white;padding:16px;border:1px solid #ddd;border-radius:10px}.msg{padding:8px;border-bottom:1px solid #ddd}label{display:block;margin-top:16px;font-weight:600}</style><h2>AI 자동 봇 실행기 — 로컬 데모</h2><p>이 페이지에서는 메시지 전송 시 Python 워커가 실제 실행돼. 공식 ChatGPT 앱의 채팅이 아니야.</p><label>메시지</label><textarea id="msg" aria-label="메시지">에러 고쳐</textarea><label>검사할 Python 코드(선택)</label><textarea id="code" aria-label="파이썬 코드">print(1)</textarea><button id="send">자동 분석·실행</button><pre id="out">메시지 전송을 눌러 봐.</pre><script>document.getElementById('send').onclick=async()=>{const out=document.getElementById('out');out.textContent='실행 중';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:document.getElementById('msg').value,code:document.getElementById('code').value})});out.textContent=JSON.stringify(await r.json(),null,2)}catch(e){out.textContent=String(e)}}</script></html>"""


def make_handler(*, network: bool = False, project_context: bool = False):
    class Handler(BaseHTTPRequestHandler):
        def _response(self, code:int, data:bytes, content_type:str):
            self.send_response(code)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline' 'self'")
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            if self.path=="/health":
                self._response(200,b'{"ok":true,"local_only":true}',"application/json")
            elif self.path=="/":
                self._response(200,_PAGE.encode(),"text/html; charset=utf-8")
            else:self._response(404,b'{"error":"not found"}',"application/json")
        def do_POST(self):
            if self.path!="/api/chat":
                self._response(404,b'{"error":"not found"}',"application/json");return
            try:
                length=int(self.headers.get("Content-Length", "0"))
                if self.headers.get("Content-Type","").split(";")[0].strip()!="application/json":
                    raise ValueError("Content-Type must be application/json")
                if not 1<=length<=16000:raise ValueError("body too large or empty")
                d=json.loads(self.rfile.read(length))
                if not isinstance(d,dict):raise ValueError("expected object")
                x=run_message(d.get("message"),code=d.get("code",""),network=network,
                              project_context=project_context)
                self._response(200,json.dumps(x,ensure_ascii=False).encode(),"application/json; charset=utf-8")
            except (ValueError,TypeError,json.JSONDecodeError) as exc:
                self._response(400,json.dumps({"error":str(exc)},ensure_ascii=False).encode(),"application/json; charset=utf-8")
        def log_message(self,*args):pass
    return Handler


def main() -> int:
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message")
    group.add_argument("--serve",action="store_true")
    parser.add_argument("--code",default="")
    parser.add_argument("--allow-github-read",action="store_true",help="perform bounded public GitHub REST GETs")
    parser.add_argument("--project-context",action="store_true",help="treat continuation commands as this approved local AI project")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    if args.serve:
        # Loopback only; never expose this unauthenticated demo on 0.0.0.0.
        server=ThreadingHTTPServer(("127.0.0.1",args.port),make_handler(network=args.allow_github_read,
                                                                         project_context=args.project_context))
        print("http://127.0.0.1:"+str(server.server_port),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
    else:
        try:result=run_message(args.message,code=args.code,network=args.allow_github_read,
                               project_context=args.project_context)
        except ValueError as exc:
            print(json.dumps({"error":str(exc)},ensure_ascii=False));return 2
        print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":raise SystemExit(main())
