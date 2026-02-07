"""MCP client demo: connect to MCP server via stdio, list tools, call echo.

Starts the MCP server as a subprocess (asap.mcp.server_runner), connects
the client via stdio, lists available tools, calls the "echo" tool with
a message, and verifies the result.

Run:
    uv run python -m asap.examples.mcp_client_demo
"""

from __future__ import annotations

import asyncio
import logging
import sys

from asap.mcp.client import MCPClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
_log = logging.getLogger(__name__)


async def main() -> int:
    """Run MCP demo: start server, list tools, call echo."""
    server_command = [sys.executable, "-m", "asap.mcp.server_runner"]
    client = MCPClient(server_command)

    async with client:
        result = client._init_result
        if result:
            _log.info(
                "Initialized: %s %s",
                result.server_info.name,
                result.server_info.version,
            )

        tools = await client.list_tools()
        _log.info("Tools: %s", [t.name for t in tools])
        if not tools:
            _log.error("No tools found")
            return 1

        call_result = await client.call_tool("echo", {"message": "hello from MCP demo"})
        if call_result.is_error:
            _log.error("Echo failed: %s", call_result.content)
            return 1
        text = "".join(c.get("text", "") for c in call_result.content if c.get("type") == "text")
        _log.info("Echo result: %s", text)
        if text != "hello from MCP demo":
            _log.error("Expected 'hello from MCP demo'")
            return 1

    _log.info("Demo OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
