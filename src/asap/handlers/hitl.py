"""HITL (Human-in-the-Loop) protocol-agnostic types for ASAP.

This module provides protocol-agnostic human-in-the-loop abstractions:
- ApprovalDecision: Enum for approve/decline outcomes
- ApprovalResult: Pydantic model for human approval responses
- HumanApprovalProvider: Protocol for any HITL implementation (A2H, Slack, custom)
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class ApprovalDecision(StrEnum):
    """Human approval outcome for HITL flows."""

    APPROVE = "APPROVE"
    DECLINE = "DECLINE"


class ApprovalResult(BaseModel):
    """Result of a human approval request.

    Attributes:
        decision: Whether the human approved or declined.
        data: Optional payload from the approval flow.
        evidence: Optional audit trail or evidence.
        decided_at: Optional timestamp of the decision.
        interaction_id: Optional ID for correlating with the approval UI.
    """

    model_config = ConfigDict(extra="forbid")

    decision: ApprovalDecision
    data: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    decided_at: datetime | None = None
    interaction_id: str | None = None


@runtime_checkable
class HumanApprovalProvider(Protocol):
    """Protocol-agnostic interface for human approval.

    Implementations can use any backend (A2H Gateway, Slack, email, custom UI).
    Async-only to match ASAP's async-first architecture.
    """

    async def request_approval(
        self,
        *,
        context: str,
        principal_id: str,
        assurance_level: str = "LOW",
        timeout_seconds: float = 300.0,
    ) -> ApprovalResult:
        """Request human approval for an action.

        Args:
            context: Human-readable description of what requires approval.
            principal_id: Human or system identifier requesting approval.
            assurance_level: Assurance level (e.g. LOW, MEDIUM, HIGH).
            timeout_seconds: Max wait time before timing out.

        Returns:
            ApprovalResult with the human's decision.
        """
        ...
