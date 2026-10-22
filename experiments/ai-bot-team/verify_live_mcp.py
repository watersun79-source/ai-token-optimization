"""Live MCP v1 loopback integration: initialize, list tools, call real Python worker.
This is not proof of ChatGPT plugin linkage or public HTTPS deployment.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def wait_for_tcp(host: str, port: int, process: subprocess.Popen, timeout: float = 18) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('MCP server exited prematurely with code '+str(process.returncode))
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError('MCP server did not bind localhost within timeout')


async def actual_client_session() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client('http://127.0.0.1:8000/mcp') as transport:
        read_stream, write_stream = transport[:2]
        async with ClientSession(read_stream, write_stream) as session:
            initialize = await session.initialize()
            assert initialize.serverInfo.name, 'server identity missing'
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert 'delegate_message' in names, f'list_tools missing: {names}'
            call = await session.call_tool('delegate_message', {
                'message': '에러 고쳐', 'python_code': 'print('
            })
            assert not call.isError, f'MCP reported tool failure: {call}'
            structured = getattr(call, 'structuredContent', None)
            if structured is None:
                blocks = [b.text for b in call.content if getattr(b,'type',None)=='text']
                assert blocks, 'missing tool result content'
                structured = json.loads(blocks[0])
            payload = structured.get('result', structured)
            assert payload['workers'][0]['role'] == 'ai-auto-debug', payload
            assert payload['workers'][0]['status'] == 'DONE', payload
            assert payload['workers'][0]['evidence']['syntax_valid'] is False, payload
            assert payload['external_llm_calls'] == 0
            assert payload['production_writes'] == 0
            assert payload['chatgpt_composer_hook'] is False
            print(json.dumps({'mcp_live_transport': 'PASS', 'server': initialize.serverInfo.name,
                'tool': 'delegate_message', 'worker': payload['workers'][0]['role'],
                'worker_status': payload['workers'][0]['status'],
                'python_syntax_valid': False, 'external_llm_calls': 0,
                'production_writes': 0, 'connected_to_chatgpt': False}, ensure_ascii=False))


def main() -> None:
    root = Path(__file__).resolve().parent
    if not (root/'mcp_server.py').exists():
        raise SystemExit('Place verify_live_mcp.py beside mcp_server.py')
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    process = subprocess.Popen([sys.executable, str(root/'mcp_server.py')], cwd=root,
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_tcp('127.0.0.1', 8000, process)
        asyncio.run(actual_client_session())
    finally:
        process.terminate()
        try: process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=4)

if __name__=='__main__':
    main()
