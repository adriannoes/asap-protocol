# ADR-003: JSON-RPC 2.0 Binding

## Context and Problem Statement

ASAP envelopes must be transported over HTTP. We need a standard framing protocol for request/response correlation, error handling, and interoperability.

## Decision Drivers

* Standard protocol for RPC over HTTP
* Request/response correlation via `id` field
* Structured error format (code, message, data)
* Wide tooling support (clients, proxies, debuggers)

## Considered Options

* Raw JSON POST (custom format)
* JSON-RPC 2.0
* gRPC
* GraphQL

## Decision Outcome

Chosen option: "JSON-RPC 2.0", because it provides a well-defined envelope (`method`, `params`, `id`), standard error structure, and broad ecosystem support. ASAP envelopes are wrapped in `params.envelope` and `method: asap.send`.

### Consequences

* Good, because interoperable with existing JSON-RPC tooling
* Good, because clear error taxonomy (code, message, data)
* Good, because batch requests possible (future)
* Bad, because extra wrapping layer; slightly larger payloads

### Confirmation

Transport layer uses `asap.send` method. See `asap.transport.jsonrpc` and integration tests.

## Pros and Cons of the Options

### Raw JSON POST

* Good, because minimal overhead
* Bad, because no standard for errors or correlation

### JSON-RPC 2.0

* Good, because RFC-standard; tooling exists
* Good, because supports batching for future use
* Neutral, because one extra wrapper object

### gRPC

* Good, because binary efficiency
* Bad, because different ecosystem; HTTP/1.1 and browser support weaker

## More Information

* [JSON-RPC 2.0 spec](https://www.jsonrpc.org/specification)
* Implementation: `src/asap/transport/jsonrpc.py`
* Endpoint: `POST /asap`
