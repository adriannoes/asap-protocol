# ADR-018: Streaming Transport (SSE for HTTP)

## Context and Problem Statement

AI agents often need to return results incrementally — streaming partial LLM tokens, progress updates, or chunked data. Currently ASAP supports real-time communication via WebSocket (v1.1, ADR-003/SD-3) but lacks HTTP-based streaming. This is the biggest competitive gap vs Google A2A which has native streaming support. Existing decisions Q5 (`stream_uri` for MCP payloads) and Q16 (streaming does not require MessageAck) provide partial foundations but no SSE endpoint exists.

## Decision Drivers

* Competitive parity with Google A2A streaming
* AI agent use cases require incremental responses (LLM token streaming, progress)
* HTTP-based streaming needed for environments where WebSocket is unavailable (proxies, serverless)
* Q16 established that streaming messages do NOT require ack (only state-changing messages do)
* Must complement WebSocket, not replace it (WebSocket remains for bidirectional use cases)

## Considered Options

* SSE (Server-Sent Events) over HTTP
* WebSocket-only streaming (extend existing)
* HTTP/2 Server Push
* gRPC streaming

## Decision Outcome

Chosen option: "SSE (Server-Sent Events) over HTTP", because SSE provides unidirectional server-to-client streaming over standard HTTP, works through most proxies and CDNs, requires no additional dependencies (FastAPI's `StreamingResponse`), and complements the existing WebSocket transport for bidirectional needs.

### Consequences

* Good, because SSE works through HTTP/1.1 proxies and CDNs where WebSocket may not
* Good, because no new dependencies — uses `starlette.responses.StreamingResponse`
* Good, because follows established `text/event-stream` standard (W3C)
* Good, because aligns with Q16 — streaming events don't require ack
* Good, because `httpx.stream()` on client side already supports async iteration
* Bad, because SSE is unidirectional (server-to-client only) — client-to-server streaming still needs WebSocket
* Bad, because adds a new endpoint (`/asap/stream`) increasing API surface

### Confirmation

SSE endpoint tests in `tests/transport/test_streaming.py`. E2E test with `ASAPClient.stream()`. Compliance Harness v2 streaming checks.

## Pros and Cons of the Options

### SSE (Server-Sent Events)

* Good, because standard HTTP, works through proxies
* Good, because automatic reconnection built into browser/client implementations
* Good, because `text/event-stream` content type is well understood
* Good, because FastAPI native support via `StreamingResponse`
* Bad, because unidirectional (server → client only)
* Bad, because no binary data support (text only, but JSON is text)

### WebSocket-only streaming

* Good, because already implemented for bidirectional comms
* Good, because supports binary data
* Bad, because not all environments support WebSocket (serverless, some proxies)
* Bad, because mixing streaming and request/response on same connection adds complexity
* Bad, because doesn't close the competitive gap (HTTP streaming is the specific gap)

### HTTP/2 Server Push

* Good, because multiplexed streams
* Bad, because largely deprecated by browsers
* Bad, because requires HTTP/2 infrastructure
* Bad, because complex implementation

### gRPC streaming

* Good, because excellent streaming support, bidirectional
* Bad, because contradicts ADR-003 (JSON-RPC 2.0 binding chosen over gRPC)
* Bad, because requires Protocol Buffers, heavy tooling
* Bad, because limited browser support without grpc-web proxy

## More Information

* Q5 (`decision-records/02-protocol.md`): `stream_uri` for large MCP payloads
* Q16 (`decision-records/02-protocol.md`): Streaming does not require MessageAck
* ADR-003 (`docs/adr/`): JSON-RPC 2.0 chosen over gRPC
* `tech-stack-decisions.md` §2.3: WebSocket rationale
* PRD v2.2: `prd-v2.2-protocol-hardening.md` §4.1
