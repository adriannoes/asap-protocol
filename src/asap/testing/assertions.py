"""Custom assertions for ASAP protocol tests.

This module provides assertion helpers to validate envelopes and
task outcomes with clear error messages.

Functions:
    assert_envelope_valid: Assert an Envelope has required fields and valid shape.
    assert_task_completed: Assert a TaskResponse or envelope payload indicates
                           task completion (e.g. status completed).
    assert_response_correlates: Assert response envelope correlates to request.
"""

from typing import Any

from asap.models.envelope import Envelope


def assert_envelope_valid(
    envelope: Envelope,
    *,
    require_id: bool = True,
    require_timestamp: bool = True,
    allowed_payload_types: list[str] | None = None,
) -> None:
    """Assert that an envelope has required fields and valid structure.

    Args:
        envelope: The envelope to validate.
        require_id: If True, envelope.id must be non-empty.
        require_timestamp: If True, envelope.timestamp must be set.
        allowed_payload_types: If set, payload_type must be in this list.

    Raises:
        AssertionError: If any check fails.
    """
    assert envelope is not None, "Envelope must not be None"
    if require_id:
        assert envelope.id, "Envelope must have a non-empty id"
    if require_timestamp:
        assert envelope.timestamp is not None, "Envelope must have a timestamp"
    assert envelope.sender, "Envelope must have a sender"
    assert envelope.recipient, "Envelope must have a recipient"
    assert envelope.payload_type, "Envelope must have a payload_type"
    assert envelope.payload is not None, "Envelope must have a payload"
    if allowed_payload_types is not None:
        assert envelope.payload_type in allowed_payload_types, (
            f"payload_type {envelope.payload_type!r} not in {allowed_payload_types}"
        )


def assert_task_completed(
    payload: dict[str, Any] | Envelope,
    *,
    status_key: str = "status",
    completed_value: str = "completed",
) -> None:
    """Assert that a task response indicates completion.

    Accepts either a TaskResponse-like dict (with status_key) or an
    Envelope whose payload is such a dict.

    Args:
        payload: TaskResponse payload dict or Envelope containing it.
        status_key: Key in payload that holds status (default 'status').
        completed_value: Value that indicates completion (default 'completed').

    Raises:
        AssertionError: If payload does not indicate completion.
    """
    if isinstance(payload, Envelope):
        payload = payload.payload or {}
    assert isinstance(payload, dict), "payload must be a dict or Envelope"
    actual = payload.get(status_key)
    assert actual == completed_value, f"Expected task status {completed_value!r}, got {actual!r}"


def assert_response_correlates(
    request_envelope: Envelope,
    response_envelope: Envelope,
    *,
    correlation_id_field: str = "correlation_id",
) -> None:
    """Assert that a response envelope correlates to the request (by correlation id).

    Args:
        request_envelope: The request envelope (must have id).
        response_envelope: The response envelope (must have correlation_id).
        correlation_id_field: Attribute name on response for correlation (default
            'correlation_id').

    Raises:
        AssertionError: If request id or response correlation_id is missing or
            they do not match.
    """
    assert request_envelope.id, "Request envelope must have a non-empty id"
    correlation_id = getattr(response_envelope, correlation_id_field, None)
    assert correlation_id is not None, f"Response envelope must have {correlation_id_field!r}"
    assert correlation_id == request_envelope.id, (
        f"Response {correlation_id_field!r} {correlation_id!r} does not match "
        f"request id {request_envelope.id!r}"
    )


__all__ = [
    "assert_envelope_valid",
    "assert_task_completed",
    "assert_response_correlates",
]
