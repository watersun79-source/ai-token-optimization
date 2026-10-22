"""Live local OAuth resource-server test. External authorization is mocked, no user login."""
import asyncio,json,os,socket,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx,jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
PORT,JPORT=18084,18085
RESOURCE=f"http://127.0.0.1:{PORT}/mcp"
ISSUER=f"http://127.0.0.1:{JPORT}"
KEY=rsa.generate_private_key(public_exponent=65537,key_size=2048)
JWK=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
JWK.update({"kid":"local-test-key","alg":"RS256","use":"sig"})
class JWKSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/jwks":d={"keys":[JWK]}
        elif self.path=="/.well-known/oauth-authorization-server":
            d={"issuer":ISSUER,"authorization_endpoint":ISSUER+"/authorize",
               "token_endpoint":ISSUER+"/token","jwks_uri":ISSUER+"/jwks",
               "code_challenge_methods_supported":["S256"]}
        else:self.send_response(404);self.end_headers();return
        b=json.dumps(d).encode()
        self.send_response(200);self.send_header("content-type","application/json")
        self.send_header("content-length",str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*a):pass
def token(**kw):
    now=int(time.time())
    claims={"iss":ISSUER,"aud":RESOURCE,"sub":"sandbox-user","client_id":"sandbox-client",
            "scope":"ai:analyze","iat":now-20,"nbf":now-20,"exp":now+120}
    claims.update(kw)
    return jwt.encode(claims,KEY,algorithm="RS256",headers={"kid":"local-test-key","typ":"at+jwt"})
async def verify():
    async with httpx.AsyncClient(timeout=15) as client:
        h=await client.get(f"http://127.0.0.1:{PORT}/health")
        assert h.status_code==200 and h.json()["oauth"]=="resource-server-only"
        r=await client.post(RESOURCE,json={})
        assert r.status_code==401,(r.status_code,r.text[:150])
        assert "resource_metadata=" in r.headers.get("www-authenticate","")
        md=await client.get(f"http://127.0.0.1:{PORT}/.well-known/oauth-protected-resource/mcp")
        assert md.status_code==200,(md.status_code,md.text[:200])
        assert md.json()["resource"]==RESOURCE,md.text
        assert [u.rstrip("/") for u in md.json()["authorization_servers"]]==[ISSUER],md.text
        checks={
            "expired":token(exp=int(time.time())-300),
            "wrong_audience":token(aud="http://localhost:9999/mcp"),
            "wrong_issuer":token(iss="http://localhost:9999"),
            "missing_scope":token(scope="other:read"),
            "future":token(nbf=int(time.time())+300),
            "forged_signature":token()[:-6]+"ABCDEF",
        }
        for name,t in checks.items():
            rr=await client.post(RESOURCE,json={},headers={"authorization":"Bearer "+t})
            assert rr.status_code in (401,403),(name,rr.status_code,rr.text[:150])
        async with httpx.AsyncClient(timeout=20,headers={"Authorization":"Bearer "+token()}) as client_auth:
            async with streamable_http_client(RESOURCE,http_client=client_auth) as streams:
                async with ClientSession(streams[0],streams[1]) as session:
                    await session.initialize()
                    tools=await session.list_tools()
                    assert "delegate_message" in {x.name for x in tools.tools}
                    result=await session.call_tool("delegate_message",{"message":"에러 고쳐","python_code":"print("})
                    assert not result.isError,result
                    d=getattr(result,"structuredContent",None)
                    if d is None:d=json.loads(next(x.text for x in result.content if x.type=="text"))
                    d=d.get("result",d)
                    assert d["workers"][0]["status"]=="DONE",d
                    assert d["workers"][0]["evidence"]["syntax_valid"] is False
                    assert d["external_llm_calls"]==0 and d["production_writes"]==0
        print(json.dumps({"oauth_mcp_resource_server":"PASS","rfc9728":"PASS","invalid_token_cases":len(checks),
                          "real_worker":"DONE","oauth_login_pkce":"NOT_TESTED","chatgpt_connected":False}))
def main():
    mock=ThreadingHTTPServer(("127.0.0.1",JPORT),JWKSHandler)
    threading.Thread(target=mock.serve_forever,daemon=True).start()
    env=os.environ.copy()
    env.update({"AI_MCP_RESOURCE":RESOURCE,"AI_OAUTH_ISSUER":ISSUER,
                "AI_OAUTH_JWKS_URI":ISSUER+"/jwks","AI_OAUTH_LOCAL_TEST":"1"})
    proc=subprocess.Popen([sys.executable,"-m","uvicorn","oauth_mcp:build_app",
                           "--factory","--host","127.0.0.1","--port",str(PORT)],
                          env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(120):
            if proc.poll() is not None:
                raise RuntimeError("OAuth server failed: "+proc.stderr.read().decode()[-2500:])
            try:
                with socket.create_connection(("127.0.0.1",PORT),timeout=.4):break
            except OSError:time.sleep(.15)
        else:raise TimeoutError("OAuth MCP did not start")
        asyncio.run(verify())
    finally:
        proc.terminate()
        try:proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate(timeout=4)
        mock.shutdown();mock.server_close()
if __name__=="__main__":main()
