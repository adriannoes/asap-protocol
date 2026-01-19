"""Enumerations for ASAP protocol.

This module defines all enum types used in the protocol to ensure
type safety and prevent magic strings.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task lifecycle states.

    Tasks progress through these states during their lifecycle.
    Terminal states are: COMPLETED, FAILED, CANCELLED.
    """

    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INPUT_REQUIRED = "input_required"

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        return self in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }


class MessageRole(str, Enum):
    """Message sender roles.

    Defines the role of the entity sending a message in a conversation.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UpdateType(str, Enum):
    """Task update types.

    Defines the type of update being sent for a task.
    """

    PROGRESS = "progress"
    INPUT_REQUIRED = "input_required"
    STATUS_CHANGE = "status_change"
