"""ASAP Protocol Handler Abstractions.

This module provides handler-level abstractions for agent workflows:
- Human-in-the-loop (HITL): Protocol-agnostic interface for human approval

Public exports:
    HumanApprovalProvider: Protocol for HITL implementations
    ApprovalResult: Model for human approval responses
    ApprovalDecision: Enum for approve/decline outcomes
"""

from asap.handlers.hitl import (
    ApprovalDecision,
    ApprovalResult,
    HumanApprovalProvider,
)

__all__ = [
    "ApprovalDecision",
    "ApprovalResult",
    "HumanApprovalProvider",
]
