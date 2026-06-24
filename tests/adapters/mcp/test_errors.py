"""Unit tests for MCP auth error helpers."""

from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
    INVALID_TOKEN,
    tool_error_result,
)


def test_error_code_constants() -> None:
    """ASAP MCP error codes use asap: namespace prefix."""
    assert AUTH_REQUIRED == "asap:auth_required"
    assert INVALID_TOKEN == "asap:invalid_token"
    assert CAPABILITY_DENIED == "asap:capability_denied"
    assert CONSTRAINT_VIOLATION == "asap:constraint_violation"


def test_tool_error_result_is_error_shape() -> None:
    """tool_error_result returns CallToolResult-shaped dict with isError true."""
    result = tool_error_result(AUTH_REQUIRED)
    assert result["isError"] is True
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"] == "asap:auth_required"


def test_tool_error_result_includes_detail() -> None:
    """tool_error_result appends detail after the code."""
    result = tool_error_result(CAPABILITY_DENIED, "grant missing for web_search")
    assert result["isError"] is True
    assert result["content"][0]["text"] == ("asap:capability_denied: grant missing for web_search")
