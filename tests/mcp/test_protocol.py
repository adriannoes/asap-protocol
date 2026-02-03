"""Unit tests for MCP protocol models (spec 2025-11-25)."""

from asap.mcp.protocol import (
    MCP_PROTOCOL_VERSION,
    CallToolRequestParams,
    CallToolResult,
    Implementation,
    InitializeResult,
    ListToolsResult,
    TextContent,
    Tool,
)


def test_protocol_version() -> None:
    """Protocol version is 2025-11-25."""
    assert MCP_PROTOCOL_VERSION == "2025-11-25"


def test_implementation_serialization() -> None:
    """Implementation serializes with camelCase aliases."""
    impl = Implementation(name="test", version="1.0.0", title="Test")
    d = impl.model_dump(by_alias=True, exclude_none=True)
    assert d["name"] == "test"
    assert d["version"] == "1.0.0"
    assert d["title"] == "Test"
    assert "websiteUrl" not in d


def test_tool_serialization() -> None:
    """Tool has name, description, inputSchema and optional title."""
    tool = Tool(
        name="echo",
        description="Echo back",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        title="Echo",
    )
    d = tool.model_dump(by_alias=True, exclude_none=True)
    assert d["name"] == "echo"
    assert d["description"] == "Echo back"
    assert d["inputSchema"]["type"] == "object"
    assert d["title"] == "Echo"


def test_text_content() -> None:
    """TextContent has type text and text field."""
    tc = TextContent(text="hello")
    assert tc.type == "text"
    assert tc.text == "hello"
    d = tc.model_dump(by_alias=True)
    assert d["type"] == "text"
    assert d["text"] == "hello"


def test_call_tool_result() -> None:
    """CallToolResult has content list and isError."""
    result = CallToolResult(
        content=[{"type": "text", "text": "ok"}],
        is_error=False,
    )
    assert result.is_error is False
    assert len(result.content) == 1
    assert result.content[0]["text"] == "ok"
    d = result.model_dump(by_alias=True, exclude_none=True)
    assert d["isError"] is False


def test_call_tool_request_params() -> None:
    """CallToolRequestParams accepts name and arguments."""
    params = CallToolRequestParams(name="echo", arguments={"message": "hi"})
    assert params.name == "echo"
    assert params.arguments == {"message": "hi"}


def test_initialize_result() -> None:
    """InitializeResult has protocolVersion, capabilities, serverInfo."""
    impl = Implementation(name="srv", version="1.0.0")
    result = InitializeResult(
        protocol_version=MCP_PROTOCOL_VERSION,
        capabilities={"tools": {"listChanged": True}},
        server_info=impl,
    )
    d = result.model_dump(by_alias=True, exclude_none=True)
    assert d["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert d["capabilities"]["tools"]["listChanged"] is True
    assert d["serverInfo"]["name"] == "srv"


def test_list_tools_result() -> None:
    """ListToolsResult has tools array."""
    tool = Tool(name="t", description="d", input_schema={"type": "object"})
    result = ListToolsResult(tools=[tool])
    assert len(result.tools) == 1
    assert result.tools[0].name == "t"


def test_initialize_result_parses_from_camelcase() -> None:
    """InitializeResult can be parsed from server response (camelCase keys)."""
    raw = {
        "protocolVersion": "2025-11-25",
        "capabilities": {"tools": {"listChanged": True}},
        "serverInfo": {"name": "test-server", "version": "1.0.0"},
    }
    result = InitializeResult.model_validate(raw)
    assert result.protocol_version == "2025-11-25"
    assert result.server_info.name == "test-server"
    assert result.server_info.version == "1.0.0"
    assert result.capabilities.get("tools", {}).get("listChanged") is True
