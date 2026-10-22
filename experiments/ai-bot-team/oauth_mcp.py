"""OAuth resource-server prototype (not an OAuth authorization server or ChatGPT hook)."""
from __future__ import annotations
import os
from urllib.parse import urlparse
import jwt
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse
from real_gateway import run_message

SCOPE="ai:analyze"

def validate_config(env=None):
    env=os.environ if env is None else env
    resource=env.get("AI_MCP_RESOURCE","")
    issuer=env.get("AI_OAUTH_ISSUER","")
    jwks_uri=env.get("AI_OAUTH_JWKS_URI","")
    test_mode=env.get("AI_OAUTH_LOCAL_TEST")=="1"
    for name,value in (("AI_MCP_RESOURCE",resource),("AI_OAUTH_ISSUER",issuer),("AI_OAUTH_JWKS_URI",jwks_uri)):
        u=urlparse(value)
        if not u.hostname or u.username or u.password or u.fragment:
            raise RuntimeError("Invalid or missing "+name)
        if u.scheme!="https" and not (test_mode and u.scheme=="http" and u.hostname in ("127.0.0.1","localhost")):
            raise RuntimeError(name+" requires HTTPS")
    if not resource.endswith("/mcp") or urlparse(resource).query:
        raise RuntimeError("Resource URL must end with /mcp and have no query")
    if test_mode and any(urlparse(x).hostname not in ("127.0.0.1","localhost") for x in (resource,issuer,jwks_uri)):
        raise RuntimeError("Local test mode must remain loopback-only")
    if not test_mode and urlparse(resource).hostname in ("127.0.0.1","localhost"):
        raise RuntimeError("Production must use external HTTPS endpoint")
    return resource,issuer,jwks_uri,test_mode

class JWTTokenVerifier:
    def __init__(self,resource,issuer,jwks_uri):
        self.resource,self.issuer=resource,issuer
        self.keys=jwt.PyJWKClient(jwks_uri,cache_keys=True,cache_jwk_set=True,lifespan=300,timeout=4)
    async def verify_token(self,token: str)->AccessToken|None:
        try:
            header=jwt.get_unverified_header(token)
            if header.get("alg")!="RS256" or header.get("typ") not in (None,"JWT","at+jwt"):
                return None
            key=self.keys.get_signing_key_from_jwt(token)
            claims=jwt.decode(token,key.key,algorithms=["RS256"],issuer=self.issuer,
                              audience=self.resource,options={"require":["iss","aud","exp","iat","sub"]},leeway=10)
            scope=claims.get("scope","")
            scopes=scope.split() if isinstance(scope,str) else []
            client_id=claims.get("client_id") or claims.get("azp")
            if SCOPE not in scopes or not isinstance(client_id,str) or not client_id:
                return None
            return AccessToken(token=token,client_id=client_id,scopes=scopes,
                               expires_at=int(claims["exp"]),resource=self.resource,
                               subject=claims["sub"],claims={"iss":claims["iss"],"aud":claims["aud"]})
        except Exception:
            return None

def build_app():
    resource,issuer,jwks_uri,_=validate_config()
    u=urlparse(resource)
    host=u.hostname
    port=u.port
    origin=f"{u.scheme}://{host}"+(f":{port}" if port else "")
    mcp=FastMCP("AI OAuth Bot Gateway",
        token_verifier=JWTTokenVerifier(resource,issuer,jwks_uri),
        auth=AuthSettings(issuer_url=AnyHttpUrl(issuer),resource_server_url=AnyHttpUrl(resource),
                          required_scopes=[SCOPE]),
        json_response=True,stateless_http=True,host="0.0.0.0",
        transport_security=TransportSecuritySettings(
          enable_dns_rebinding_protection=True,
          allowed_hosts=[host+":*"],allowed_origins=[origin]),
        max_request_body_size=16000)
    @mcp.tool(meta={"securitySchemes":[{"type":"oauth2","scopes":[SCOPE]}]})
    def delegate_message(message:str,python_code:str="")->dict:
        """Execute only permitted local Python analysis workers on natural-language instructions."""
        return run_message(message,code=python_code,network=False)
    @mcp.custom_route("/health",methods=["GET"])
    async def health(_request:Request):
        return JSONResponse({"ok":True,"oauth":"resource-server-only","chatgpt_connected":False})
    return mcp.streamable_http_app()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(build_app(),host="0.0.0.0",port=int(os.environ.get("PORT","8000")),access_log=False)
