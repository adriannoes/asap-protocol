"""MCP protocol types (spec 2025-11-25).

JSON-RPC 2.0 and MCP message types for initialize, tools/list, and tools/call.
Models use extra="ignore" for forward compatibility with future spec fields.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Protocol version supported by this implementation
MCP_PROTOCOL_VERSION = "2025-11-25"

# JSON-RPC 2.0 standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _mcp_model_config() -> ConfigDict:
    """Pydantic config for MCP models: allow extra fields for forward compatibility."""
    return ConfigDict(extra="ignore", populate_by_name=True)


# --- JSON-RPC 2.0 ---


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""

    model_config = _mcp_model_config()

    code: int = Field(description="Error code (integer)")
    message: str = Field(description="Short error description")
    data: Any = Field(default=None, description="Optional additional data")


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request (has id, expects response)."""

    model_config = _mcp_model_config()

    jsonrpc: Literal["2.0"] = Field(default="2.0")
    id: str | int = Field(description="Request id (must not be null)")
    method: str = Field(description="Method name")
    params: dict[str, Any] | None = Field(default=None)


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 success response."""

    model_config = _mcp_model_config()

    jsonrpc: Literal["2.0"] = Field(default="2.0")
    id: str | int = Field(description="Same id as request")
    result: dict[str, Any] = Field(description="Result payload")


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response."""

    model_config = _mcp_model_config()

    jsonrpc: Literal["2.0"] = Field(default="2.0")
    id: str | int | None = Field(description="Same id as request, or null")
    error: JSONRPCError = Field(description="Error object")


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id, no response)."""

    model_config = _mcp_model_config()

    jsonrpc: Literal["2.0"] = Field(default="2.0")
    method: str = Field(description="Method name")
    params: dict[str, Any] | None = Field(default=None)


# --- Implementation (clientInfo / serverInfo) ---


class Implementation(BaseModel):
    """MCP implementation info (client or server)."""

    model_config = _mcp_model_config()

    name: str = Field(description="Programmatic name")
    version: str = Field(description="Version string")
    title: str | None = Field(default=None, description="Human-readable title")
    description: str | None = Field(default=None)
    icons: list[dict[str, Any]] | None = Field(default=None)
    website_url: str | None = Field(default=None, alias="websiteUrl")


# --- Initialize ---


class InitializeRequestParams(BaseModel):
    """Params for initialize request."""

    model_config = _mcp_model_config()

    protocol_version: str = Field(alias="protocolVersion")
    capabilities: dict[str, Any] = Field(default_factory=dict)
    client_info: Implementation = Field(alias="clientInfo")


class InitializeResult(BaseModel):
    """Result of initialize (server response)."""

    model_config = _mcp_model_config()

    protocol_version: str = Field(alias="protocolVersion", default=MCP_PROTOCOL_VERSION)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    server_info: Implementation = Field(alias="serverInfo")
    instructions: str | None = Field(default=None)


# --- Tools ---


class Tool(BaseModel):
    """MCP tool definition (tools/list item)."""

    model_config = _mcp_model_config()

    name: str = Field(description="Unique tool name")
    description: str = Field(description="Human-readable description")
    input_schema: dict[str, Any] = Field(
        alias="inputSchema",
        description="JSON Schema for parameters (object, not null)",
    )
    title: str | None = Field(default=None)
    icons: list[dict[str, Any]] | None = Field(default=None)
    output_schema: dict[str, Any] | None = Field(default=None, alias="outputSchema")
    annotations: dict[str, Any] | None = Field(default=None)


class TextContent(BaseModel):
    """Text content item in tool result."""

    model_config = _mcp_model_config()

    type: Literal["text"] = Field(default="text")
    text: str = Field(description="Text content")
    annotations: dict[str, Any] | None = Field(default=None)


class CallToolRequestParams(BaseModel):
    """Params for tools/call request."""

    model_config = _mcp_model_config()

    name: str = Field(description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class CallToolResult(BaseModel):
    """Result of tools/call (content + isError)."""

    model_config = _mcp_model_config()

    content: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Content blocks (e.g. TextContent)",
    )
    is_error: bool = Field(default=False, alias="isError")
    structured_content: dict[str, Any] | None = Field(default=None, alias="structuredContent")


class ListToolsResult(BaseModel):
    """Result of tools/list."""

    model_config = _mcp_model_config()

    tools: list[Tool] = Field(default_factory=list)
    next_cursor: str | None = Field(default=None, alias="nextCursor")
