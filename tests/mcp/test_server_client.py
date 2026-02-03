"""Integration tests for MCP server and client (stdio)."""

import asyncio
import json
import sys

import pytest

from asap.mcp.client import MCPClient
from asap.mcp.server import MCPServer


@pytest.mark.asyncio
async def test_mcp_client_list_and_call_echo() -> None:
    """Client can connect to server_runner, list tools, and call echo."""
    server_command = [sys.executable, "-m", "asap.mcp.server_runner"]
    client = MCPClient(server_command)
    async with client:
        result = client._init_result
        assert result is not None
        assert result.server_info.name == "asap-mcp-demo"
        tools = await client.list_tools()
        assert len(tools) >= 1
        names = [t.name for t in tools]
        assert "echo" in names
        call_result = await client.call_tool("echo", {"message": "test"})
        assert call_result.is_error is False
        text = "".join(c.get("text", "") for c in call_result.content if c.get("type") == "text")
        assert text == "test"


@pytest.mark.asyncio
async def test_mcp_server_handle_initialize_and_tools_list() -> None:
    """MCPServer handle_initialize and _handle_tools_list return valid structures."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "add",
        lambda a, b: a + b,
        {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
        description="Add two numbers",
    )
    init_result = server._handle_initialize(None)
    assert init_result["protocolVersion"] == "2025-11-25"
    assert "tools" in init_result["capabilities"]
    list_result = server._handle_tools_list(None)
    assert "tools" in list_result
    assert len(list_result["tools"]) == 1
    assert list_result["tools"][0]["name"] == "add"


@pytest.mark.asyncio
async def test_mcp_server_handle_tools_call() -> None:
    """MCPServer _handle_tools_call executes tool and returns content."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "double",
        lambda x: x * 2,
        {"type": "object", "properties": {"x": {"type": "number"}}, "required": ["x"]},
        description="Double a number",
    )
    result = await server._handle_tools_call({"name": "double", "arguments": {"x": 5}})
    assert result["isError"] is False
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"] == "10"


@pytest.mark.asyncio
async def test_mcp_server_unknown_tool_returns_is_error() -> None:
    """Calling unknown tool returns isError true."""
    server = MCPServer(name="t", version="0.1.0")
    result = await server._handle_tools_call({"name": "nonexistent", "arguments": {}})
    assert result["isError"] is True
    assert any("Unknown tool" in c.get("text", "") for c in result["content"])


@pytest.mark.asyncio
async def test_mcp_server_invalid_tools_call_params_raises() -> None:
    """Invalid tools/call params (e.g. missing name) raise ValueError for protocol error."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "x", lambda: 1, {"type": "object", "additionalProperties": False}, description="X"
    )
    with pytest.raises(ValueError, match="Invalid params"):
        await server._handle_tools_call({})
    with pytest.raises(ValueError, match="Invalid params"):
        await server._handle_tools_call({"arguments": {}})


@pytest.mark.asyncio
async def test_mcp_server_dispatch_tools_call_invalid_params_returns_jsonrpc_error() -> None:
    """When tools/call has invalid params, server returns JSON-RPC error -32602, not CallToolResult."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "echo",
        lambda message: message,
        {"type": "object", "properties": {"message": {"type": "string"}}},
        description="Echo",
    )
    from asap.mcp.protocol import JSONRPCRequest

    req = JSONRPCRequest(id=1, method="tools/call", params={})
    response_line = await server._dispatch_request(req)
    assert response_line is not None
    data = json.loads(response_line)
    assert "error" in data
    assert data["error"]["code"] == -32602
    assert "result" not in data or data.get("result") is None


@pytest.mark.asyncio
async def test_mcp_server_dispatch_ping_returns_empty_result() -> None:
    """Ping method returns JSON-RPC result with empty object."""
    from asap.mcp.protocol import JSONRPCRequest

    server = MCPServer(name="t", version="0.1.0")
    req = JSONRPCRequest(id=42, method="ping", params=None)
    response_line = await server._dispatch_request(req)
    assert response_line is not None
    data = json.loads(response_line)
    assert data.get("result") == {}
    assert "error" not in data


@pytest.mark.asyncio
async def test_mcp_server_dispatch_method_not_found_returns_32601() -> None:
    """Unknown method returns JSON-RPC error -32601 METHOD_NOT_FOUND."""
    from asap.mcp.protocol import JSONRPCRequest

    server = MCPServer(name="t", version="0.1.0")
    req = JSONRPCRequest(id=1, method="unknown/method", params={})
    response_line = await server._dispatch_request(req)
    assert response_line is not None
    data = json.loads(response_line)
    assert data["error"]["code"] == -32601
    assert "Method not found" in data["error"]["message"]


@pytest.mark.asyncio
async def test_mcp_server_subprocess_returns_internal_error_when_dispatch_raises() -> None:
    """When server process receives a request that causes dispatch to raise, it returns -32603."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "asap.mcp.server_runner",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None
    # Send request that causes _handle_tools_call to get invalid params and raise (e.g. params list)
    proc.stdin.write(b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":[]}\n')
    await proc.stdin.drain()
    # Close stdin so producer stops and consumer processes the queued message
    proc.stdin.close()
    await asyncio.sleep(0.1)
    # Server may log to stdout first; read until we get a JSON-RPC response line
    data = None
    for _ in range(20):
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=2.0)
        if not line:
            break
        s = line.decode("utf-8").strip()
        if s.startswith("{"):
            data = json.loads(s)
            break
    await proc.wait()
    assert data is not None, "Expected one JSON-RPC response line on stdout"
    assert "error" in data
    assert data["error"]["code"] == -32603


@pytest.mark.asyncio
async def test_mcp_server_handle_tools_call_returns_dict_as_json_text() -> None:
    """Tool returning a dict is serialized as JSON in text content."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "get_dict",
        lambda: {"a": 1, "b": 2},
        {"type": "object", "additionalProperties": False},
        description="Returns dict",
    )
    result = await server._handle_tools_call({"name": "get_dict", "arguments": {}})
    assert result["isError"] is False
    assert result["content"][0]["text"] == '{"a": 1, "b": 2}'


@pytest.mark.asyncio
async def test_mcp_server_handle_tools_call_tool_raises_returns_is_error() -> None:
    """Tool that raises returns isError true with error message in content."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "raises",
        lambda: 1 / 0,
        {"type": "object", "additionalProperties": False},
        description="Raises",
    )
    result = await server._handle_tools_call({"name": "raises", "arguments": {}})
    assert result["isError"] is True
    assert any(
        "division" in c.get("text", "").lower() or "zero" in c.get("text", "").lower()
        for c in result["content"]
    )


@pytest.mark.asyncio
async def test_mcp_server_handle_initialize_no_tools_empty_capabilities() -> None:
    """Server with no tools returns capabilities without tools key."""
    server = MCPServer(name="t", version="0.1.0")
    init_result = server._handle_initialize(None)
    assert init_result["protocolVersion"] == "2025-11-25"
    assert "capabilities" in init_result
    assert init_result["capabilities"] == {}


@pytest.mark.asyncio
async def test_mcp_server_register_tool_with_title() -> None:
    """register_tool with title exposes it in tools/list."""
    server = MCPServer(name="t", version="0.1.0")
    server.register_tool(
        "echo",
        lambda message: message,
        {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
        description="Echo back",
        title="Echo Tool",
    )
    list_result = server._handle_tools_list(None)
    assert list_result["tools"][0]["title"] == "Echo Tool"


@pytest.mark.asyncio
async def test_mcp_server_dispatch_notification_initialized() -> None:
    """Notification notifications/initialized is accepted (no response)."""
    from asap.mcp.protocol import JSONRPCNotification

    server = MCPServer(name="t", version="0.1.0")
    notif = JSONRPCNotification(method="notifications/initialized")
    server._dispatch_notification(notif)


@pytest.mark.asyncio
async def test_mcp_server_dispatch_notification_cancelled() -> None:
    """Notification notifications/cancelled is accepted (no response)."""
    from asap.mcp.protocol import JSONRPCNotification

    server = MCPServer(name="t", version="0.1.0")
    notif = JSONRPCNotification(method="notifications/cancelled", params={"requestId": 1})
    server._dispatch_notification(notif)
