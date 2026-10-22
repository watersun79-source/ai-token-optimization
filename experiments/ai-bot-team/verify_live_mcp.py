"""Live MCP v1 transport integration with a real Python worker on localhost."""
from __future__ import annotations
import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

async def check_protocol():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client("http://127.0.0.1:8000/mcp") as streams:
        read_stream, write_stream = streams[:2]
        async with ClientSession(read_stream, write_stream) as session:
            welcome = await session.initialize()
            assert welcome.serverInfo.name
            tools = await session.list_tools()
            assert "delegate_message" in {tool.name for tool in tools.tools}
            response = await session.call_tool("delegate_message", {
                "message": "에러 고쳐", "python_code": "print("
            })
            assert not response.isError, response
            data = getattr(response, "structuredContent", None)
            if data is None:
                blocks = [x.text for x in response.content if x.type == "text"]
                assert blocks
                data = json.loads(blocks[0])
            payload = data.get("result", data)
            assert payload["workers"][0]["role"] == "ai-auto-debug", payload
            assert payload["workers"][0]["status"] == "DONE", payload
            assert payload["workers"][0]["evidence"]["syntax_valid"] is False, payload
            assert payload["external_llm_calls"] == 0
            assert payload["production_writes"] == 0
            assert payload["chatgpt_composer_hook"] is False
            print(json.dumps({
                "real_mcp_initialize_list_tools_call_tool": "PASS",
                "worker_status": payload["workers"][0]["status"],
                "provider_calls": 0, "production_writes": 0,
                "chatgpt_connected": False
            }, ensure_ascii=False))

def main():
    cwd = Path(__file__).resolve().parent
    server = subprocess.Popen([sys.executable, "mcp_server.py"], cwd=cwd,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError("MCP server exited before accepting connections")
            try:
                with socket.create_connection(("127.0.0.1", 8000), timeout=.5):
                    break
            except OSError:
                time.sleep(.15)
        else:
            raise TimeoutError("MCP server never bound to loopback port 8000")
        asyncio.run(check_protocol())
    finally:
        server.terminate()
        try: server.wait(timeout=4)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=4)

if __name__ == "__main__":
    main()
