"""
MCP Client — connects to the MCP server via stdio (local dev) or HTTP/SSE (Docker/ECS).

Transport is selected by the MCP_TRANSPORT environment variable:

  MCP_TRANSPORT=stdio  (default)
      Spawns the MCP server as a local subprocess.
      Used when running the agent directly with `uv run python main.py`.

  MCP_TRANSPORT=http
      Connects to a running MCP server over HTTP/SSE.
      Used in Docker (docker-compose) and ECS deployment.
      Requires MCP_SERVER_URL — e.g. http://mcp-server:8200/sse

Responsibilities:
  - list_tools()  → return tools in Bedrock toolSpec format
  - call_tool()   → forward a tool call, return plain-text result
  - close()       → clean shutdown (handled by context manager)

Usage:
    async with MCPClient.connect() as client:
        tools  = await client.list_tools()
        result = await client.call_tool("get_weather", {"city": "Tokyo"})
"""

import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client

# ── Transport config ──────────────────────────────────────────────────────────

_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")

# stdio — path to the server script (one level up from this file)
_SERVER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "mcp-server", "server.py"
)
_SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "python", os.path.abspath(_SERVER_SCRIPT)],
    env=None,   # inherits current environment (.env already loaded by agent)
)

# http — URL of the running MCP server's SSE endpoint
_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8200/sse")


# ── Format conversion ─────────────────────────────────────────────────────────

def _mcp_tool_to_bedrock(tool) -> dict:
    """
    Convert one MCP tool object to Bedrock Converse toolSpec format.

    MCP shape:
        tool.name        str
        tool.description str
        tool.inputSchema dict  (raw JSON Schema)

    Bedrock shape:
        {"toolSpec": {"name": ..., "description": ..., "inputSchema": {"json": <schema>}}}
    """
    return {
        "toolSpec": {
            "name":        tool.name,
            "description": tool.description or "",
            "inputSchema": {
                "json": tool.inputSchema   # Bedrock wraps JSON Schema under "json" key
            },
        }
    }


# ── Client ────────────────────────────────────────────────────────────────────

class MCPClient:
    """Thin async wrapper around an MCP ClientSession."""

    def __init__(self, session: ClientSession):
        self._session = session

    # ── Factory ───────────────────────────────────────────────────────────────

    @staticmethod
    @asynccontextmanager
    async def connect():
        """
        Async context manager that connects to the MCP server and yields
        a ready MCPClient.

        Transport is chosen by MCP_TRANSPORT env var:
          - "stdio" (default) — spawns the MCP server as a subprocess
          - "http"            — connects to a running server via SSE

        Example:
            async with MCPClient.connect() as client:
                tools = await client.list_tools()
        """
        if _TRANSPORT == "http":
            print(f"[mcp] connecting via HTTP/SSE → {_MCP_SERVER_URL}")
            async with sse_client(_MCP_SERVER_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield MCPClient(session)
        else:
            print("[mcp] connecting via stdio (subprocess)")
            async with stdio_client(_SERVER_PARAMS) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield MCPClient(session)

    # ── Public API ────────────────────────────────────────────────────────────

    async def list_tools(self) -> list[dict]:
        """
        Return all MCP tools converted to Bedrock toolSpec format.
        Call once at agent startup and pass the result to Bedrock toolConfig.
        """
        response = await self._session.list_tools()
        bedrock_tools = [_mcp_tool_to_bedrock(t) for t in response.tools]
        print(f"[mcp] {len(bedrock_tools)} tools loaded: "
              f"{[t['toolSpec']['name'] for t in bedrock_tools]}")
        return bedrock_tools

    async def call_tool(self, name: str, inputs: dict) -> str:
        """
        Call an MCP tool by name and return the result as a plain string.
        The MCP server handles the actual Travel API call.
        """
        print(f"[mcp] calling tool '{name}' with {inputs}")
        response = await self._session.call_tool(name, inputs)

        # response.content is a list of content blocks; collect all text parts
        parts = [block.text for block in response.content if hasattr(block, "text")]
        result = "\n".join(parts)
        print(f"[mcp] result preview: {result[:120]!r}")
        return result
