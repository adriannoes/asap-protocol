"""Unit tests for OpenTelemetry tracing module."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from asap.models.envelope import Envelope
from asap.observability.tracing import (
    EXTENSION_SPAN_ID,
    EXTENSION_TRACE_ID,
    configure_tracing,
    extract_and_activate_envelope_trace_context,
    get_tracer,
    handler_span_context,
    inject_envelope_trace_context,
    reset_tracing,
    state_transition_span_context,
)
from opentelemetry import context, trace


def _make_envelope(
    trace_id: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> Envelope:
    """Build a minimal Envelope for tests."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:sender",
        recipient="urn:asap:agent:recipient",
        payload_type="task.request",
        payload={},
        trace_id=trace_id,
        extensions=extensions,
    )


@pytest.fixture(autouse=True)
def _isolate_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset tracing before and after each test to avoid cross-test pollution."""
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    reset_tracing()
    yield
    reset_tracing()


class TestConfigureAndGetTracer:
    """Tests for configure_tracing and get_tracer."""

    def test_get_tracer_returns_tracer_without_configure(self) -> None:
        """get_tracer returns a tracer even when configure_tracing was not called."""
        tracer = get_tracer(__name__)
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    def test_configure_tracing_none_exporter_sets_tracer(self) -> None:
        """configure_tracing with exporter 'none' sets module tracer."""
        reset_tracing()
        configure_tracing(service_name="test-service")
        tracer = get_tracer(__name__)
        assert tracer is not None

    def test_reset_tracing_clears_state(self) -> None:
        """reset_tracing clears global tracer so get_tracer uses fallback."""
        configure_tracing(service_name="test-service")
        reset_tracing()
        tracer = get_tracer(__name__)
        assert tracer is not None

    def test_configure_otlp_without_endpoint_does_not_add_processor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When OTEL_TRACES_EXPORTER=otlp but OTEL_EXPORTER_OTLP_ENDPOINT is unset, no OTLP processor is added."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        reset_tracing()
        configure_tracing(service_name="test-otlp")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()


class TestInjectEnvelopeTraceContext:
    """Tests for inject_envelope_trace_context."""

    def test_inject_without_active_span_returns_unchanged(self) -> None:
        """When no recording span is active, envelope is returned unchanged."""
        envelope = _make_envelope()
        result = inject_envelope_trace_context(envelope)
        assert result is envelope
        assert result.trace_id == envelope.trace_id
        assert result.extensions == envelope.extensions

    def test_inject_with_active_span_adds_trace_id_and_extensions(self) -> None:
        """With an active recording span, envelope gets trace_id and extensions."""
        configure_tracing(service_name="test-inject")
        tracer = get_tracer(__name__)
        envelope = _make_envelope()

        with tracer.start_as_current_span("test.span"):
            result = inject_envelope_trace_context(envelope)

        assert result is not envelope
        assert result.trace_id is not None
        assert len(result.trace_id) == 32
        assert result.extensions is not None
        assert EXTENSION_TRACE_ID in result.extensions
        assert EXTENSION_SPAN_ID in result.extensions
        assert len(result.extensions[EXTENSION_TRACE_ID]) == 32
        assert len(result.extensions[EXTENSION_SPAN_ID]) == 16

    def test_inject_preserves_existing_trace_id(self) -> None:
        """When envelope already has trace_id, it is preserved."""
        configure_tracing(service_name="test-inject")
        tracer = get_tracer(__name__)
        existing = "a" * 32
        envelope = _make_envelope(trace_id=existing)

        with tracer.start_as_current_span("test.span"):
            result = inject_envelope_trace_context(envelope)

        assert result.trace_id == existing
        assert result.extensions is not None
        assert result.extensions[EXTENSION_TRACE_ID] is not None


class TestExtractAndActivateEnvelopeTraceContext:
    """Tests for extract_and_activate_envelope_trace_context."""

    def test_extract_none_trace_id_returns_none(self) -> None:
        """Envelope with no trace_id returns None."""
        envelope = _make_envelope(trace_id=None, extensions={})
        assert extract_and_activate_envelope_trace_context(envelope) is None

    def test_extract_short_trace_id_returns_none(self) -> None:
        """Envelope with trace_id length != 32 returns None."""
        envelope = _make_envelope(trace_id="abc", extensions={})
        assert extract_and_activate_envelope_trace_context(envelope) is None

    def test_extract_missing_span_id_returns_none(self) -> None:
        """Envelope with trace_id but no span_id in extensions returns None."""
        envelope = _make_envelope(
            trace_id="0" * 32,
            extensions={},
        )
        assert extract_and_activate_envelope_trace_context(envelope) is None

    def test_extract_short_span_id_returns_none(self) -> None:
        """Envelope with span_id length != 16 returns None."""
        envelope = _make_envelope(
            trace_id="0" * 32,
            extensions={EXTENSION_SPAN_ID: "abc"},
        )
        assert extract_and_activate_envelope_trace_context(envelope) is None

    def test_extract_invalid_hex_returns_none(self) -> None:
        """Envelope with non-hex trace_id or span_id returns None."""
        envelope = _make_envelope(
            trace_id="z" * 32,
            extensions={EXTENSION_SPAN_ID: "0" * 16},
        )
        assert extract_and_activate_envelope_trace_context(envelope) is None

    def test_extract_valid_returns_token_and_activates_context(self) -> None:
        """Valid trace_id and span_id returns token; caller must detach."""
        envelope = _make_envelope(
            trace_id="0" * 32,
            extensions={EXTENSION_SPAN_ID: "0" * 16},
        )
        token = extract_and_activate_envelope_trace_context(envelope)
        assert token is not None
        try:
            current = trace.get_current_span()
            ctx = current.get_span_context()
            assert ctx.trace_id == 0
            assert ctx.span_id == 0
        finally:
            context.detach(token)


class TestHandlerSpanContext:
    """Tests for handler_span_context."""

    def test_handler_span_context_enters_and_exits(self) -> None:
        """handler_span_context works as context manager."""
        with handler_span_context(
            payload_type="task.request",
            agent_urn="urn:asap:agent:test",
            envelope_id="env-123",
        ) as span:
            assert span.is_recording()
            assert span.get_span_context().trace_id != 0 or span.get_span_context().span_id != 0

    def test_handler_span_context_without_envelope_id(self) -> None:
        """handler_span_context accepts None envelope_id."""
        with handler_span_context(
            payload_type="task.request",
            agent_urn="urn:asap:agent:test",
            envelope_id=None,
        ) as span:
            assert span.is_recording()


class TestStateTransitionSpanContext:
    """Tests for state_transition_span_context."""

    def test_state_transition_span_context_enters_and_exits(self) -> None:
        """state_transition_span_context works as context manager."""
        with state_transition_span_context(
            from_status="pending",
            to_status="running",
            task_id="task-1",
        ) as span:
            assert span.is_recording()

    def test_state_transition_span_context_without_task_id(self) -> None:
        """state_transition_span_context accepts None task_id."""
        with state_transition_span_context(
            from_status="pending",
            to_status="completed",
            task_id=None,
        ) as span:
            assert span.is_recording()


class TestConfigureTracingExporters:
    """Tests for configure_tracing with OTLP/console exporters (env-driven)."""

    def test_configure_tracing_with_otlp_env_adds_processor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With OTEL_TRACES_EXPORTER=otlp and endpoint set, OTLP processor is attempted."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        configure_tracing(service_name="test-otlp")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_configure_tracing_with_console_env_adds_processor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With OTEL_TRACES_EXPORTER=console, console processor is attempted."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
        configure_tracing(service_name="test-console")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_configure_tracing_with_app_instruments_fastapi(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When app is passed, _instrument_app is called (FastAPI/httpx instrumentation attempted)."""
        mock_app = MagicMock()
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
        configure_tracing(service_name="test-app", app=mock_app)
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_configure_tracing_otlp_without_endpoint_does_not_add_processor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With OTEL_TRACES_EXPORTER=otlp and no endpoint, _add_otlp_processor returns early."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        configure_tracing(service_name="test-otlp-no-endpoint")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()


class TestTracingImportErrorBranches:
    """Tests for import-failure branches in _add_otlp_processor and _add_console_processor."""

    def test_otlp_grpc_import_error_falls_back_to_http(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When gRPC OTLP exporter import fails, HTTP fallback is attempted."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        class FakeGrpcModule:
            def __getattr__(self, name: str) -> None:
                raise ImportError("grpc not available")

        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.otlp.proto.grpc.trace_exporter": FakeGrpcModule()},
        ):
            configure_tracing(service_name="test-otlp-fallback")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_otlp_grpc_and_http_import_error_logs_and_continues(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both gRPC and HTTP OTLP exporters fail to import, configure_tracing still sets tracer."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        class FakeModule:
            def __getattr__(self, name: str) -> None:
                raise ImportError("not available")

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": FakeModule(),
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": FakeModule(),
            },
        ):
            configure_tracing(service_name="test-otlp-both-fail")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_console_span_exporter_import_error_logs_and_continues(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ConsoleSpanExporter() raises ImportError, configure_tracing still sets tracer."""

        def raise_import_error() -> None:
            raise ImportError("console exporter not available")

        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
        export_mod = sys.modules["opentelemetry.sdk.trace.export"]
        monkeypatch.setattr(export_mod, "ConsoleSpanExporter", raise_import_error, raising=False)
        configure_tracing(service_name="test-console-fail")
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()


class TestInstrumentAppFailureBranches:
    """Tests for _instrument_app when FastAPI/httpx instrumentation raises."""

    def test_fastapi_instrumentation_failure_does_not_propagate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FastAPIInstrumentor.instrument_app raises, configure_tracing does not propagate."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
        mock_app = MagicMock()
        with patch(
            "opentelemetry.instrumentation.fastapi.FastAPIInstrumentor",
            MagicMock(instrument_app=MagicMock(side_effect=RuntimeError("instrumentation failed"))),
        ):
            configure_tracing(service_name="test", app=mock_app)
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()

    def test_httpx_instrumentation_failure_does_not_propagate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When HTTPXClientInstrumentor().instrument() raises, configure_tracing does not propagate."""
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
        mock_app = MagicMock()
        with patch(
            "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor",
            MagicMock(
                return_value=MagicMock(
                    instrument=MagicMock(side_effect=RuntimeError("httpx failed"))
                )
            ),
        ):
            configure_tracing(service_name="test", app=mock_app)
        tracer = get_tracer(__name__)
        assert tracer is not None
        reset_tracing()
