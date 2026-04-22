"""Custom assertions for ASAP protocol tests.

This module provides assertion helpers to validate envelopes and
task outcomes with clear error messages.

Functions:
    assert_envelope_valid: Assert an Envelope has required fields and valid shape.
    assert_task_completed: Assert a TaskResponse or envelope payload indicates
                           task completion (e.g. status completed).
    assert_response_correlates: Assert response envelope correlates to request.
"""

from __future__ import annotations

from typing import Any

from asap.models.envelope import Envelope


def _fail(message: str) -> None:
    raise AssertionError(message)


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
    if envelope is None:
        _fail("Envelope must not be None")
    if require_id and not envelope.id:
        _fail("Envelope must have a non-empty id")
    if require_timestamp and envelope.timestamp is None:
        _fail("Envelope must have a timestamp")
    if not envelope.sender:
        _fail("Envelope must have a sender")
    if not envelope.recipient:
        _fail("Envelope must have a recipient")
    if not envelope.payload_type:
        _fail("Envelope must have a payload_type")
    if envelope.payload is None:
        _fail("Envelope must have a payload")
    if allowed_payload_types is not None and envelope.payload_type not in allowed_payload_types:
        _fail(f"payload_type {envelope.payload_type!r} not in {allowed_payload_types}")


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
        payload = payload.payload_dict
    if not isinstance(payload, dict):
        _fail("payload must be a dict or Envelope")
    actual = payload.get(status_key)
    if actual != completed_value:
        _fail(f"Expected task status {completed_value!r}, got {actual!r}")


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
    if not request_envelope.id:
        _fail("Request envelope must have a non-empty id")
    correlation_id = getattr(response_envelope, correlation_id_field, None)
    if correlation_id is None:
        _fail(f"Response envelope must have {correlation_id_field!r}")
    if correlation_id != request_envelope.id:
        _fail(
            f"Response {correlation_id_field!r} {correlation_id!r} does not match "
            f"request id {request_envelope.id!r}"
        )


__all__ = [
    "assert_envelope_valid",
    "assert_task_completed",
    "assert_response_correlates",
]
