"""ASAP Protocol Error Taxonomy.

This module defines the error hierarchy for the ASAP protocol,
providing structured error handling with specific error codes
and context information.
"""
from __future__ import annotations

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
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{code, message, details}`` dict."""
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


class InvalidTimestampError(ASAPError):
    """Raised when an envelope timestamp is invalid (too old or too far in the future).

    This error occurs when validating envelope timestamps for replay attack prevention.
    Envelopes with timestamps outside the acceptable window are rejected.

    Attributes:
        timestamp: The invalid timestamp value
        age_seconds: Age of the envelope in seconds (if too old)
        future_offset_seconds: Offset in seconds from current time (if too far in future)
    """

    def __init__(
        self,
        timestamp: str,
        message: str,
        age_seconds: float | None = None,
        future_offset_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        # Build details dict with optional fields
        details_dict: dict[str, Any] = {"timestamp": timestamp}
        if age_seconds is not None:
            details_dict["age_seconds"] = age_seconds
        if future_offset_seconds is not None:
            details_dict["future_offset_seconds"] = future_offset_seconds
        if details:
            details_dict.update(details)

        super().__init__(
            code="asap:protocol/invalid_timestamp",
            message=message,
            details=details_dict,
        )
        self.timestamp = timestamp
        self.age_seconds = age_seconds
        self.future_offset_seconds = future_offset_seconds


class InvalidNonceError(ASAPError):
    """Raised when an envelope nonce is invalid (duplicate or malformed).

    This error occurs when validating envelope nonces for replay attack prevention.
    Nonces that have been used before within the TTL window are rejected.

    Attributes:
        nonce: The invalid nonce value
    """

    def __init__(
        self,
        nonce: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="asap:protocol/invalid_nonce",
            message=message,
            details={
                "nonce": nonce,
                **(details or {}),
            },
        )
        self.nonce = nonce


class CircuitOpenError(ASAPError):
    """Raised when circuit breaker is open and request is rejected.

    This error occurs when the circuit breaker pattern has detected
    too many consecutive failures and is preventing further requests
    to protect the system from cascading failures.

    Attributes:
        base_url: The URL for which the circuit is open
        consecutive_failures: Number of consecutive failures that opened the circuit
    """

    def __init__(
        self,
        base_url: str,
        consecutive_failures: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = (
            f"Circuit breaker is OPEN for {base_url}. "
            f"Too many consecutive failures ({consecutive_failures}). "
            "Service temporarily unavailable."
        )
        super().__init__(
            code="asap:transport/circuit_open",
            message=message,
            details={
                "base_url": base_url,
                "consecutive_failures": consecutive_failures,
                **(details or {}),
            },
        )
        self.base_url = base_url
        self.consecutive_failures = consecutive_failures


class WebhookURLValidationError(ASAPError):
    """Raised when a webhook callback URL fails SSRF validation.

    This error occurs when a callback URL resolves to a private, loopback,
    or link-local address, or when HTTPS is required but the scheme is HTTP.

    Attributes:
        url: The rejected URL.
        reason: Why the URL was rejected.
    """

    def __init__(
        self,
        url: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"Webhook URL rejected: {reason}"
        super().__init__(
            code="asap:transport/webhook_url_rejected",
            message=message,
            details={
                "url": url,
                "reason": reason,
                **(details or {}),
            },
        )
        self.url = url
        self.reason = reason


class SignatureVerificationError(ASAPError):
    """Tampering, wrong algorithm, or invalid/corrupted signature; see message for cause."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="asap:error/signature-verification",
            message=message,
            details=details or {},
        )


class UnsupportedAuthSchemeError(ASAPError):
    """Raised when an unsupported authentication scheme is specified.

    This error occurs when a Manifest specifies an authentication scheme
    that is not supported by the current implementation.

    Attributes:
        scheme: The unsupported scheme name
        supported_schemes: List of supported schemes
    """

    def __init__(
        self,
        scheme: str,
        supported_schemes: set[str] | frozenset[str],
        details: dict[str, Any] | None = None,
    ) -> None:
        supported_list = sorted(supported_schemes)
        message = (
            f"Unsupported authentication scheme '{scheme}'. "
            f"Supported schemes: {', '.join(supported_list)}"
        )
        super().__init__(
            code="asap:auth/unsupported_scheme",
            message=message,
            details={
                "scheme": scheme,
                "supported_schemes": list(supported_list),
                **(details or {}),
            },
        )
        self.scheme = scheme
        self.supported_schemes = supported_schemes
