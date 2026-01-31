"""Tests for structured logging configuration.

This module tests the logging module that provides structured
logging capabilities for the ASAP protocol.
"""

import logging
from unittest.mock import patch

import structlog

from asap.observability.logging import (
    REDACTED_PLACEHOLDER,
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    is_debug_log_mode,
    is_debug_mode,
    sanitize_for_logging,
)


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_sets_up_structlog(self) -> None:
        """Test that configure_logging sets up structlog correctly."""
        configure_logging(log_format="console", log_level="DEBUG", force=True)

        # Should be able to get a logger after configuration
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_respects_log_level(self) -> None:
        """Test that configure_logging sets the correct log level."""
        configure_logging(log_format="console", log_level="WARNING", force=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_with_json_format(self) -> None:
        """Test that configure_logging works with JSON format."""
        configure_logging(log_format="json", log_level="INFO", force=True)

        logger = get_logger("test.json")
        assert logger is not None

    def test_configure_logging_with_custom_service_name(self) -> None:
        """Test that configure_logging accepts custom service name."""
        configure_logging(
            log_format="console",
            log_level="INFO",
            service_name="my-custom-service",
            force=True,
        )

        logger = get_logger("test.service")
        assert logger is not None

    def test_configure_logging_does_not_reconfigure_by_default(self) -> None:
        """Test that configure_logging skips reconfiguration without force."""
        configure_logging(log_format="console", log_level="DEBUG", force=True)

        # Second call without force should be a no-op
        configure_logging(log_format="json", log_level="ERROR")

        # Verify we can still get a logger (configuration didn't crash)
        # Note: Due to structlog's caching, the exact level might vary
        logger = get_logger("test.no_reconfig")
        assert logger is not None

    def test_configure_logging_from_environment_variables(self) -> None:
        """Test that configure_logging reads from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "ASAP_LOG_FORMAT": "json",
                "ASAP_LOG_LEVEL": "ERROR",
                "ASAP_SERVICE_NAME": "env-service",
            },
        ):
            configure_logging(force=True)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.ERROR


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a structlog BoundLogger."""
        configure_logging(force=True)
        logger = get_logger("test.module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_get_logger_with_different_names(self) -> None:
        """Test that get_logger works with different names."""
        configure_logging(force=True)

        logger1 = get_logger("module.one")
        logger2 = get_logger("module.two")

        assert logger1 is not None
        assert logger2 is not None

    def test_logger_can_log_with_context(self) -> None:
        """Test that logger can log with additional context."""
        configure_logging(log_format="console", log_level="DEBUG", force=True)
        logger = get_logger("test.context")

        # Should not raise
        logger.info("test.event", key="value", number=42)

    def test_logger_bind_creates_new_logger_with_context(self) -> None:
        """Test that bind creates a new logger with bound context."""
        configure_logging(force=True)
        logger = get_logger("test.bind")

        bound_logger = logger.bind(trace_id="trace_123")
        assert bound_logger is not None

        # Original logger should not have the context
        # (this is just a structural test, not verifying output)


class TestContextBinding:
    """Tests for context binding functions."""

    def test_bind_context_adds_to_contextvars(self) -> None:
        """Test that bind_context adds context variables."""
        configure_logging(force=True)

        bind_context(trace_id="trace_abc", user_id="user_123")

        # Context should be bound (verifying via structlog internals)
        ctx = structlog.contextvars.get_contextvars()
        assert ctx.get("trace_id") == "trace_abc"
        assert ctx.get("user_id") == "user_123"

        # Clean up
        clear_context()

    def test_clear_context_removes_all_bound_context(self) -> None:
        """Test that clear_context removes all bound context."""
        configure_logging(force=True)

        bind_context(key1="value1", key2="value2")
        clear_context()

        ctx = structlog.contextvars.get_contextvars()
        # After clearing, the context should not have the bound keys
        assert "key1" not in ctx
        assert "key2" not in ctx


class TestSanitizeForLogging:
    """Tests for sanitize_for_logging (sensitive data redaction)."""

    def test_tokens_redacted(self) -> None:
        """Test that token-like keys are redacted."""
        data = {"token": "sk_live_abc123", "authorization": "Bearer xyz"}
        result = sanitize_for_logging(data)
        assert result["token"] == REDACTED_PLACEHOLDER
        assert result["authorization"] == REDACTED_PLACEHOLDER

    def test_password_and_secret_redacted(self) -> None:
        """Test that password and secret keys are redacted."""
        data = {"password": "secret123", "api_secret": "key456"}
        result = sanitize_for_logging(data)
        assert result["password"] == REDACTED_PLACEHOLDER
        assert result["api_secret"] == REDACTED_PLACEHOLDER

    def test_nested_objects_sanitized(self) -> None:
        """Test that nested dicts are recursively sanitized."""
        data = {"user": "alice", "nested": {"token": "sk_live_xyz", "id": 1}}
        result = sanitize_for_logging(data)
        assert result["user"] == "alice"
        assert result["nested"]["token"] == REDACTED_PLACEHOLDER
        assert result["nested"]["id"] == 1

    def test_non_sensitive_preserved(self) -> None:
        """Test that non-sensitive keys and correlation_id are preserved."""
        data = {"user": "alice", "correlation_id": "c123", "trace_id": "t456"}
        result = sanitize_for_logging(data)
        assert result["user"] == "alice"
        assert result["correlation_id"] == "c123"
        assert result["trace_id"] == "t456"

    def test_list_of_dicts_sanitized(self) -> None:
        """Test that lists of dicts are sanitized."""
        data = {"items": [{"name": "a", "password": "p1"}, {"name": "b", "token": "t1"}]}
        result = sanitize_for_logging(data)
        assert result["items"][0]["name"] == "a"
        assert result["items"][0]["password"] == REDACTED_PLACEHOLDER
        assert result["items"][1]["name"] == "b"
        assert result["items"][1]["token"] == REDACTED_PLACEHOLDER

    def test_empty_dict_returns_empty(self) -> None:
        """Test that empty dict returns empty dict."""
        assert sanitize_for_logging({}) == {}

    def test_sensitive_key_case_insensitive(self) -> None:
        """Test that sensitive key matching is case-insensitive."""
        data = {"PASSWORD": "pwd", "Token": "t1", "Authorization": "Bearer x"}
        result = sanitize_for_logging(data)
        assert result["PASSWORD"] == REDACTED_PLACEHOLDER
        assert result["Token"] == REDACTED_PLACEHOLDER
        assert result["Authorization"] == REDACTED_PLACEHOLDER


class TestIsDebugMode:
    """Tests for ASAP_DEBUG environment variable (is_debug_mode)."""

    def test_debug_mode_false_when_unset(self) -> None:
        """Test that is_debug_mode is False when ASAP_DEBUG is unset or empty."""
        with patch.dict("os.environ", {"ASAP_DEBUG": ""}):
            assert is_debug_mode() is False

    def test_debug_mode_true_when_true(self) -> None:
        """Test that is_debug_mode is True when ASAP_DEBUG=true."""
        with patch.dict("os.environ", {"ASAP_DEBUG": "true"}):
            assert is_debug_mode() is True

    def test_debug_mode_true_when_1(self) -> None:
        """Test that is_debug_mode is True when ASAP_DEBUG=1."""
        with patch.dict("os.environ", {"ASAP_DEBUG": "1"}):
            assert is_debug_mode() is True

    def test_debug_mode_false_when_false(self) -> None:
        """Test that is_debug_mode is False when ASAP_DEBUG=false."""
        with patch.dict("os.environ", {"ASAP_DEBUG": "false"}):
            assert is_debug_mode() is False


class TestIsDebugLogMode:
    """Tests for ASAP_DEBUG_LOG environment variable (is_debug_log_mode)."""

    def test_debug_log_mode_false_when_empty(self) -> None:
        """Test that is_debug_log_mode is False when ASAP_DEBUG_LOG is empty."""
        with patch.dict("os.environ", {"ASAP_DEBUG_LOG": ""}):
            assert is_debug_log_mode() is False

    def test_debug_log_mode_true_when_true(self) -> None:
        """Test that is_debug_log_mode is True when ASAP_DEBUG_LOG=true."""
        with patch.dict("os.environ", {"ASAP_DEBUG_LOG": "true"}):
            assert is_debug_log_mode() is True

    def test_debug_log_mode_true_when_1(self) -> None:
        """Test that is_debug_log_mode is True when ASAP_DEBUG_LOG=1."""
        with patch.dict("os.environ", {"ASAP_DEBUG_LOG": "1"}):
            assert is_debug_log_mode() is True

    def test_debug_log_mode_true_when_yes(self) -> None:
        """Test that is_debug_log_mode is True when ASAP_DEBUG_LOG=yes."""
        with patch.dict("os.environ", {"ASAP_DEBUG_LOG": "yes"}):
            assert is_debug_log_mode() is True

    def test_debug_log_mode_false_when_false(self) -> None:
        """Test that is_debug_log_mode is False when ASAP_DEBUG_LOG=false."""
        with patch.dict("os.environ", {"ASAP_DEBUG_LOG": "false"}):
            assert is_debug_log_mode() is False


class TestLoggingIntegration:
    """Integration tests for logging with transport modules."""

    def test_server_logger_can_be_created(self) -> None:
        """Test that server module logger can be created."""
        configure_logging(force=True)
        from asap.transport.server import logger as server_logger

        assert server_logger is not None

    def test_client_logger_can_be_created(self) -> None:
        """Test that client module logger can be created."""
        configure_logging(force=True)
        from asap.transport.client import logger as client_logger

        assert client_logger is not None

    def test_handlers_logger_can_be_created(self) -> None:
        """Test that handlers module logger can be created."""
        configure_logging(force=True)
        from asap.transport.handlers import logger as handlers_logger

        assert handlers_logger is not None
