"""JSON-RPC 2.0 wrapper models for ASAP protocol transport.

This module implements JSON-RPC 2.0 specification (https://www.jsonrpc.org/specification)
to wrap ASAP Envelope messages for HTTP transport.

The JSON-RPC layer provides:
- Standard request/response structure
- Error handling with standard error codes
- Request/response correlation via id field

Standard JSON-RPC Error Codes:
    -32700: Parse error (invalid JSON)
    -32600: Invalid request (malformed JSON-RPC)
    -32601: Method not found
    -32602: Invalid params
    -32603: Internal error

Example:
    >>> from asap.models import Envelope, TaskRequest
    >>> from asap.transport.jsonrpc import JsonRpcRequest
    >>>
    >>> # Create ASAP envelope
    >>> envelope = Envelope(
    ...     sender="urn:asap:agent:client",
    ...     recipient="urn:asap:agent:server",
    ...     payload_type="task.request",
    ...     payload=TaskRequest(...)
    ... )
    >>>
    >>> # Wrap in JSON-RPC
    >>> rpc_request = JsonRpcRequest(
    ...     method="asap.send",
    ...     params={"envelope": envelope.model_dump()},
    ...     id="req-1"
    ... )
"""

from typing import Any, Literal

from pydantic import Field

from asap.models.base import ASAPBaseModel

# JSON-RPC 2.0 Standard Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# ASAP Protocol JSON-RPC Method Name
ASAP_METHOD = "asap.send"

# Error code descriptions
ERROR_MESSAGES: dict[int, str] = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
}


class JsonRpcError(ASAPBaseModel):
    """JSON-RPC 2.0 error object.

    Represents an error that occurred during request processing.
    Follows JSON-RPC 2.0 specification for error responses.

    Attributes:
        code: Integer error code (standard or application-defined)
        message: Short error description
        data: Optional additional error information

    Example:
        >>> error = JsonRpcError(
        ...     code=-32602,
        ...     message="Invalid params",
        ...     data={"missing_field": "task_id"}
        ... )
        >>> error.code
        -32602
    """

    code: int = Field(description="Error code (negative integer)")
    message: str = Field(description="Short error description")
    data: dict[str, Any] | None = Field(
        default=None, description="Optional additional error information"
    )

    @staticmethod
    def from_code(code: int, data: dict[str, Any] | None = None) -> "JsonRpcError":
        """Create error from standard error code.

        Args:
            code: Standard JSON-RPC error code
            data: Optional additional error information

        Returns:
            JsonRpcError instance with standard message

        Example:
            >>> error = JsonRpcError.from_code(INVALID_PARAMS, data={"field": "task_id"})
            >>> error.message
            'Invalid params'
        """
        message = ERROR_MESSAGES.get(code, "Unknown error")
        return JsonRpcError(code=code, message=message, data=data)


class JsonRpcRequest(ASAPBaseModel):
    """JSON-RPC 2.0 request.

    Wraps an ASAP Envelope in a JSON-RPC request structure.
    The envelope is passed in the params field.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        method: RPC method name (typically "asap.send")
        params: Request parameters (contains ASAP envelope)
        id: Request identifier for correlation

    Example:
        >>> request = JsonRpcRequest(
        ...     method="asap.send",
        ...     params={"envelope": {...}},
        ...     id="req-123"
        ... )
        >>> request.jsonrpc
        '2.0'
    """

    jsonrpc: Literal["2.0"] = Field(
        default="2.0", description="JSON-RPC protocol version (always '2.0')"
    )
    method: str = Field(description="RPC method name")
    params: dict[str, Any] = Field(description="Request parameters")
    id: str | int = Field(description="Request identifier for correlation")


class JsonRpcResponse(ASAPBaseModel):
    """JSON-RPC 2.0 successful response.

    Wraps an ASAP Envelope response or other result data.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        result: Response data (ASAP envelope or other result)
        id: Request identifier (matches original request)

    Example:
        >>> response = JsonRpcResponse(
        ...     result={"envelope": {...}},
        ...     id="req-123"
        ... )
        >>> response.jsonrpc
        '2.0'
    """

    jsonrpc: Literal["2.0"] = Field(
        default="2.0", description="JSON-RPC protocol version (always '2.0')"
    )
    result: dict[str, Any] = Field(description="Response data")
    id: str | int = Field(description="Request identifier (matches request)")


class JsonRpcErrorResponse(ASAPBaseModel):
    """JSON-RPC 2.0 error response.

    Returned when a request fails or cannot be processed.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        error: Error object with code, message, and optional data
        id: Request identifier (matches request, or null if id unavailable)

    Example:
        >>> error_response = JsonRpcErrorResponse(
        ...     error=JsonRpcError(code=-32602, message="Invalid params"),
        ...     id="req-123"
        ... )
        >>> error_response.error.code
        -32602
    """

    jsonrpc: Literal["2.0"] = Field(
        default="2.0", description="JSON-RPC protocol version (always '2.0')"
    )
    error: JsonRpcError = Field(description="Error object")
    id: str | int | None = Field(description="Request identifier (or null)")
