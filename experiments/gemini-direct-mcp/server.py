"""Dependency-free MCP stdio server. Does not start an HTTP listener."""
from __future__ import annotations

import json
import signal
import sys

from adapter import Adapter, Blocked, Config

PROTOCOL_VERSION = "2025-06-18"
TOOLS = [
    {"name": "gemini_status", "description": "Inspect the actual official CLI runtime and local verification gate. Never reads credentials or calls a model.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "gemini_review", "description": "Run the official Gemini CLI once. Blocks unless recent externally verified personal Google authentication and CLI free quota evidence are configured. No arbitrary CLI arguments or tool execution.",
     "inputSchema": {"type": "object", "properties": {"request_id": {"type": "string", "minLength": 8, "maxLength": 80, "pattern": "^[A-Za-z0-9_-]+$"}, "prompt": {"type": "string", "minLength": 1, "maxLength": 6000}}, "required": ["request_id", "prompt"], "additionalProperties": False},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}},
]


class Server:
    def __init__(self, adapter):
        self.adapter = adapter
        self.initialized = False

    @staticmethod
    def error(rid, code, message):
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}

    @staticmethod
    def ok(rid, result):
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    @staticmethod
    def tool(value, error=False):
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "structuredContent": value, "isError": error}

    def handle(self, req):
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
            return self.error(req.get("id") if isinstance(req, dict) else None, -32600, "Invalid Request")
        if "id" not in req:
            return None
        rid = req["id"]
        if isinstance(rid, bool) or not isinstance(rid, (str, int)):
            return self.error(None, -32600, "Invalid request id")
        method = req["method"]
        params = req.get("params", {})
        if not isinstance(params, dict):
            return self.error(rid, -32602, "Invalid params")
        if method == "initialize":
            if not isinstance(params.get("protocolVersion"), str):
                return self.error(rid, -32602, "Missing protocolVersion")
            self.initialized = True
            return self.ok(rid, {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "gemini-real-cli-mcp", "version": "0.1.0"}, "instructions": "Status and protocol success do not prove Gemini authentication or model inference. Never send credentials in tool arguments."})
        if not self.initialized:
            return self.error(rid, -32000, "Not initialized")
        if method == "ping":
            return self.ok(rid, {})
        if method == "tools/list":
            return self.ok(rid, {"tools": TOOLS})
        if method != "tools/call":
            return self.error(rid, -32601, "Method not found")
        args = params.get("arguments", {})
        if not isinstance(args, dict):
            return self.error(rid, -32602, "Invalid tool arguments")
        try:
            if params.get("name") == "gemini_status" and not args:
                return self.ok(rid, self.tool(self.adapter.status()))
            if params.get("name") == "gemini_review" and set(args) == {"request_id", "prompt"}:
                result = self.adapter.review(args["request_id"], args["prompt"])
                return self.ok(rid, self.tool(result, result["status"] != "PASS_REAL_CLI_JSON_RESPONSE"))
            return self.error(rid, -32602, "Invalid tool name or arguments")
        except Blocked as exc:
            return self.ok(rid, self.tool({"status": exc.code, "model_called": False}, True))
        except Exception:
            return self.ok(rid, self.tool({"status": "BLOCKED_INTERNAL_ERROR", "model_called": "UNVERIFIED"}, True))


def main():
    def cancelled(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, cancelled)
    try:
        adapter = Adapter(Config.from_env())
    except Blocked as exc:
        print(exc.code, file=sys.stderr)
        return 1
    server = Server(adapter)
    source = sys.stdin.buffer
    while True:
        line = source.readline(65537)
        if not line:
            break
        if len(line) > 65536:
            while line and not line.endswith(b"\n"):
                line = source.readline(65537)
            reply = Server.error(None, -32600, "Request too large")
        else:
            try:
                req = json.loads(line)
                reply = server.handle(req)
            except (ValueError, UnicodeError):
                reply = Server.error(None, -32700, "Parse error")
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
