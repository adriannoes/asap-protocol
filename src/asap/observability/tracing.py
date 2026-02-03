"""OpenTelemetry tracing integration for ASAP protocol.

This module provides distributed tracing with W3C Trace Context propagation.
When enabled, FastAPI and httpx are auto-instrumented; custom spans cover
handler execution and state transitions. Trace IDs can be carried in
envelope.trace_id and envelope.extensions for cross-service correlation.

Example:
    >>> from asap.observability.tracing import configure_tracing, get_tracer
    >>> configure_tracing(service_name="my-agent", app=app)
    >>> tracer = get_tracer(__name__)
    >>> with tracer.start_as_current_span("my.operation"):
    ...     ...
"""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from opentelemetry import context, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

if TYPE_CHECKING:
    from fastapi import FastAPI

from asap.models.envelope import Envelope
from asap.observability.logging import get_logger

# Environment variables for zero-config (OpenTelemetry convention)
_ENV_OTEL_SERVICE_NAME = "OTEL_SERVICE_NAME"
_ENV_OTEL_TRACES_EXPORTER = "OTEL_TRACES_EXPORTER"
_ENV_OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"

# Extension keys for W3C trace context in envelope
EXTENSION_TRACE_ID = "trace_id"
EXTENSION_SPAN_ID = "span_id"

logger = get_logger(__name__)

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def configure_tracing(
    service_name: str | None = None,
    app: FastAPI | None = None,
) -> None:
    """Configure OpenTelemetry tracing and optionally instrument FastAPI and httpx.

    Uses environment variables for zero-config:
    - OTEL_SERVICE_NAME: service name (default: "asap-server")
    - OTEL_TRACES_EXPORTER: "none" | "otlp" | "console" (default: "none")
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (e.g. http://localhost:4317)

    When OTEL_TRACES_EXPORTER is "none" or unset, tracing is configured but
    no spans are exported (useful for dev without Jaeger). Set to "otlp" and
    OTEL_EXPORTER_OTLP_ENDPOINT for Jaeger/collector.

    Args:
        service_name: Override for OTEL_SERVICE_NAME.
        app: If provided, FastAPI and httpx are instrumented.
    """
    global _tracer_provider, _tracer

    name = service_name or os.environ.get(_ENV_OTEL_SERVICE_NAME) or "asap-server"
    resource = Resource.create({"service.name": name})
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)

    exporter_name = os.environ.get(_ENV_OTEL_TRACES_EXPORTER, "none").strip().lower()
    if exporter_name == "none":
        _tracer = trace.get_tracer("asap.protocol", "1.0.0", schema_url=None)
        if app is not None:
            _instrument_app(app)
        return

    if exporter_name == "otlp":
        _add_otlp_processor()
    elif exporter_name == "console":
        _add_console_processor()

    _tracer = trace.get_tracer("asap.protocol", "1.0.0", schema_url=None)
    if app is not None:
        _instrument_app(app)


def _add_otlp_processor() -> None:
    """Add OTLP span processor if endpoint is set."""
    global _tracer_provider
    if _tracer_provider is None:
        return
    endpoint = os.environ.get(_ENV_OTEL_EXPORTER_OTLP_ENDPOINT)
    if not endpoint:
        return
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter: SpanExporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    except ImportError as e:
        logger.debug("OTLP gRPC exporter not available: %s", e)
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter as OTLPSpanExporterHttp,
            )

            exporter = OTLPSpanExporterHttp(endpoint=endpoint)
            _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError as e2:
            logger.debug("OTLP HTTP exporter not available: %s", e2)


def _add_console_processor() -> None:
    """Add console span processor for debugging."""
    global _tracer_provider
    if _tracer_provider is None:
        return
    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        _tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    except ImportError as e:
        logger.debug("Console span exporter not available: %s", e)


def _instrument_app(app: FastAPI) -> None:
    """Instrument FastAPI and httpx for automatic spans."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        logger.debug("Failed to instrument FastAPI: %s", e)
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as e:
        logger.debug("Failed to instrument httpx: %s", e)


def reset_tracing() -> None:
    """Reset global tracer state (for test teardown).

    Clears the module-level tracer provider and tracer so that subsequent
    tests or configure_tracing() calls start from a clean state.
    """
    global _tracer_provider, _tracer
    _tracer_provider = None
    _tracer = None


def get_tracer(name: str | None = None) -> trace.Tracer:
    """Return the ASAP protocol tracer for custom spans.

    Args:
        name: Optional logger/module name for span attribution.

    Returns:
        OpenTelemetry Tracer instance.
    """
    if _tracer is None:
        trace.set_tracer_provider(TracerProvider())
        return trace.get_tracer("asap.protocol", "1.0.0", schema_url=None)
    return _tracer


def inject_envelope_trace_context(envelope: Envelope) -> Envelope:
    """Inject current span trace_id and span_id into envelope (W3C propagation).

    Sets envelope.trace_id and envelope.extensions[trace_id, span_id] from the
    current OpenTelemetry context so downstream services can continue the trace.

    Args:
        envelope: Response envelope to annotate.

    Returns:
        New envelope with trace_id and extensions updated (immutable).
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return envelope

    ctx = span.get_span_context()
    trace_id_hex = format(ctx.trace_id, "032x")
    span_id_hex = format(ctx.span_id, "016x")

    extensions = dict(envelope.extensions or {})
    extensions[EXTENSION_TRACE_ID] = trace_id_hex
    extensions[EXTENSION_SPAN_ID] = span_id_hex

    # Preserve existing trace_id for correlation (e.g. from request); set only if missing
    new_trace_id = envelope.trace_id if envelope.trace_id else trace_id_hex
    return envelope.model_copy(update={"trace_id": new_trace_id, "extensions": extensions})


def extract_and_activate_envelope_trace_context(envelope: Envelope) -> Any | None:
    """Extract trace context from envelope and set as current context (W3C).

    If envelope has trace_id (and optionally span_id in extensions), creates
    a non-recording span context so new spans become children of the incoming
    trace. Caller should call context.detach(token) when request ends.

    Args:
        envelope: Incoming envelope carrying trace_id / extensions.

    Returns:
        Context token to pass to context.detach(), or None if no context set.
    """
    trace_id_str = envelope.trace_id
    if not trace_id_str or len(trace_id_str) != 32:
        return None

    extensions = envelope.extensions or {}
    span_id_str = extensions.get(EXTENSION_SPAN_ID)
    if not span_id_str or len(span_id_str) != 16:
        return None

    try:
        trace_id = int(trace_id_str, 16)
        span_id = int(span_id_str, 16)
    except ValueError:
        return None

    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

    span_context = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=True,
        trace_flags=TraceFlags(0x01),
    )
    ctx = trace.set_span_in_context(NonRecordingSpan(span_context))
    return context.attach(ctx)


def handler_span_context(
    payload_type: str,
    agent_urn: str,
    envelope_id: str | None,
) -> AbstractContextManager[trace.Span]:
    """Start a current span for handler execution (use as context manager).

    Attributes: asap.payload_type, asap.agent.urn, asap.envelope.id.

    Args:
        payload_type: Envelope payload type.
        agent_urn: Manifest/agent URN.
        envelope_id: Envelope id.

    Returns:
        Span context manager (use with "with").
    """
    tracer = get_tracer(__name__)
    attrs: dict[str, str] = {
        "asap.payload_type": payload_type,
        "asap.agent.urn": agent_urn,
    }
    if envelope_id:
        attrs["asap.envelope.id"] = envelope_id
    return tracer.start_as_current_span("asap.handler.execute", attributes=attrs)


def state_transition_span_context(
    from_status: str,
    to_status: str,
    task_id: str | None = None,
) -> AbstractContextManager[trace.Span]:
    """Start a current span for a state machine transition (use as context manager).

    Attributes: asap.state.from, asap.state.to, asap.task.id.

    Args:
        from_status: Previous status.
        to_status: New status.
        task_id: Optional task id.

    Returns:
        Span context manager (use with "with").
    """
    tracer = get_tracer(__name__)
    attrs: dict[str, str] = {
        "asap.state.from": from_status,
        "asap.state.to": to_status,
    }
    if task_id:
        attrs["asap.task.id"] = task_id
    return tracer.start_as_current_span("asap.state.transition", attributes=attrs)
