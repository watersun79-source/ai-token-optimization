"""Fail-closed, read-only remote MCP server for staging deployment.

Intentionally separate from the localhost demo. Requires a private static bearer
secret and an explicitly verified public hostname. This is an MCP API-key style
resource, not an OAuth authorization server; ChatGPT connection remains separate.
"""
from __future__ import annotations

import hmac
import json
import os
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from real_gateway import run_message


def runtime_config() -> tuple[str, str]:
    token = os.environ.get('AI_MCP_BEARER_TOKEN', '')
    if len(token) < 32 or token.isspace() or len(token) > 512:
        raise RuntimeError('AI_MCP_BEARER_TOKEN must be a private random secret >=32 chars')
    hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME') or os.environ.get('AI_MCP_ALLOWED_HOST', '')
    # No wildcard or URL schemes. Prevent host-header bypass by configuration.
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,250}[a-z0-9]', hostname) or '..' in hostname:
        raise RuntimeError('Explicit RENDER_EXTERNAL_HOSTNAME or AI_MCP_ALLOWED_HOST required')
    return token, hostname


SECRET, HOSTNAME = runtime_config()

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[HOSTNAME, HOSTNAME + ':*', '127.0.0.1:*', 'localhost:*'],
    allowed_origins=['https://' + HOSTNAME, 'http://127.0.0.1:*', 'http://localhost:*'],
)
mcp = FastMCP(
    'AI Real Bot Gateway',
    instructions='Read-only bounded Python workers. Does not call external LLM providers or change production.',
    json_response=True,
    stateless_http=True,
    host='0.0.0.0',
    transport_security=transport_security,
)


@mcp.tool()
def delegate_message(message: str, python_code: str = '') -> dict:
    """Run bounded local Python analysis workers on a message now (no production writes)."""
    return run_message(message, code=python_code, network=False)


async def _respond(send, status: int, body: dict):
    data = json.dumps(body).encode('utf-8')
    await send({'type':'http.response.start','status':status,'headers':[
        (b'content-type',b'application/json'),(b'content-length',str(len(data)).encode()),
        (b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),
    ]})
    await send({'type':'http.response.body','body':data})


inner_app = mcp.streamable_http_app()


async def app(scope, receive, send):
    """Protect every MCP HTTP method before the SDK reaches it, pass lifespan through."""
    if scope['type'] == 'http':
        path = scope.get('path', '')
        method = scope.get('method', '')
        if path == '/health' and method == 'GET':
            await _respond(send, 200, {'healthy': True, 'mcp': '/mcp', 'auth': 'required'})
            return
        if path != '/mcp':
            await _respond(send, 404, {'error': 'not found'})
            return
        headers = {k.lower():v for k,v in scope.get('headers',[])}
        provided = headers.get(b'authorization', b'')
        expected = ('Bearer ' + SECRET).encode('utf-8')
        if not hmac.compare_digest(provided, expected):
            await _respond(send, 401, {'error': 'unauthorized'})
            return
    await inner_app(scope, receive, send)
