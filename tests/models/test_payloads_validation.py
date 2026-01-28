"""Tests for McpToolResult validation edge cases in payloads.py.

These tests cover lines 347, 349, 352, 354 - the McpToolResult validator.
"""

import pytest

from asap.models.payloads import McpToolResult


class TestMcpToolResultValidation:
    """Tests for McpToolResult result/error mutual exclusivity validation."""

    def test_success_true_requires_result(self) -> None:
        """Line 347: success=True with result=None should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            McpToolResult(
                request_id="req_123",
                success=True,
                result=None,  # Invalid: should have result
                error=None,
            )

        assert "result must be provided when success=True" in str(exc_info.value)

    def test_success_true_error_must_be_none(self) -> None:
        """Line 349: success=True with error set should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            McpToolResult(
                request_id="req_123",
                success=True,
                result={"data": "ok"},
                error="Some error",  # Invalid: should be None
            )

        assert "error must be None when success=True" in str(exc_info.value)

    def test_success_false_requires_error(self) -> None:
        """Line 352: success=False with error=None should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            McpToolResult(
                request_id="req_123",
                success=False,
                result=None,
                error=None,  # Invalid: should have error
            )

        assert "error must be provided when success=False" in str(exc_info.value)

    def test_success_false_result_must_be_none(self) -> None:
        """Line 354: success=False with result set should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            McpToolResult(
                request_id="req_123",
                success=False,
                result={"data": "should not be here"},  # Invalid: should be None
                error="Some error",
            )

        assert "result must be None when success=False" in str(exc_info.value)

    def test_valid_success_response(self) -> None:
        """Valid success response should pass validation."""
        result = McpToolResult(
            request_id="req_123",
            success=True,
            result={"findings": ["finding1", "finding2"]},
            error=None,
        )
        assert result.success is True
        assert result.result == {"findings": ["finding1", "finding2"]}
        assert result.error is None

    def test_valid_failure_response(self) -> None:
        """Valid failure response should pass validation."""
        result = McpToolResult(
            request_id="req_123",
            success=False,
            result=None,
            error="Tool execution failed: timeout",
        )
        assert result.success is False
        assert result.result is None
        assert result.error == "Tool execution failed: timeout"
