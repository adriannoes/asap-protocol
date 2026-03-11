"""Tests for HITL (Human-in-the-Loop) protocol types."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from asap.handlers.hitl import (
    ApprovalDecision,
    ApprovalResult,
    HumanApprovalProvider,
)


def test_approval_result_approve() -> None:
    """ApprovalResult with APPROVE serializes correctly; optional fields are None."""
    result = ApprovalResult(decision=ApprovalDecision.APPROVE)
    dumped = result.model_dump()
    assert dumped["decision"] == "APPROVE"
    assert result.decision == ApprovalDecision.APPROVE
    assert result.data is None
    assert result.evidence is None
    assert result.decided_at is None
    assert result.interaction_id is None


def test_approval_result_decline() -> None:
    """ApprovalResult with DECLINE has correct decision value."""
    result = ApprovalResult(decision=ApprovalDecision.DECLINE)
    assert result.decision == ApprovalDecision.DECLINE
    assert result.model_dump()["decision"] == "DECLINE"


def test_approval_result_forbids_extra_fields() -> None:
    """ApprovalResult raises ValidationError when extra fields are passed."""
    with pytest.raises(ValidationError):
        ApprovalResult(
            decision=ApprovalDecision.APPROVE,
            unknown_field="x",
        )


def test_approval_result_with_all_fields() -> None:
    """ApprovalResult with all optional fields round-trips via model_validate."""
    decided_at = datetime.now(timezone.utc)
    result = ApprovalResult(
        decision=ApprovalDecision.APPROVE,
        data={"key": "value"},
        evidence={"audit": "trail"},
        decided_at=decided_at,
        interaction_id="int-123",
    )
    round_tripped = ApprovalResult.model_validate(result.model_dump())
    assert round_tripped.decision == result.decision
    assert round_tripped.data == result.data
    assert round_tripped.evidence == result.evidence
    assert round_tripped.decided_at == result.decided_at
    assert round_tripped.interaction_id == result.interaction_id


@pytest.mark.asyncio
async def test_protocol_conformance_with_mock() -> None:
    """A class implementing request_approval conforms to HumanApprovalProvider."""

    class MockProvider:
        async def request_approval(
            self,
            *,
            context: str,
            principal_id: str,
            assurance_level: str = "LOW",
            timeout_seconds: float = 300.0,
        ) -> ApprovalResult:
            return ApprovalResult(decision=ApprovalDecision.APPROVE)

    provider = MockProvider()
    assert isinstance(provider, HumanApprovalProvider)


def test_non_conforming_class_fails() -> None:
    """A class missing request_approval does not conform to HumanApprovalProvider."""

    class NonConforming:
        pass

    provider = NonConforming()
    assert isinstance(provider, HumanApprovalProvider) is False
