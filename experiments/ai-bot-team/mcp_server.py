"""Real MCP tool adapter for the Python gateway.

The tool is not automatically inserted in official ChatGPT conversations.
Install the pinned MCP SDK and host/connect the server through a supported
ChatGPT MCP environment. Prefer authentication before any public deployment.
"""
from __future__ import annotations
from real_gateway import run_message

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit("Install requirements-mcp.txt to run the actual MCP server") from exc

mcp = FastMCP("AI Real Bot Gateway", json_response=True)

@mcp.tool()
def delegate_message(message: str, python_code: str = "") -> dict:
    """Automatically route an AI-project request to bounded Python workers; execute them now.

    This tool does not write to GitHub, Slack, Activepieces, or any production
    system. Only local analysis and limited read-only checks are possible.
    """
    return run_message(message,code=python_code,network=False)

if __name__=="__main__":
    mcp.run(transport="streamable-http")
