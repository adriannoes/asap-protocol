# Troubleshooting Guide

This guide helps you diagnose and fix common issues when running ASAP agents in development or production. Use it together with [Error Handling](error-handling.md), [Observability](observability.md), and [Deployment (Kubernetes)](deployment/kubernetes.md).

---

## Common Errors

This section lists the most frequent errors you may encounter, with cause and solution. For the full error taxonomy, see [Error Handling](error-handling.md). All ASAP protocol errors use the code format `asap:<domain>/<error>`.

### Error → Cause → Solution

| # | Error | Cause | Solution |
|---|--------|--------|----------|
| 1 | **InvalidTransitionError** (`asap:protocol/invalid_state`) | Task state transition not allowed by the state machine (e.g. `submitted` → `completed` without `running`). | Ensure transitions follow the defined state machine; use `running` before `completed`/`failed`. |
| 2 | **MalformedEnvelopeError** (`asap:protocol/malformed_envelope`) | Envelope missing required fields, wrong types, or invalid structure. | Validate envelope with Pydantic before sending; check `task_id`, `sender`, `payload`, timestamps. |
| 3 | **TaskNotFoundError** (`asap:task/not_found`) | Requested task ID does not exist or was never created. | Verify `task_id` is correct and the task was created on the target agent; check for typos or wrong agent. |
| 4 | **TaskAlreadyCompletedError** (`asap:task/already_completed`) | Update attempted on a task already in a terminal state (`completed` or `failed`). | Do not send updates for completed tasks; create a new task if you need a new unit of work. |
| 5 | **ThreadPoolExhaustedError** (`asap:transport/thread_pool_exhausted`) | All worker threads are busy; server cannot accept more synchronous handler work. | Increase `max_threads` in server config (or `ASAP_MAX_THREADS`), optimize slow handlers, or use async handlers. |
| 6 | **InvalidTimestampError** (`asap:protocol/invalid_timestamp`) | Envelope timestamp too old (replay) or too far in the future (clock skew). | Sync clocks (NTP); ensure envelope is sent within the allowed time window (see server config). |
| 7 | **InvalidNonceError** (`asap:protocol/invalid_nonce`) | Duplicate or invalid nonce (replay attack prevention). | Generate a unique nonce per envelope; do not reuse nonces within the TTL window. |
| 8 | **CircuitOpenError** (`asap:transport/circuit_open`) | Circuit breaker opened after consecutive failures; requests are rejected. | Wait for circuit timeout or fix remote service; check connectivity and remote agent health. |
| 9 | **UnsupportedAuthSchemeError** (`asap:auth/unsupported_scheme`) | Manifest specifies an auth scheme the client does not support. | Use a supported scheme (e.g. `Bearer`) or extend the client to support the required scheme. |
| 10 | **ASAPConnectionError** | HTTP connection failed: agent down, wrong URL, network/firewall, or TLS issues. | Verify agent is running, URL scheme and port, network/firewall, and SSL certificates. |
| 11 | **ASAPTimeoutError** | Request exceeded the configured timeout. | Increase client `timeout`; optimize slow handlers or network; consider smaller payloads or streaming. |
| 12 | **ASAPRemoteError** | Remote agent returned a JSON-RPC error (code, message, data). | Inspect `code` and `data`; fix request (envelope/params) or fix the remote agent implementation. |
| 13 | **HandlerNotFoundError** (`asap:transport/handler_not_found`) | No handler registered for the payload type (e.g. `task.request`). | Register a handler for that payload type in `HandlerRegistry` before processing requests. |
| 14 | **JSON-RPC INVALID_REQUEST** (-32600) | Malformed JSON-RPC request (invalid JSON or missing `jsonrpc`/`method`/`id`). | Ensure request is valid JSON-RPC 2.0; include `jsonrpc`, `method`, `id`, and `params` where required. |
| 15 | **JSON-RPC INVALID_PARAMS** (-32602) | Invalid `params` (e.g. envelope validation failed). | Validate envelope structure and types before sending; check server logs for validation details. |
| 16 | **JSON-RPC METHOD_NOT_FOUND** (-32601) | Unknown method or payload type. | Use a supported method/payload type; ensure client and server versions and APIs are compatible. |
| 17 | **JSON-RPC INTERNAL_ERROR** (-32603) | Unexpected server-side exception. | Check server logs and traces; fix bug in handler or server code; report if persistent. |
| 18 | **Pydantic ValidationError** | Envelope or model validation failed when building/serializing. | Fix field types and required fields; use `model_dump()`/`model_validate()` and handle validation in code. |
| 19 | **Connection refused / OSError** | TCP connection to host:port failed (e.g. nothing listening). | Start the agent; confirm host and port; check firewall and security groups. |
| 20 | **Path traversal / security** | Invalid or suspicious `FilePart` URI (e.g. `../` outside allowed base). | Use only allowed URIs; ensure server validates paths and rejects traversal attempts. |

### Example stack traces

**InvalidTransitionError** (state machine):

```text
asap.errors.InvalidTransitionError: Invalid transition from 'submitted' to 'completed'

  details: {"from_state": "submitted", "to_state": "completed"}
  code: asap:protocol/invalid_state
```

Fix: Transition through `running` (e.g. `submitted` → `running` → `completed`).

**ASAPConnectionError** (agent unreachable):

```text
asap.transport.client.ASAPConnectionError: Connection failed to http://localhost:8000.
Troubleshooting: Connection failed to http://localhost:8000. Verify the agent is running...
  url: http://localhost:8000
  cause: [Errno 61] Connection refused
```

Fix: Start the agent on the given URL or correct the URL/port.

---

## Chaos Failure Modes

This section describes failure modes validated by chaos testing (Sprint 8). It helps you tell **network vs agent** issues and what to expect in logs. See [ADR-017 Failure Injection](adr/ADR-017-failure-injection-strategy.md) and [Building Resilient Agents](tutorials/resilience.md).

### Scenarios from chaos tests

| Scenario | What is simulated | Expected client behavior | Typical error / log |
|----------|-------------------|---------------------------|----------------------|
| **Message loss** | Response never arrives (black hole, dropped response) | Retries up to `max_retries`, then raises `ASAPTimeoutError` | `Request to ... timed out after N seconds` |
| **Intermittent loss** | Some requests succeed, some time out | Retries; eventual success or `ASAPTimeoutError` after retries | Mix of success logs and timeout on final attempt |
| **Network partition** | Connection refused or unreachable | Retries with backoff, then `ASAPConnectionError` | `Connection failed to ... Connection refused` |
| **Circuit open** | Many consecutive failures | Client stops sending, raises `CircuitOpenError` | `Circuit breaker is OPEN for ... Too many consecutive failures` |
| **Clock skew (old)** | Envelope timestamp too old | Server rejects with `InvalidTimestampError` | `asap:protocol/invalid_timestamp`, `age_seconds` in details |
| **Clock skew (future)** | Envelope timestamp in the future | Server rejects with `InvalidTimestampError` | `asap:protocol/invalid_timestamp`, `future_offset_seconds` in details |
| **Server crash** | Server dies mid-request (connection reset) | Retries, then `ASAPConnectionError` (e.g. "Connection reset by peer") | `Connection reset by peer` or `Connection failed` |
| **Server 503** | Server shutting down or overloaded | Retries; may eventually get response or timeout/connection error | HTTP 503 in logs; client retries then may raise `ASAPConnectionError` or succeed |

### Expected logs vs actual failures

**When the network drops the response (message loss):**

- **Expected:** Client logs retries, then a single final timeout.
- **Actual failure:** You see `ASAPTimeoutError` with `timeout` set; no response body. Server logs may show the request as received and processed—so the **agent is fine**, the **network or path back to the client** dropped the response.

**When the agent is down or unreachable (partition/crash):**

- **Expected:** Connection errors, possibly retries then `ASAPConnectionError` or `CircuitOpenError`.
- **Actual failure:** `ASAPConnectionError` with cause like "Connection refused" or "Connection reset by peer". Server logs may show nothing (crashed) or "connection closed". So the **network path or the agent** is the problem.

**When clocks are wrong (clock skew):**

- **Expected:** Server rejects envelope with `InvalidTimestampError`; client gets `ASAPRemoteError` with code/data indicating `asap:protocol/invalid_timestamp`.
- **Actual failure:** No retry will fix this; **agent logic is fine**, **clock sync** (NTP, container time) is wrong on sender or receiver.

### Is it the network or the agent?

| Symptom | Likely cause | What to check |
|---------|----------------|----------------|
| `ASAPTimeoutError` after retries, server log shows "request received" | **Network** (response path): response lost or very slow | Client/server network path, load balancer timeouts, proxy. |
| `ASAPConnectionError` (refused, reset, unreachable) | **Network or agent**: server down, partition, or crash | Agent process up? Port open? Firewall? Restart/crash logs on server. |
| `CircuitOpenError` | **Network or agent**: many consecutive failures | Check why each request failed (timeout vs connection vs 5xx). Fix agent or network, then wait for circuit to half-open. |
| `InvalidTimestampError` / `InvalidNonceError` | **Agent/config**: bad clock or duplicate nonce | NTP on both sides; single source of nonces per sender. |
| `ASAPRemoteError` with `asap:task/not_found` or `asap:protocol/...` | **Agent**: business or protocol error on server | Server logs and error `data`; fix handler or request. |
| `HandlerNotFoundError` or JSON-RPC `METHOD_NOT_FOUND` | **Agent**: payload type not registered or wrong method | Register handler for that payload type or fix client method/params. |

Use **trace_id** and **correlation_id** in logs on both client and server to match a single request across the path and see whether the server saw it and how it responded.

---

## Debugging

Use this checklist and the tools below to debug ASAP issues systematically. See [Observability](observability.md) and [Metrics](metrics.md) for configuration details.

### Step-by-step debugging checklist

1. **Reproduce the issue**
   - Note the exact operation (e.g. `client.send(envelope)`, specific payload type).
   - Capture the full error message, exception type, and stack trace.
   - If intermittent, try to reproduce under load or with the same sequence of requests.

2. **Check server and client logs**
   - Enable structured logs (JSON in production) and set `ASAP_LOG_LEVEL=DEBUG` if needed.
   - Look for `asap.request.received`, `asap.request.processed`, and any `error` or `exception` entries.
   - Match requests across services using `trace_id` and `correlation_id` (see [Observability](observability.md)).

3. **Correlate with trace_id / correlation_id**
   - Extract `trace_id` from the failing request (envelope or log line).
   - Search server logs for the same `trace_id` to see if the request arrived and how it was processed.
   - If the server never logged the request, the failure is likely **network or client-side**. If the server logged an error, focus on **agent/handler logic**.

4. **Inspect metrics**
   - Query `/asap/metrics` on the agent: `curl http://<agent>:8000/asap/metrics`.
   - Check `asap_requests_error_total` by `error_type` and `payload_type`.
   - Check `asap_request_duration_seconds` for latency spikes or timeouts.
   - Compare with [Chaos Failure Modes](#chaos-failure-modes) to see if the pattern matches network vs agent.

5. **Visualize request flow (trace command)**
   - If logs are in ASAP JSON format, use the CLI to visualize a single trace:
   - `asap trace <trace-id> [--log-file asap.log] [--format ascii|json]`
   - This shows request flow and latency per hop (e.g. `agent_a -> agent_b (15ms) -> agent_c (23ms)`).

6. **Classify the failure**
   - Use the table [Is it the network or the agent?](#is-it-the-network-or-the-agent) in Chaos Failure Modes.
   - Apply the suggested checks (URL, firewall, handler registration, clock sync, etc.).

### Tools

| Tool | Purpose | Reference |
|------|---------|-----------|
| **Structured logs** | Request/response events, errors, trace context | [Observability](observability.md); `ASAP_LOG_LEVEL`, `ASAP_LOG_FORMAT` |
| **trace_id / correlation_id** | Correlate a request across client and server | [Observability](observability.md); bind in logs and search by ID |
| **asap trace** (CLI) | Visualize request flow and latency from JSON logs | `asap trace <trace-id> --log-file asap.log` |
| **Metrics** | Counts and latency histograms per payload type and error type | [Metrics](metrics.md); `GET /asap/metrics` |
| **Health endpoints** | Agent liveness and readiness | `GET /health`, `GET /ready`; see [Deployment (Kubernetes)](deployment/kubernetes.md) |

### Example: debugging a timeout

**Symptom:** Client raises `ASAPTimeoutError` after 30 seconds.

1. **Reproduce:** Same envelope, same agent URL; happens every time (or only under load).
2. **Logs:** Client log shows retries and final timeout. Search server logs for the client’s `trace_id`.
3. **If server log has the request:** Server received it; slow handler or overload. Check `asap_request_duration_seconds` and handler code. Consider increasing timeout or optimizing the handler.
4. **If server log has no request:** Request never reached the server (network, LB, or wrong URL). Check URL, firewall, and agent reachability.
5. **Metrics:** High `asap_request_duration_seconds` or many timeouts in `asap_requests_error_total` suggest server-side slowness or overload.

### Example: debugging "Connection refused"

**Symptom:** `ASAPConnectionError` with "Connection refused".

1. **Reproduce:** Note the exact URL (host and port).
2. **Check agent:** Is the process running? `curl -I http://<host>:<port>/health`. If 200, the agent is up; then check path (e.g. correct port and no typo in URL).
3. **Check network:** From the client host, `curl http://<host>:<port>/health`. If this fails, the issue is network or firewall, not application code.
4. **Logs:** Server may have no log for the request (connection never established). Fix connectivity or URL, then retry.

### Example: debugging InvalidTransitionError

**Symptom:** `InvalidTransitionError: Invalid transition from 'submitted' to 'completed'`.

1. **Reproduce:** Same sequence of payloads (e.g. sending a task update without a prior "running" update).
2. **Classify:** This is an **agent/protocol** error: the state machine disallows that transition.
3. **Fix:** Ensure state transitions follow the model (e.g. `submitted` → `running` → `completed`). Check client or orchestrator logic that sends status updates.
4. **Logs:** Server log should show the invalid transition; use `trace_id` to find the exact request and payload.

---

## Performance Tuning

This section covers connection pools, manifest caching, compression, and batch operations. For full benchmark results, see [benchmarks/RESULTS.md](https://github.com/asap-protocol/asap-protocol/blob/main/benchmarks/RESULTS.md) in the repository, or run `uv run pytest benchmarks/benchmark_transport.py --benchmark-only -v`.

### Connection pools

The ASAP client uses httpx connection pooling. Tuning pool size improves throughput when you have many concurrent requests to the same agent.

| Parameter | Default | When to increase |
|-----------|--------|-------------------|
| **pool_connections** | 100 | More idle keep-alive connections; use 200–500 for small clusters. |
| **pool_maxsize** | 100 | More concurrent connections; use 500–1000 for large clusters if OS limits allow. |
| **pool_timeout** | 5.0 | Increase if you see pool timeout errors under load (e.g. 30.0). |

**Before/after:** With default `pool_maxsize=100`, the client supports **1000+ concurrent requests** to the same host via connection reuse (benchmark: 1000 concurrent `send()` all succeed). Without pooling, each request would open a new connection and latency would increase under load.

```python
# Higher concurrency (e.g. many workers calling same agent)
async with ASAPClient(
    base_url="https://api.example.com",
    pool_connections=200,
    pool_maxsize=200,
    pool_timeout=30.0,
) as client:
    ...
```

Keep **HTTP/2** enabled (default) for multiplexing; it improves batch throughput.

### Manifest caching

The client caches agent manifests in memory with a TTL to avoid repeated GETs to `/.well-known/asap/manifest.json`.

| Setting | Default | Effect |
|---------|--------|--------|
| **default_ttl** | 300 s (5 min) | Longer TTL = fewer manifest requests, slightly staler manifest. |

**Before/after:** With caching, repeated `get_manifest()` calls for the same URL yield **>90% cache hit rate** (benchmark: 99% with 100 requests). Without cache, every call would trigger an HTTP GET.

Increase TTL if agents change manifest rarely; shorten it if you need quick reflection of manifest changes.

### Compression

Requests and responses can be compressed (gzip or Brotli) when the payload exceeds **1 KB** (configurable). This reduces bandwidth and can help on slow or costly links.

| Setting | Default | Effect |
|---------|--------|--------|
| **COMPRESSION_THRESHOLD** | 1024 (1 KB) | Payloads smaller than this are sent uncompressed. |
| **Algorithm** | gzip (br if available) | Brotli typically gives 10–20% better ratio than gzip for JSON. |

**Before/after (benchmarks):**

- **1 MB JSON payload:** gzip achieves **~70% size reduction** (compressed ≤30% of original); Brotli often 10–20% better.
- **Large envelopes:** End-to-end compress → decompress → deserialize is benchmarked; enable compression for large payloads to cut bandwidth.

Ensure the server supports `Content-Encoding: gzip` (or `br`); the ASAP server decompresses automatically.

### Batch operations

Use `send_batch()` instead of sequential `send()` when you have many envelopes for the same or multiple agents.

**Before/after:** With real HTTP/2, **batch send** gives roughly **10x throughput** vs sequential `send()` (benchmark target). With in-process or mock transport the speedup is lower; the gain is largest when network latency is significant.

```python
# Prefer batch when sending many envelopes
results = await client.send_batch(envelopes)  # parallel over HTTP/2
```

### Quick reference: tuning checklist

| Goal | Action |
|------|--------|
| Higher throughput to one agent | Increase `pool_maxsize`; keep HTTP/2 on; use `send_batch()` where applicable. |
| Fewer manifest round-trips | Rely on default cache (5 min TTL); increase TTL if manifests change rarely. |
| Lower bandwidth | Use default compression (auto for payloads >1 KB); install `brotli` for better ratio. |
| Lower latency under load | Horizontal scaling (multiple server instances); see [Deployment (Kubernetes)](deployment/kubernetes.md). |

---

## FAQ

Frequently asked questions grouped by category. For more detail, see the linked guides.

### Setup

**Q: How do I install ASAP?**  
A: `uv add asap-protocol` or `pip install asap-protocol`. See [index](index.md).

**Q: What Python version is required?**  
A: Python 3.13+. See [ADR-010 Python 3.13+](adr/ADR-010-python-313-requirement.md).

**Q: How do I run my first agent?**  
A: Follow [Building Your First Agent](tutorials/first-agent.md): create a server with a handler, then use `ASAPClient` to send envelopes.

**Q: How do I start the ASAP server?**  
A: `uv run uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000`. Or use `create_app()` and mount it in your own ASGI app.

**Q: Can I use ASAP over HTTP (not HTTPS)?**  
A: Yes for local development. Set `require_https=False` on the client. In production use HTTPS; see [Security](security.md).

**Q: How do I deploy ASAP in Kubernetes?**  
A: See [Deployment (Kubernetes)](deployment/kubernetes.md): Dockerfile, k8s manifests, Helm chart, health checks.

**Q: Where is the agent manifest?**  
A: `GET /.well-known/asap/manifest.json` on the agent base URL. The client uses it for discovery.

**Q: How do I register a handler for a payload type?**  
A: Use `HandlerRegistry.register(payload_type, handler)` before starting the server. Unregistered types raise `HandlerNotFoundError`.

**Q: Can I use ASAP with FastAPI/Starlette?**  
A: Yes. The ASAP server is FastAPI-based; you can mount it or reuse its `create_app()` and add your own routes.

**Q: How do I run the CLI?**  
A: `asap --version`, `asap list-schemas`, `asap trace <trace-id> [--log-file PATH]`. See [index](index.md).

### Config

**Q: What environment variables does ASAP use?**  
A: Server: `ASAP_RATE_LIMIT`, `ASAP_MAX_REQUEST_SIZE`, `ASAP_MAX_THREADS`, `ASAP_HOT_RELOAD`, `ASAP_DEBUG`. Logging: `ASAP_LOG_LEVEL`, `ASAP_LOG_FORMAT`, `ASAP_SERVICE_NAME`, `ASAP_DEBUG`, `ASAP_DEBUG_LOG`. See [Observability](observability.md) and server docstrings.

**Q: How do I increase the rate limit?**  
A: Set `ASAP_RATE_LIMIT` (e.g. `100/second;1000/minute`) or pass `rate_limit` to `create_app()`. See [Security](security.md).

**Q: How do I enable debug logging?**  
A: `ASAP_LOG_LEVEL=DEBUG`. For full request/response bodies use `ASAP_DEBUG_LOG=true` (development only). For full data and stack traces use `ASAP_DEBUG=true`.

**Q: How do I increase the request size limit?**  
A: Set `ASAP_MAX_REQUEST_SIZE` (bytes) or pass `max_request_size` to `create_app()`. Default is 10 MB.

**Q: How do I increase the number of worker threads?**  
A: Set `ASAP_MAX_THREADS` or pass `max_threads` to `create_app()`. Default is `min(32, cpu_count + 4)`.

**Q: How do I tune the connection pool?**  
A: Pass `pool_connections`, `pool_maxsize`, `pool_timeout` to `ASAPClient`. See [Performance Tuning](#performance-tuning) above.

**Q: How do I change the client timeout?**  
A: Pass `timeout=<seconds>` to `ASAPClient`. Default is 60.0.

**Q: How do I configure retries?**  
A: Use `RetryConfig` and pass it to `ASAPClient(retry_config=...)`. See [Building Resilient Agents](tutorials/resilience.md).

**Q: How do I enable or disable the circuit breaker?**  
A: Pass `circuit_breaker_enabled=True/False` to `ASAPClient`. You can also set threshold and timeout.

**Q: How long is the manifest cached?**  
A: Default TTL is 5 minutes (300 s). The client uses an in-memory cache; TTL is configurable on the cache.

**Q: How do I allow HTTP in production?**  
A: Not recommended. Use HTTPS. For local-only agents you can set `require_https=False` on the client.

### Errors

**Q: What does InvalidTransitionError mean?**  
A: You tried an invalid task state transition (e.g. `submitted` → `completed`). Use allowed transitions (e.g. `submitted` → `running` → `completed`). See [Common Errors](#common-errors).

**Q: What does MalformedEnvelopeError mean?**  
A: The envelope is invalid (missing fields, wrong types). Validate with Pydantic before sending.

**Q: What does TaskNotFoundError mean?**  
A: The requested task ID does not exist on the agent. Check `task_id` and that the task was created on the right agent.

**Q: What does ASAPConnectionError mean?**  
A: The HTTP connection failed (agent down, wrong URL, network/firewall). See [Error Handling](error-handling.md) and [Common Errors](#common-errors).

**Q: What does ASAPTimeoutError mean?**  
A: The request took longer than the client timeout. Increase `timeout` or optimize the handler/network.

**Q: What does CircuitOpenError mean?**  
A: The circuit breaker opened after consecutive failures. Wait for the timeout or fix the remote service; see [Chaos Failure Modes](#chaos-failure-modes).

**Q: What does InvalidTimestampError mean?**  
A: Envelope timestamp is too old (replay) or too far in the future (clock skew). Sync clocks (NTP) and stay within the allowed window.

**Q: What does InvalidNonceError mean?**  
A: Duplicate or invalid nonce (replay protection). Use a unique nonce per envelope; do not reuse within the TTL window.

**Q: What does HandlerNotFoundError mean?**  
A: No handler is registered for that payload type. Register one with `HandlerRegistry.register(payload_type, handler)`.

**Q: What does ThreadPoolExhaustedError mean?**  
A: All server worker threads are busy. Increase `max_threads` or optimize/use async handlers.

**Q: How do I know if the failure is network or agent?**  
A: Use the table [Is it the network or the agent?](#is-it-the-network-or-the-agent) in Chaos Failure Modes and correlate logs with `trace_id`/`correlation_id`.

**Q: Why do I get JSON-RPC INVALID_PARAMS?**  
A: The server rejected the envelope (validation failed). Check envelope structure and server logs for details.

### Best practices

**Q: Should I set trace_id and correlation_id?**  
A: Yes. They help correlate requests across client and server. Bind them in logs; see [Observability](observability.md).

**Q: Should I use retries?**  
A: Yes for transient failures. Use `RetryConfig` and optionally a circuit breaker. See [Building Resilient Agents](tutorials/resilience.md).

**Q: When should I use send_batch()?**  
A: When sending many envelopes to one or more agents; it improves throughput with HTTP/2. See [Performance Tuning](#performance-tuning).

**Q: When is compression used?**  
A: Automatically for payloads larger than 1 KB (configurable). Use default settings for large payloads to reduce bandwidth.

**Q: How do I secure tokens in logs?**  
A: Do not set `ASAP_DEBUG`/`ASAP_DEBUG_LOG` in production; sensitive fields are redacted unless debug is on. See [Observability](observability.md).

**Q: What rate limit should I use in production?**  
A: Depends on load. Default `10/second;100/minute` allows bursts; for high throughput use a higher limit (e.g. from benchmarks). See [Security](security.md).

**Q: How do I monitor ASAP in production?**  
A: Use `/asap/metrics` (Prometheus), `/health` and `/ready`, and structured logs with trace_id. See [Metrics](metrics.md) and [Deployment](deployment/kubernetes.md).

**Q: Where can I find a production checklist?**  
A: See [Production Deployment Checklist](tutorials/production-checklist.md).

**Q: How do I test resilience?**  
A: Use retries, circuit breaker, and timeouts; run chaos tests. See [Building Resilient Agents](tutorials/resilience.md) and [Testing](testing.md).

**Q: What state transitions are allowed for tasks?**  
A: Follow the task state machine (e.g. submitted → running → completed/failed). See [State Management](state-management.md) and [ADR-005](adr/ADR-005-state-machine-design.md).
