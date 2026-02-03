"""Entry point to run the MCP server over stdio.

Used by the demo and by clients that launch the server as a subprocess.

Example:
    python -m asap.mcp.server_runner

Then send JSON-RPC messages (one per line) to stdin; read responses from stdout.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys


def main() -> None:
    """Run MCP server with echo tool on stdio."""
    from asap.mcp.server import MCPServer

    server = MCPServer(
        name="asap-mcp-demo",
        version="1.0.0",
        description="ASAP MCP demo server with echo tool",
    )
    server.register_tool(
        "echo",
        lambda message: message,
        {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
        description="Echo back the given message",
        title="Echo",
    )
    with contextlib.suppress(BrokenPipeError, KeyboardInterrupt):
        asyncio.run(server.run_stdio())
    sys.exit(0)


if __name__ == "__main__":
    main()
