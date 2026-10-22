"""Real authenticated remote transport test, no Internet deployment or paid provider."""
from __future__ import annotations
import asyncio
import json
import os
import socket
import subprocess
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

TOKEN = 'local-test-only-' + ('x' * 45)
HOST = '127.0.0.1'
PORT = 18083

async def verify():
    url=f'http://{HOST}:{PORT}/mcp'
    async with httpx.AsyncClient(timeout=10) as ordinary:
        response = await ordinary.post(url, json={'jsonrpc':'2.0', 'id':1,'method':'initialize','params':{}})
        assert response.status_code == 401, (response.status_code, response.text[:200])
        result = await ordinary.get(f'http://{HOST}:{PORT}/health')
        assert result.status_code == 200 and result.json()['auth'] == 'required'
    async with httpx.AsyncClient(headers={'Authorization':'Bearer WRONG'+TOKEN}, timeout=10) as wrong:
        r=await wrong.post(url,json={})
        assert r.status_code==401, r.status_code
    async with httpx.AsyncClient(headers={'Authorization':'Bearer '+TOKEN}, timeout=15) as authorized:
        async with streamable_http_client(url,http_client=authorized) as streams:
            read,write=streams[:2]
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert 'delegate_message' in [x.name for x in tools.tools]
                reply = await session.call_tool('delegate_message',{'message':'에러 고쳐','python_code':'print('})
                assert not reply.isError
                data = getattr(reply,'structuredContent',None)
                if data is None:
                    data = json.loads(next(x.text for x in reply.content if x.type == 'text'))
                data = data.get('result',data)
                assert data['workers'][0]['status']=='DONE',data
                assert data['workers'][0]['evidence']['syntax_valid'] is False
                assert data['external_llm_calls']==0 and data['production_writes']==0
                print(json.dumps({'mcp_real_authenticated_transport':'PASS','unauthorized_http':401,
                    'actual_worker':'DONE','tests':'initialize/list_tools/call_tool',
                    'external_llm_calls':0,'production_writes':0,'chatgpt_connected':False}))

def main():
    env=os.environ.copy()
    env.update({'AI_MCP_BEARER_TOKEN':TOKEN,'AI_MCP_ALLOWED_HOST':HOST})
    env.pop('RENDER_EXTERNAL_HOSTNAME',None)
    child=subprocess.Popen([sys.executable,'-m','uvicorn','remote_mcp:app','--host',HOST,'--port',str(PORT)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        until=time.monotonic()+25
        while time.monotonic()<until:
            if child.poll() is not None:
                raise AssertionError('server startup failed: '+child.stderr.read().decode()[-1000:])
            try:
                with socket.create_connection((HOST,PORT),timeout=.3): break
            except OSError: time.sleep(.15)
        else: raise TimeoutError('remote MCP server startup timed out')
        asyncio.run(verify())
    finally:
        child.terminate()
        try:child.communicate(timeout=4)
        except subprocess.TimeoutExpired:child.kill();child.communicate(timeout=4)

if __name__ == '__main__':main()
