"""Observability module for ASAP protocol.

This module provides structured logging and observability utilities
for the ASAP protocol transport layer.

Features:
- Structured logging with JSON output for production
- Console output with colors for development
- Automatic trace_id and correlation_id propagation
- Logger factory with common context binding

Example:
    >>> from asap.observability import get_logger
    >>>
    >>> logger = get_logger(__name__)
    >>> logger.info("asap.request.received", envelope_id="env_123", payload_type="task.request")
"""

from asap.observability.logging import (
    configure_logging,
    get_logger,
)

__all__ = [
    "configure_logging",
    "get_logger",
]
