"""Structured logging configuration for ASAP protocol.

This module configures structlog for structured logging with support for
both development (console) and production (JSON) output formats.

The logging configuration includes:
- JSON renderer for production environments
- Console renderer with colors for development
- Automatic timestamp and log level injection
- Context binding for trace_id, correlation_id, etc.

Environment Variables:
    ASAP_LOG_FORMAT: Set to "json" for JSON output, "console" for colored output
    ASAP_LOG_LEVEL: Set log level (DEBUG, INFO, WARNING, ERROR)
    ASAP_SERVICE_NAME: Service name to include in logs
    ASAP_DEBUG: Set to "true" or "1" to log full data and stack traces; otherwise sensitive fields are redacted

Example:
    >>> from asap.observability.logging import get_logger, configure_logging
    >>>
    >>> # Configure logging (typically done once at startup)
    >>> configure_logging(log_format="json", log_level="INFO")
    >>>
    >>> # Get a logger and use it
    >>> logger = get_logger("asap.transport.server")
    >>> logger.info("request.received", envelope_id="env_123")
"""

import logging
import os
import sys
from typing import Any

import structlog
from structlog.typing import Processor

# Default configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "console"
DEFAULT_SERVICE_NAME = "asap-protocol"

# Environment variable names
ENV_LOG_FORMAT = "ASAP_LOG_FORMAT"
ENV_LOG_LEVEL = "ASAP_LOG_LEVEL"
ENV_SERVICE_NAME = "ASAP_SERVICE_NAME"
ENV_DEBUG = "ASAP_DEBUG"

# Placeholder for redacted sensitive values in logs
REDACTED_PLACEHOLDER = "***REDACTED***"

# Key substrings (case-insensitive) that indicate sensitive data to redact
_SENSITIVE_KEY_PATTERNS = frozenset({"password", "token", "secret", "key", "authorization", "auth"})

# Module-level flag to track if logging has been configured
_logging_configured = False


def _is_sensitive_key(key: str) -> bool:
    """Return True if the key name indicates sensitive data that should be redacted."""
    lower = key.lower()
    return any(pattern in lower for pattern in _SENSITIVE_KEY_PATTERNS)


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dict for safe logging by redacting sensitive field values.

    Keys matching (case-insensitive) password, token, secret, key, authorization,
    or auth have their values replaced with REDACTED_PLACEHOLDER. Handles nested
    dicts and lists of dicts recursively. Non-sensitive keys and correlation_id
    are preserved for debugging.

    Args:
        data: The dict to sanitize (e.g. envelope payload or request params).

    Returns:
        A new dict with sensitive values replaced; nested structures are deep-copied
        and sanitized. Non-dict/non-list values for sensitive keys are redacted.

    Example:
        >>> sanitize_for_logging({"user": "alice", "password": "secret123"})
        {'user': 'alice', 'password': '***REDACTED***'}
        >>> sanitize_for_logging({"nested": {"token": "sk_live_abc"}})
        {'nested': {'token': '***REDACTED***'}}
    """
    if not data:
        return {}
    result: dict[str, Any] = {}
    for k, v in data.items():
        if _is_sensitive_key(k):
            result[k] = REDACTED_PLACEHOLDER
        elif isinstance(v, dict):
            result[k] = sanitize_for_logging(v)
        elif isinstance(v, list):
            result[k] = [
                sanitize_for_logging(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            result[k] = v
    return result


def is_debug_mode() -> bool:
    """Return True if ASAP_DEBUG is set to a truthy value (e.g. true, 1)."""
    value = os.environ.get(ENV_DEBUG, "").strip().lower()
    return value in ("true", "1", "yes", "on")


def _get_log_level() -> str:
    """Get log level from environment or use default."""
    return os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper()


def _get_log_format() -> str:
    """Get log format from environment or use default."""
    return os.environ.get(ENV_LOG_FORMAT, DEFAULT_LOG_FORMAT).lower()


def _get_service_name() -> str:
    """Get service name from environment or use default."""
    return os.environ.get(ENV_SERVICE_NAME, DEFAULT_SERVICE_NAME)


def _get_shared_processors() -> list[Processor]:
    """Get shared processors for all log formats."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def _get_console_renderer() -> Processor:
    """Get console renderer for development."""
    return structlog.dev.ConsoleRenderer(
        colors=True,
        exception_formatter=structlog.dev.plain_traceback,
    )


def _get_json_renderer() -> Processor:
    """Get JSON renderer for production."""
    return structlog.processors.JSONRenderer()


def configure_logging(
    log_format: str | None = None,
    log_level: str | None = None,
    service_name: str | None = None,
    force: bool = False,
) -> None:
    """Configure structured logging for the application.

    This function sets up structlog with the appropriate processors and
    renderers based on the specified format.

    Args:
        log_format: Output format - "json" or "console". Defaults to env var or "console"
        log_level: Minimum log level. Defaults to env var or "INFO"
        service_name: Service name for log context. Defaults to env var or "asap-protocol"
        force: If True, reconfigure even if already configured

    Example:
        >>> # Configure for production
        >>> configure_logging(log_format="json", log_level="INFO")
        >>>
        >>> # Configure for development
        >>> configure_logging(log_format="console", log_level="DEBUG")
    """
    global _logging_configured

    if _logging_configured and not force:
        return

    # Get configuration values
    log_format = log_format or _get_log_format()
    log_level = log_level or _get_log_level()
    service_name = service_name or _get_service_name()

    # Get shared processors
    shared_processors = _get_shared_processors()

    # Add format-specific renderer
    if log_format == "json":
        renderer: Processor = _get_json_renderer()
    else:
        renderer = _get_console_renderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level))

    # Set service name in context
    structlog.contextvars.bind_contextvars(service=service_name)

    _logging_configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for the given name.

    Creates a bound logger with the given name. If logging has not been
    configured, it will be configured with default settings.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Bound structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("event.happened", key="value")
        >>>
        >>> # With bound context
        >>> logger = logger.bind(trace_id="trace_123")
        >>> logger.info("request.processed")  # trace_id automatically included
    """
    # Ensure logging is configured
    if not _logging_configured:
        configure_logging()

    return structlog.stdlib.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables that will be included in all subsequent logs.

    This is useful for setting trace_id, correlation_id, or other context
    that should be included in all logs within the current context.

    Args:
        **kwargs: Key-value pairs to bind to the log context

    Example:
        >>> bind_context(trace_id="trace_123", user_id="user_456")
        >>> logger.info("event")  # Will include trace_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables.

    Useful for cleaning up context at the end of a request.
    """
    structlog.contextvars.clear_contextvars()
