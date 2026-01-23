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
