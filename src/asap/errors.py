"""ASAP Protocol Error Taxonomy.

This module defines the error hierarchy for the ASAP protocol,
providing structured error handling with specific error codes
and context information.
"""

from typing import Any


class ASAPError(Exception):
    """Base exception for all ASAP protocol errors.

    This is the root exception class that all ASAP-specific errors
    should inherit from. It provides a standardized way to handle
    protocol-level errors with error codes and additional context.

    Attributes:
        code: Error code following the asap:error/... pattern
        message: Human-readable error message
        details: Optional additional error context
    """

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize ASAP error.

        Args:
            code: Error code (e.g., 'asap:protocol/invalid_state')
            message: Human-readable error description
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization.

        Returns:
            Dictionary containing code, message, and details
        """
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class InvalidTransitionError(ASAPError):
    """Raised when attempting an invalid task state transition.

    This error occurs when trying to change a task from one status
    to another status that is not allowed by the state machine rules.

    Attributes:
        from_state: The current task status
        to_state: The attempted target status
    """

    def __init__(
        self, from_state: str, to_state: str, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize invalid transition error.

        Args:
            from_state: Current task status
            to_state: Attempted target status
            details: Optional additional context
        """
        message = f"Invalid transition from '{from_state}' to '{to_state}'"
        super().__init__(
            code="asap:protocol/invalid_state",
            message=message,
            details={"from_state": from_state, "to_state": to_state, **(details or {})},
        )
        self.from_state = from_state
        self.to_state = to_state


class MalformedEnvelopeError(ASAPError):
    """Raised when receiving a malformed or invalid envelope.

    This error occurs when the envelope structure is invalid,
    missing required fields, or contains malformed data that
    cannot be processed by the protocol.
    """

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize malformed envelope error.

        Args:
            reason: Description of what's malformed
            details: Optional additional context (e.g., validation errors)
        """
        message = f"Malformed envelope: {reason}"
        super().__init__(
            code="asap:protocol/malformed_envelope", message=message, details=details or {}
        )
        self.reason = reason


class TaskNotFoundError(ASAPError):
    """Raised when a requested task cannot be found.

    This error occurs when attempting to access or modify a task
    that doesn't exist in the system.
    """

    def __init__(self, task_id: str, details: dict[str, Any] | None = None) -> None:
        """Initialize task not found error.

        Args:
            task_id: The ID of the task that was not found
            details: Optional additional context
        """
        message = f"Task not found: {task_id}"
        super().__init__(
            code="asap:task/not_found",
            message=message,
            details={"task_id": task_id, **(details or {})},
        )
        self.task_id = task_id


class TaskAlreadyCompletedError(ASAPError):
    """Raised when attempting to modify a task that is already completed.

    This error occurs when trying to perform operations on a task
    that has reached a terminal state and cannot be modified further.
    """

    def __init__(
        self, task_id: str, current_status: str, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize task already completed error.

        Args:
            task_id: The ID of the completed task
            current_status: The current terminal status
            details: Optional additional context
        """
        message = f"Task already completed: {task_id} (status: {current_status})"
        super().__init__(
            code="asap:task/already_completed",
            message=message,
            details={"task_id": task_id, "current_status": current_status, **(details or {})},
        )
        self.task_id = task_id
        self.current_status = current_status


class ThreadPoolExhaustedError(ASAPError):
    """Raised when the thread pool is exhausted and cannot accept new tasks.

    This error occurs when attempting to submit a synchronous handler
    to a bounded thread pool that has reached its maximum capacity.
    This prevents DoS attacks by limiting resource consumption.

    Attributes:
        max_threads: Maximum number of threads in the pool
        active_threads: Current number of active threads
    """

    def __init__(
        self,
        max_threads: int,
        active_threads: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize thread pool exhausted error.

        Args:
            max_threads: Maximum number of threads in the pool
            active_threads: Current number of active threads
            details: Optional additional context
        """
        message = (
            f"Thread pool exhausted: {active_threads}/{max_threads} threads in use. "
            "Service temporarily unavailable."
        )
        super().__init__(
            code="asap:transport/thread_pool_exhausted",
            message=message,
            details={
                "max_threads": max_threads,
                "active_threads": active_threads,
                **(details or {}),
            },
        )
        self.max_threads = max_threads
        self.active_threads = active_threads
