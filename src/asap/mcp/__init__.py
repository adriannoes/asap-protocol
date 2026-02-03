"""Model Context Protocol (MCP) integration for ASAP.

Implements MCP spec 2025-11-25: JSON-RPC 2.0 over stdio (or other transports),
with support for initialize, tools/list, and tools/call.

Example:
    >>> from asap.mcp import MCPServer
    >>> server = MCPServer(name="my-server", version="1.0.0")
    >>> server.register_tool("echo", lambda message: message, {"type": "object", "properties": {"message": {"type": "string"}}})
    >>> # asyncio.run(server.run_stdio())
"""

from asap.mcp.client import MCPClient
from asap.mcp.protocol import (
    MCP_PROTOCOL_VERSION,
    CallToolRequestParams,
    CallToolResult,
    InitializeRequestParams,
    InitializeResult,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    ListToolsResult,
    TextContent,
    Tool,
)
from asap.mcp.server import MCPServer

__all__ = [
    "MCPClient",
    "MCPServer",
    "MCP_PROTOCOL_VERSION",
    "CallToolRequestParams",
    "CallToolResult",
    "InitializeRequestParams",
    "InitializeResult",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "ListToolsResult",
    "TextContent",
    "Tool",
]
