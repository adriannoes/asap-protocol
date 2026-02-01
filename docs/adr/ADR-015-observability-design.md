# ADR-015: Observability Design (trace_id, correlation_id)

## Context and Problem Statement

Distributed agent communication requires tracing requests across services. We need standard fields for correlation and distributed tracing.

## Decision Drivers

* Trace requests across agents
* Correlate request/response pairs
* Structured logging with context
* Compatibility with OpenTelemetry and tracing backends

## Considered Options

* No standard fields
* Single request ID
* trace_id + correlation_id (request ID)
* Full OpenTelemetry context propagation

## Decision Outcome

Chosen option: "trace_id + correlation_id", because trace_id identifies the full workflow across agents; correlation_id links request and response envelopes. Envelope model includes trace_id; response includes correlation_id pointing to request. bind_context/clear_context for log correlation.

### Consequences

* Good, because trace_id flows through multi-agent workflows
* Good, because correlation_id links request/response for debugging
* Good, because structlog + bind_context for log enrichment
* Bad, because manual propagation; OTel auto-instrumentation deferred

### Confirmation

Envelope.trace_id, response.correlation_id. bind_context(trace_id=..., correlation_id=...). See [Observability](../observability.md).

## Pros and Cons of the Options

### Single request ID

* Good, because simple
* Bad, because no workflow-level trace

### trace_id + correlation_id

* Good, because workflow + request/response correlation
* Good, because aligns with OTel concepts
* Neutral, because OTel full propagation future work

## More Information

* [Observability](../observability.md)
* `asap.observability.logging.bind_context`, `clear_context`
* Envelope.trace_id, correlation_id
