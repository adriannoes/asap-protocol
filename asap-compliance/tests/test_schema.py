"""Tests for schema validator - envelope and payload compliance."""

from __future__ import annotations

from asap_compliance.validators.handshake import CheckResult
from asap_compliance.validators.schema import (
    SchemaResult,
    validate_envelope,
    validate_payload,
    validate_schema,
    validate_unknown_fields_rejected,
)


def _minimal_envelope(
    payload_type: str = "task.request",
    payload: dict[str, object] | None = None,
    correlation_id: str | None = None,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build minimal valid envelope dict."""
    base: dict[str, object] = {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:test",
        "recipient": "urn:asap:agent:echo",
        "payload_type": payload_type,
        "payload": payload
        or {
            "conversation_id": "conv_01HX5K3MQVN8",
            "skill_id": "echo",
            "input": {},
        },
    }
    if correlation_id is not None:
        base["correlation_id"] = correlation_id
    if extensions is not None:
        base["extensions"] = extensions
    return base


def _minimal_task_response() -> dict[str, object]:
    """Minimal valid TaskResponse payload."""
    return {
        "task_id": "task_01HX5K4N",
        "status": "completed",
        "result": {"summary": "done"},
    }


def _minimal_mcp_tool_result(success: bool = True) -> dict[str, object]:
    """Minimal McpToolResult payload."""
    if success:
        return {"request_id": "req_1", "success": True, "result": {}}
    return {"request_id": "req_1", "success": False, "error": "Tool failed"}


def _minimal_message_ack(status: str = "received", error: str | None = None) -> dict[str, object]:
    """Minimal MessageAck payload."""
    d: dict[str, object] = {"original_envelope_id": "env_1", "status": status}
    if error is not None:
        d["error"] = error
    return d


class TestEnvelopeValidation:
    """Tests for envelope structure validation."""

    def test_envelope_valid_minimal(self) -> None:
        """Minimal valid envelope passes."""
        data = _minimal_envelope()
        passed, results = validate_envelope(data)
        assert passed
        assert all(r.passed for r in results)

    def test_envelope_missing_required_fields(self) -> None:
        """Envelope with missing required fields fails."""
        data = {"asap_version": "0.1", "sender": "urn:asap:agent:a"}
        passed, results = validate_envelope(data)
        assert not passed
        failed = [r for r in results if not r.passed]
        assert len(failed) >= 1
        assert "recipient" in failed[0].message or "Missing" in failed[0].message

    def test_envelope_payload_not_dict(self) -> None:
        """Envelope with non-dict payload fails."""
        data = _minimal_envelope()
        data["payload"] = "not-a-dict"
        passed, results = validate_envelope(data)
        assert not passed

    def test_envelope_invalid_urn(self) -> None:
        """Envelope with invalid sender URN fails."""
        data = _minimal_envelope()
        data["sender"] = "invalid-urn"
        passed, results = validate_envelope(data)
        assert not passed

    def test_envelope_task_response_requires_correlation_id(self) -> None:
        """TaskResponse envelope without correlation_id fails.

        Envelope model requires correlation_id when payload_type is TaskResponse
        (PascalCase, as in the model validator).
        """
        data = _minimal_envelope(
            payload_type="TaskResponse",
            payload=_minimal_task_response(),
        )
        passed, results = validate_envelope(data)
        assert not passed


class TestPayloadValidation:
    """Tests for payload schema validation."""

    def test_task_request_valid(self) -> None:
        """Valid TaskRequest payload passes."""
        payload = {
            "conversation_id": "conv_1",
            "skill_id": "echo",
            "input": {"x": 1},
        }
        passed, results = validate_payload(payload, "task.request")
        assert passed
        assert all(r.passed for r in results)

    def test_task_request_dot_notation(self) -> None:
        """task.request and TaskRequest both resolve to TaskRequest."""
        payload = {"conversation_id": "conv_1", "skill_id": "x", "input": {}}
        p1, _ = validate_payload(payload, "task.request")
        p2, _ = validate_payload(payload, "TaskRequest")
        assert p1 and p2

    def test_task_response_valid(self) -> None:
        """Valid TaskResponse payload passes."""
        payload = _minimal_task_response()
        passed, results = validate_payload(payload, "task.response")
        assert passed

    def test_task_response_invalid_status(self) -> None:
        """TaskResponse with invalid status fails."""
        payload = _minimal_task_response()
        payload["status"] = "invalid_status"
        passed, results = validate_payload(payload, "task.response")
        assert not passed

    def test_mcp_tool_result_success_requires_result(self) -> None:
        """McpToolResult with success=True must have result."""
        payload = {"request_id": "r1", "success": True}
        passed, _ = validate_payload(payload, "mcp.tool_result")
        assert not passed

    def test_mcp_tool_result_failure_requires_error(self) -> None:
        """McpToolResult with success=False must have error."""
        payload = {"request_id": "r1", "success": False}
        passed, _ = validate_payload(payload, "mcp.tool_result")
        assert not passed

    def test_message_ack_with_error(self) -> None:
        """MessageAck with status=rejected can have error."""
        payload = _minimal_message_ack(status="rejected", error="Invalid input")
        passed, _ = validate_payload(payload, "message.ack")
        assert passed

    def test_unknown_payload_type_fails(self) -> None:
        """Unknown payload_type fails."""
        passed, results = validate_payload({}, "unknown.type")
        assert not passed
        assert any("Unknown" in r.message for r in results)


class TestExtensionHandling:
    """Tests for extension field handling."""

    def test_extensions_optional(self) -> None:
        """Envelope without extensions passes."""
        data = _minimal_envelope()
        assert "extensions" not in data
        result = validate_schema(data)
        assert result.envelope_ok

    def test_extensions_passed_through(self) -> None:
        """Envelope with extensions dict passes."""
        data = _minimal_envelope(extensions={"custom": "value", "nonce": "abc123"})
        result = validate_schema(data)
        assert result.envelope_ok


class TestUnknownFieldsRejected:
    """Tests that extra/unknown fields are rejected."""

    def test_task_request_rejects_unknown_fields(self) -> None:
        """TaskRequest payload with extra field is rejected (extra='forbid')."""
        payload = {"conversation_id": "conv_1", "skill_id": "x", "input": {}}
        results = validate_unknown_fields_rejected(payload, "task.request")
        check = next(r for r in results if r.name == "unknown_fields_rejected")
        assert check.passed

    def test_envelope_extra_fields_rejected(self) -> None:
        """Envelope with extra top-level field fails."""
        data = _minimal_envelope()
        data["_extra"] = "forbidden"
        passed, _ = validate_envelope(data)
        assert not passed


class TestFullSchemaValidation:
    """Tests for validate_schema integration."""

    def test_full_valid_envelope_passes(self) -> None:
        """Complete valid envelope passes all checks."""
        data = _minimal_envelope()
        result = validate_schema(data)
        assert result.passed
        assert result.envelope_ok
        assert result.payload_ok

    def test_full_invalid_envelope_fails(self) -> None:
        """Invalid envelope fails."""
        data = {"asap_version": "0.1"}
        result = validate_schema(data)
        assert not result.passed
        assert not result.envelope_ok

    def test_known_bad_payloads_rejected(self) -> None:
        """Known-bad payloads are rejected."""
        bad_cases = [
            (_minimal_envelope(payload={"x": "missing required"}), "missing fields"),
            (
                _minimal_envelope(payload={"conversation_id": 123, "skill_id": "x", "input": {}}),
                "wrong type",
            ),
            (
                _minimal_envelope(
                    payload_type="TaskResponse",
                    payload={"task_id": "t1", "status": "completed"},
                ),
                "TaskResponse needs correlation_id in envelope",
            ),
        ]
        for data, _desc in bad_cases:
            result = validate_schema(data)
            assert not result.passed, f"Expected failure for: {_desc}"


class TestSchemaResult:
    """Tests for SchemaResult model."""

    def test_passed_true_when_all_ok(self) -> None:
        """passed is True when envelope and payload ok."""
        result = SchemaResult(
            envelope_ok=True,
            payload_ok=True,
            checks=[CheckResult("x", True, "ok")],
        )
        assert result.passed

    def test_passed_false_when_envelope_fails(self) -> None:
        """passed is False when envelope fails."""
        result = SchemaResult(envelope_ok=False, payload_ok=True, checks=[])
        assert not result.passed
