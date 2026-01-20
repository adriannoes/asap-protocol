"""Tests for JSON-RPC 2.0 models.

Tests cover:
- Request/response serialization
- Error code mapping
- Protocol version validation
- Field validation
"""

from typing import Any

import pytest
from pydantic import ValidationError

from asap.transport.jsonrpc import (
    ERROR_MESSAGES,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcError,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)


class TestJsonRpcError:
    """Tests for JsonRpcError model."""

    def test_create_error(self) -> None:
        """Test creating a basic error object."""
        error = JsonRpcError(
            code=-32602,
            message="Invalid params",
        )

        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data is None

    def test_create_error_with_data(self) -> None:
        """Test creating error with additional data."""
        error = JsonRpcError(
            code=-32602,
            message="Invalid params",
            data={"missing_field": "task_id", "provided": None},
        )

        assert error.code == -32602
        assert error.data == {"missing_field": "task_id", "provided": None}

    def test_from_code_standard_errors(self) -> None:
        """Test creating errors from standard error codes."""
        # Test all standard error codes
        test_cases = [
            (PARSE_ERROR, "Parse error"),
            (INVALID_REQUEST, "Invalid request"),
            (METHOD_NOT_FOUND, "Method not found"),
            (INVALID_PARAMS, "Invalid params"),
            (INTERNAL_ERROR, "Internal error"),
        ]

        for code, expected_message in test_cases:
            error = JsonRpcError.from_code(code)
            assert error.code == code
            assert error.message == expected_message
            assert error.data is None

    def test_from_code_with_data(self) -> None:
        """Test from_code with additional data."""
        error = JsonRpcError.from_code(
            INVALID_PARAMS, data={"field": "task_id", "reason": "missing"}
        )

        assert error.code == INVALID_PARAMS
        assert error.message == ERROR_MESSAGES[INVALID_PARAMS]
        assert error.data == {"field": "task_id", "reason": "missing"}

    def test_from_code_unknown_code(self) -> None:
        """Test from_code with non-standard error code."""
        error = JsonRpcError.from_code(-40000)

        assert error.code == -40000
        assert error.message == "Unknown error"

    def test_error_serialization(self) -> None:
        """Test error serializes to valid JSON."""
        error = JsonRpcError(
            code=-32603,
            message="Internal error",
            data={"exception": "ValueError"},
        )

        data = error.model_dump()

        assert data == {
            "code": -32603,
            "message": "Internal error",
            "data": {"exception": "ValueError"},
        }

    def test_error_immutability(self) -> None:
        """Test error objects are immutable (frozen)."""
        error = JsonRpcError(code=-32603, message="Internal error")

        with pytest.raises(ValidationError):
            error.code = -32700  # type: ignore[misc]


class TestJsonRpcRequest:
    """Tests for JsonRpcRequest model."""

    def test_create_request(self) -> None:
        """Test creating a basic request."""
        request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": {"sender": "urn:asap:agent:test"}},
            id="req-1",
        )

        assert request.jsonrpc == "2.0"
        assert request.method == "asap.send"
        assert request.params == {"envelope": {"sender": "urn:asap:agent:test"}}
        assert request.id == "req-1"

    def test_request_with_integer_id(self) -> None:
        """Test request with integer id."""
        request = JsonRpcRequest(
            method="asap.send",
            params={},
            id=123,
        )

        assert request.id == 123
        assert isinstance(request.id, int)

    def test_jsonrpc_version_auto_set(self) -> None:
        """Test jsonrpc version is automatically set to 2.0."""
        request = JsonRpcRequest(
            method="test",
            params={},
            id=1,
        )

        assert request.jsonrpc == "2.0"

    def test_invalid_jsonrpc_version(self) -> None:
        """Test that invalid jsonrpc version is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            JsonRpcRequest(
                jsonrpc="1.0",  # type: ignore[arg-type]
                method="test",
                params={},
                id=1,
            )

        assert "jsonrpc" in str(exc_info.value)

    def test_request_serialization(self) -> None:
        """Test request serializes to valid JSON-RPC format."""
        request = JsonRpcRequest(
            method="asap.send",
            params={"key": "value"},
            id="test-id",
        )

        data = request.model_dump()

        assert data == {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"key": "value"},
            "id": "test-id",
        }

    def test_request_deserialization(self) -> None:
        """Test deserializing request from dict."""
        data = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": {}},
            "id": 42,
        }

        request = JsonRpcRequest(**data)

        assert request.method == "asap.send"
        assert request.id == 42

    def test_request_requires_all_fields(self) -> None:
        """Test request requires all mandatory fields."""
        with pytest.raises(ValidationError):
            JsonRpcRequest(method="test", params={})  # type: ignore[call-arg]

    def test_request_immutability(self) -> None:
        """Test request objects are immutable."""
        request = JsonRpcRequest(method="test", params={}, id=1)

        with pytest.raises(ValidationError):
            request.method = "new_method"  # type: ignore[misc]


class TestJsonRpcResponse:
    """Tests for JsonRpcResponse model."""

    def test_create_response(self) -> None:
        """Test creating a basic response."""
        response = JsonRpcResponse(
            result={"envelope": {"id": "env-123"}},
            id="req-1",
        )

        assert response.jsonrpc == "2.0"
        assert response.result == {"envelope": {"id": "env-123"}}
        assert response.id == "req-1"

    def test_response_with_integer_id(self) -> None:
        """Test response with integer id."""
        response = JsonRpcResponse(
            result={"status": "ok"},
            id=456,
        )

        assert response.id == 456
        assert isinstance(response.id, int)

    def test_response_serialization(self) -> None:
        """Test response serializes to valid JSON-RPC format."""
        response = JsonRpcResponse(
            result={"data": "test"},
            id="resp-1",
        )

        data = response.model_dump()

        assert data == {
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "id": "resp-1",
        }

    def test_response_deserialization(self) -> None:
        """Test deserializing response from dict."""
        data = {
            "jsonrpc": "2.0",
            "result": {"success": True},
            "id": "test-123",
        }

        response = JsonRpcResponse(**data)

        assert response.result == {"success": True}
        assert response.id == "test-123"

    def test_response_requires_all_fields(self) -> None:
        """Test response requires all mandatory fields."""
        with pytest.raises(ValidationError):
            JsonRpcResponse(result={})  # type: ignore[call-arg]

    def test_response_immutability(self) -> None:
        """Test response objects are immutable."""
        response = JsonRpcResponse(result={}, id=1)

        with pytest.raises(ValidationError):
            response.id = 2  # type: ignore[misc]


class TestJsonRpcErrorResponse:
    """Tests for JsonRpcErrorResponse model."""

    def test_create_error_response(self) -> None:
        """Test creating an error response."""
        error = JsonRpcError(code=-32602, message="Invalid params")
        response = JsonRpcErrorResponse(
            error=error,
            id="req-1",
        )

        assert response.jsonrpc == "2.0"
        assert response.error.code == -32602
        assert response.error.message == "Invalid params"
        assert response.id == "req-1"

    def test_error_response_with_null_id(self) -> None:
        """Test error response with null id (when request id unavailable)."""
        error = JsonRpcError(code=PARSE_ERROR, message="Parse error")
        response = JsonRpcErrorResponse(
            error=error,
            id=None,
        )

        assert response.id is None
        assert response.error.code == PARSE_ERROR

    def test_error_response_serialization(self) -> None:
        """Test error response serializes correctly."""
        error = JsonRpcError(
            code=-32603, message="Internal error", data={"detail": "Server crashed"}
        )
        response = JsonRpcErrorResponse(error=error, id=123)

        data = response.model_dump()

        assert data == {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"detail": "Server crashed"},
            },
            "id": 123,
        }

    def test_error_response_deserialization(self) -> None:
        """Test deserializing error response from dict."""
        data = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": None,
            },
            "id": "test",
        }

        response = JsonRpcErrorResponse(**data)

        assert response.error.code == -32601
        assert response.error.message == "Method not found"
        assert response.id == "test"

    def test_error_response_immutability(self) -> None:
        """Test error response objects are immutable."""
        error = JsonRpcError(code=-32603, message="Error")
        response = JsonRpcErrorResponse(error=error, id=1)

        with pytest.raises(ValidationError):
            response.id = 2  # type: ignore[misc]


class TestJsonRpcIntegration:
    """Integration tests for JSON-RPC workflow."""

    def test_request_response_correlation(self) -> None:
        """Test that request and response ids match."""
        request_id = "correlation-test-123"

        request = JsonRpcRequest(
            method="asap.send",
            params={"test": "data"},
            id=request_id,
        )

        response = JsonRpcResponse(
            result={"processed": True},
            id=request_id,
        )

        assert request.id == response.id

    def test_error_code_mapping_complete(self) -> None:
        """Test all standard error codes are mapped."""
        expected_codes = [
            PARSE_ERROR,
            INVALID_REQUEST,
            METHOD_NOT_FOUND,
            INVALID_PARAMS,
            INTERNAL_ERROR,
        ]

        for code in expected_codes:
            assert code in ERROR_MESSAGES
            error = JsonRpcError.from_code(code)
            assert error.message == ERROR_MESSAGES[code]

    def test_round_trip_request(self) -> None:
        """Test serialization and deserialization of request."""
        original = JsonRpcRequest(
            method="test.method",
            params={"key": "value", "nested": {"inner": 42}},
            id="round-trip-1",
        )

        # Serialize to dict (simulating JSON)
        data = original.model_dump()

        # Deserialize back
        restored = JsonRpcRequest(**data)

        assert restored.method == original.method
        assert restored.params == original.params
        assert restored.id == original.id
        assert restored.jsonrpc == original.jsonrpc

    def test_round_trip_response(self) -> None:
        """Test serialization and deserialization of response."""
        original = JsonRpcResponse(
            result={"status": "success", "data": [1, 2, 3]},
            id=999,
        )

        data = original.model_dump()
        restored = JsonRpcResponse(**data)

        assert restored.result == original.result
        assert restored.id == original.id

    def test_round_trip_error_response(self) -> None:
        """Test serialization and deserialization of error response."""
        error = JsonRpcError.from_code(INTERNAL_ERROR, data={"trace": "..."})
        original = JsonRpcErrorResponse(error=error, id="error-1")

        data = original.model_dump()
        restored = JsonRpcErrorResponse(**data)

        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.data == original.error.data
        assert restored.id == original.id
