# Observability

This guide describes structured logging and trace context in ASAP.

## Structured Logging

ASAP uses `structlog` to emit structured logs with consistent fields for
service name, log level, and timestamps.

### Configuration

Configure logging once at startup:

```python
from asap.observability import configure_logging

configure_logging(log_format="json", log_level="INFO")
```

Environment variables:

- `ASAP_LOG_FORMAT`: `json` or `console`
- `ASAP_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `ASAP_SERVICE_NAME`: service name for log context

## Trace and Correlation IDs

Include trace context in logs by binding context variables:

```python
from asap.observability import get_logger
from asap.observability.logging import bind_context, clear_context

logger = get_logger(__name__)

bind_context(trace_id="trace_123", correlation_id="corr_456")
logger.info("asap.request.received", envelope_id="env_123", payload_type="task.request")

clear_context()
```

### Recommended fields

- `trace_id`: trace a request across services
- `correlation_id`: correlate request/response pairs
- `envelope_id`: identify the ASAP envelope
- `payload_type`: identify the message type

## Logging in Transport

The transport layer emits structured logs around request handling, handler
dispatch, and client send/response events. Use these logs to troubleshoot
end-to-end flows and latency.

## OpenTelemetry Tracing

ASAP supports distributed tracing via OpenTelemetry. When the server starts,
tracing is configured automatically; FastAPI and httpx are instrumented so
HTTP requests and handler execution appear as spans. Trace context is
propagated in envelope `trace_id` and `extensions.trace_id` / `extensions.span_id`
(W3C Trace Context).

### Zero-config (environment variables)

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_SERVICE_NAME` | Service name in traces | `asap-server` |
| `OTEL_TRACES_EXPORTER` | `none`, `otlp`, or `console` | `none` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint (e.g. Jaeger) | — |

- **`OTEL_TRACES_EXPORTER=none`**: Tracing is configured but no spans are
  exported (default; no collector required).
- **`OTEL_TRACES_EXPORTER=otlp`**: Export spans to an OTLP endpoint. Set
  `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://localhost:4317` for Jaeger).
- **`OTEL_TRACES_EXPORTER=console`**: Log spans to stdout (debugging).

### Testing with Jaeger

1. Run Jaeger (e.g. Docker: `docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:1.53`).
2. Start the ASAP server with:
   - `OTEL_TRACES_EXPORTER=otlp`
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
3. Send requests to `/asap`; open Jaeger UI at http://localhost:16686 and
   select the service name (`OTEL_SERVICE_NAME` or manifest id).

An integration test verifies end-to-end: `pytest tests/observability/test_jaeger_tracing.py -v`.
It starts Jaeger in Docker, runs the ASAP server with OTLP, sends a request, and asserts
traces appear in Jaeger (skips if Docker is not available).

### Custom spans

Handler execution and state machine transitions are recorded as spans with
attributes (`asap.payload_type`, `asap.agent.urn`, `asap.envelope.id`,
`asap.state.from`, `asap.state.to`, `asap.task.id`). Use `asap.observability.tracing.get_tracer()`
to add custom spans in your code.
