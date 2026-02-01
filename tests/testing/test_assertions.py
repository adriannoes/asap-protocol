"""Unit tests for asap.testing assertions."""

import pytest

from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing.assertions import (
    assert_envelope_valid,
    assert_response_correlates,
    assert_task_completed,
)


def _make_request_envelope(
    *,
    id: str = "req_01HX5K4N",
    payload_type: str = "TaskRequest",
    correlation_id: str | None = None,
) -> Envelope:
    """Build a minimal valid request envelope."""
    payload = (
        TaskResponse(task_id="t1", status=TaskStatus.COMPLETED).model_dump()
        if payload_type == "TaskResponse"
        else TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump()
    )
    return Envelope(
        id=id,
        asap_version="0.1",
        sender="urn:asap:agent:a",
        recipient="urn:asap:agent:b",
        payload_type=payload_type,
        payload=payload,
        correlation_id=correlation_id or (id if payload_type == "TaskResponse" else None),
    )


class TestAssertEnvelopeValid:
    """Tests for assert_envelope_valid."""

    def test_valid_envelope_passes(self) -> None:
        """Valid envelope does not raise."""
        envelope = _make_request_envelope()
        assert_envelope_valid(envelope)

    def test_none_envelope_raises(self) -> None:
        """None envelope raises AssertionError."""
        with pytest.raises(AssertionError, match="Envelope must not be None"):
            assert_envelope_valid(None)  # type: ignore[arg-type]

    def test_empty_id_raises_when_required(self) -> None:
        """Envelope with empty id raises when require_id=True."""
        envelope = _make_request_envelope(id="")
        with pytest.raises(AssertionError, match="non-empty id"):
            assert_envelope_valid(envelope, require_id=True)

    def test_allowed_payload_types_rejects_other(self) -> None:
        """payload_type not in allowed_payload_types raises."""
        envelope = _make_request_envelope(payload_type="TaskResponse")
        with pytest.raises(
            AssertionError,
            match="payload_type .* not in \\['TaskRequest'\\]",
        ):
            assert_envelope_valid(envelope, allowed_payload_types=["TaskRequest"])

    def test_allowed_payload_types_accepts_match(self) -> None:
        """payload_type in allowed_payload_types does not raise."""
        envelope = _make_request_envelope()
        assert_envelope_valid(
            envelope,
            allowed_payload_types=["TaskRequest", "TaskResponse"],
        )


class TestAssertTaskCompleted:
    """Tests for assert_task_completed."""

    def test_dict_with_completed_passes(self) -> None:
        """Dict with status=completed does not raise."""
        assert_task_completed({"status": "completed"})

    def test_dict_with_wrong_status_raises(self) -> None:
        """Dict with status != completed_value raises."""
        with pytest.raises(
            AssertionError,
            match="Expected task status 'completed', got 'failed'",
        ):
            assert_task_completed({"status": "failed"})

    def test_envelope_with_task_response_payload_passes(self) -> None:
        """Envelope whose payload has status=completed does not raise."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="TaskResponse",
            payload=TaskResponse(task_id="t1", status=TaskStatus.COMPLETED).model_dump(),
            correlation_id="req_01",
        )
        assert_task_completed(envelope)

    def test_custom_status_key_and_value(self) -> None:
        """Custom status_key and completed_value work."""
        assert_task_completed(
            {"result": "done"},
            status_key="result",
            completed_value="done",
        )


class TestAssertResponseCorrelates:
    """Tests for assert_response_correlates."""

    def test_matching_correlation_passes(self) -> None:
        """Response with correlation_id equal to request id does not raise."""
        request = _make_request_envelope()
        response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="TaskResponse",
            payload=TaskResponse(task_id="t1", status=TaskStatus.COMPLETED).model_dump(),
            correlation_id=request.id,
        )
        assert_response_correlates(request, response)

    def test_mismatch_raises(self) -> None:
        """Response correlation_id != request id raises."""
        request = _make_request_envelope()
        response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="TaskResponse",
            payload=TaskResponse(task_id="t1", status=TaskStatus.COMPLETED).model_dump(),
            correlation_id="other_id",
        )
        with pytest.raises(
            AssertionError,
            match="does not match request id",
        ):
            assert_response_correlates(request, response)

    def test_request_without_id_raises(self) -> None:
        """Request envelope with empty id raises."""
        request = _make_request_envelope(id="")
        response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="TaskResponse",
            payload=TaskResponse(task_id="t1", status=TaskStatus.COMPLETED).model_dump(),
            correlation_id="req_01HX5K4N",
        )
        with pytest.raises(AssertionError, match="Request envelope must have"):
            assert_response_correlates(request, response)

    def test_response_without_correlation_id_raises(self) -> None:
        """Response without correlation_id raises."""
        request = _make_request_envelope()
        # Use payload_type that does not require correlation_id so we can set None
        response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
            correlation_id=None,
        )
        with pytest.raises(AssertionError, match="must have .*correlation_id"):
            assert_response_correlates(request, response)
