"""Observability module for ASAP protocol.

This module provides structured logging, metrics, and observability utilities
for the ASAP protocol transport layer.

Features:
- Structured logging with JSON output for production
- Console output with colors for development
- Automatic trace_id and correlation_id propagation
- Logger factory with common context binding
- Prometheus-compatible metrics collection

Example:
    >>> from asap.observability import get_logger, get_metrics
    >>>
    >>> logger = get_logger(__name__)
    >>> logger.info("asap.request.received", envelope_id="env_123", payload_type="task.request")
    >>>
    >>> metrics = get_metrics()
    >>> metrics.increment_counter("asap_requests_total", {"payload_type": "task.request"})
"""

from asap.observability.logging import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)
from asap.observability.metrics import (
    MetricsCollector,
    get_metrics,
    reset_metrics,
)

__all__ = [
    "bind_context",
    "clear_context",
    "configure_logging",
    "get_logger",
    "get_metrics",
    "reset_metrics",
    "MetricsCollector",
]
