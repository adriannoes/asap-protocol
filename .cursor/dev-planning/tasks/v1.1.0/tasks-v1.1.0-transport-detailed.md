# Tasks: ASAP v1.1.0 Transport (S3-S4) - Detailed

> **Sprints**: S3-S4 - WebSocket and Webhooks
> **Goal**: Real-time communication and event-driven callbacks

---

## Relevant Files

### Sprint S3: WebSocket
- `src/asap/transport/__init__.py` - Transport module init
- `src/asap/transport/websocket.py` - WebSocket server and client
- `tests/transport/test_websocket.py` - WebSocket tests
- `tests/integration/test_websocket_e2e.py` - E2E WebSocket tests

### Sprint S4: Webhooks
- `src/asap/transport/webhook.py` - Webhook delivery
- `tests/transport/test_webhook.py` - Webhook tests

---

## Sprint S3: WebSocket Binding

### Task 3.1: WebSocket Server

**Goal**: Accept WebSocket connections for ASAP messages

- [ ] 3.1.1 Add websockets dependency
  - Command: `uv add "websockets>=12.0"`

- [ ] 3.1.2 Create transport module structure
  - Directory: `src/asap/transport/`
  - Files: `__init__.py`, `websocket.py`

- [ ] 3.1.3 Implement WebSocket handler
  - Accept: `ws://host:port/asap/ws`
  - Protocol: JSON-RPC over WebSocket
  - Handle: Connection open, message, close, error

- [ ] 3.1.4 Add message framing
  - Send/receive ASAP Envelope as JSON
  - Support binary mode for future (base64)

- [ ] 3.1.5 Integrate with ASAPServer
  - `server.add_websocket_route("/asap/ws")`
  - Dispatch messages to existing handlers

- [ ] 3.1.6 Write unit tests
  - Test: Connection lifecycle
  - Test: Message routing
  - Test: Error handling

- [ ] 3.1.7 Commit
  - Command: `git commit -m "feat(transport): add WebSocket server binding"`

**Acceptance**: Server accepts WebSocket connections

---

### Task 3.2: WebSocket Client

**Goal**: Connect to agents via WebSocket

- [ ] 3.2.1 Implement WebSocket client
  - Class: `WebSocketTransport`
  - Method: `connect(url)`, `send(envelope)`, `receive()`

- [ ] 3.2.2 Add to ASAPClient
  - `client = ASAPClient(transport="websocket")`
  - Auto-detect: HTTP vs WebSocket from URL scheme

- [ ] 3.2.3 Implement message correlation
  - Track request_id for request/response matching
  - Timeout handling for pending requests

- [ ] 3.2.4 Add async streaming
  - Support: Server-initiated messages (push)
  - Callback: `on_message(envelope)`

- [ ] 3.2.5 Write integration tests
  - Server + Client WebSocket communication
  - Full TaskRequest → TaskResponse flow

- [ ] 3.2.6 Commit
  - Command: `git commit -m "feat(transport): add WebSocket client"`

**Acceptance**: Client can communicate via WebSocket

---

### Task 3.3: Connection Management

**Goal**: Robust WebSocket connection handling

- [ ] 3.3.1 Implement heartbeat
  - Server: Send ping every 30s
  - Client: Respond with pong
  - Detect: Stale connections

- [ ] 3.3.2 Add automatic reconnection
  - Client: Reconnect on disconnect
  - Backoff: Exponential (1s, 2s, 4s, max 30s)
  - Max attempts: Configurable

- [ ] 3.3.3 Add connection pooling
  - Reuse connections to same host
  - Configurable pool size
  - Cleanup idle connections

- [ ] 3.3.4 Add graceful shutdown
  - Close all connections on server stop
  - Send close frame with reason

- [ ] 3.3.5 Write chaos tests
  - Test: Connection drops during request
  - Test: Server restart
  - Test: Network partition

- [ ] 3.3.6 Commit
  - Command: `git commit -m "feat(transport): add WebSocket connection management"`

**Acceptance**: Connections are robust and self-healing

---

## Sprint S4: Webhooks & Release

### Task 4.1: Webhook Delivery

**Goal**: POST callbacks to registered URLs

- [ ] 4.1.1 Create webhook module
  - File: `src/asap/transport/webhook.py`
  - Class: `WebhookDelivery`

- [ ] 4.1.2 Implement URL validation (SSRF prevention)
  - Block: Private IPs (10.x, 192.168.x, 127.x)
  - Block: localhost, link-local
  - Allow: Only HTTPS in production
  - Reference: Backlog item [P0] Security

- [ ] 4.1.3 Implement delivery
  - POST payload as JSON
  - Include: HMAC signature header
  - Timeout: Configurable (default 10s)

- [ ] 4.1.4 Add signature verification
  - Header: `X-ASAP-Signature`
  - Algorithm: HMAC-SHA256
  - Payload: Request body

- [ ] 4.1.5 Write security tests
  - Test: SSRF blocked
  - Test: Signature verified
  - Test: HTTPS enforced in production

- [ ] 4.1.6 Commit
  - Command: `git commit -m "feat(transport): add webhook delivery with SSRF protection"`

**Acceptance**: Webhooks deliver securely

---

### Task 4.2: Callback Retry Logic

**Goal**: Reliable webhook delivery

- [ ] 4.2.1 Implement retry queue
  - In-memory queue (v1.1)
  - Future: Persistent queue option

- [ ] 4.2.2 Add exponential backoff
  - Delays: 1s, 2s, 4s, 8s, 16s
  - Max retries: 5

- [ ] 4.2.3 Add dead letter handling
  - After max retries: Log and emit event
  - Optional: callback for DLQ handling

- [ ] 4.2.4 Add rate limiting for callbacks
  - Per-URL rate limit
  - Default: 10/second per URL

- [ ] 4.2.5 Write tests
  - Test: Retry on 5xx
  - Test: Don't retry on 4xx
  - Test: DLQ after max retries

- [ ] 4.2.6 Commit
  - Command: `git commit -m "feat(transport): add webhook retry with exponential backoff"`

**Acceptance**: Failed webhooks retry reliably

---

### Task 4.2.5: Migrate from slowapi (Tech Debt)

**Goal**: Replace slowapi with custom rate limiter to fix deprecation warnings

**Context**: slowapi uses `asyncio.iscoroutinefunction` which is deprecated in Python 3.12+ and will be removed in 3.16. Migrating now keeps us ahead of the curve.

- [ ] 4.2.5.1 Evaluate alternatives
  - Option A: Use `limits` package directly (slowapi's backend)
  - Option B: Custom middleware using `limits` + in-memory storage
  - Decision: Choose based on simplicity and testability

- [ ] 4.2.5.2 Implement custom rate limiter
  - File: `src/asap/transport/rate_limit.py` (new)
  - Use `limits` package directly
  - Maintain current API: `create_limiter()`, `rate_limit_handler()`
  - Keep `memory://` storage, document Redis option

- [ ] 4.2.5.3 Update middleware.py
  - Remove slowapi imports
  - Use new `rate_limit.py` module
  - Keep backward compatibility

- [ ] 4.2.5.4 Update pyproject.toml
  - Remove: `slowapi>=0.1.9`
  - Add: `limits>=3.0` (if not already transitive dep)

- [ ] 4.2.5.5 Verify deprecation warnings gone
  - Command: `uv run pytest --tb=short 2>&1 | grep -i deprecat`
  - Target: No asyncio deprecation warnings

- [ ] 4.2.5.6 Run rate limiting tests
  - Command: `uv run pytest tests/transport/test_rate_limiting.py -v`
  - Ensure all tests pass

- [ ] 4.2.5.7 Commit
  - Command: `git commit -m "refactor(transport): migrate from slowapi to custom rate limiter"`

**Acceptance**: No deprecation warnings, rate limiting works

---

### Task 4.3: Comprehensive Testing

**Goal**: Validate v1.1.0 features

- [ ] 4.3.1 Run all unit tests
  - Command: `uv run pytest tests/ -v`
  - Target: 100% pass, >95% coverage

- [ ] 4.3.2 Run integration tests
  - WebSocket + OAuth2 flow
  - Discovery + Task execution

- [ ] 4.3.3 Run property tests
  - Add: Properties for new models

- [ ] 4.3.4 Update documentation
  - API reference for new features
  - Examples for OAuth2, WebSocket, Webhooks

**Acceptance**: All tests pass

---

### Task 4.4: Release Preparation

**Goal**: Prepare v1.1.0 release materials

- [ ] 4.4.1 Update CHANGELOG.md
  - Section: [1.1.0] - YYYY-MM-DD
  - List: All new features

- [ ] 4.4.2 Bump version
  - File: `pyproject.toml`
  - Value: `1.1.0`

- [ ] 4.4.3 Update README
  - Add: OAuth2 quick start
  - Add: WebSocket example

- [ ] 4.4.4 Update AGENTS.md
  - Add: OAuth2 setup commands and environment variables
  - Add: WebSocket patterns and connection management
  - Update: Security considerations with auth info

- [ ] 4.4.5 Review all docs
  - Verify: Examples work
  - Verify: Links valid

- [ ] 4.4.6 Complete checkpoint CP-1
  - File: [checkpoints.md](../../checkpoints.md#cp-1-post-v110-release)
  - Review learnings and update velocity tracking

**Acceptance**: Release materials ready

---

### Task 4.5: Build and Publish

**Goal**: Publish v1.1.0

- [ ] 4.5.1 Create release branch
  - Branch: `release/v1.1.0`

- [ ] 4.5.2 Run CI pipeline
  - Verify: All checks pass

- [ ] 4.5.3 Tag release
  - Command: `git tag v1.1.0`

- [ ] 4.5.4 Publish to PyPI
  - Command: `uv publish`

- [ ] 4.5.5 Create GitHub release
  - Tag: v1.1.0
  - Notes: From CHANGELOG

- [ ] 4.5.6 Update Docker images
  - Push: `ghcr.io/adriannoes/asap-protocol:v1.1.0`

**Acceptance**: v1.1.0 published

---

## Task 4.6: Mark Sprints S3-S4 Complete

- [ ] 4.6.1 Update roadmap progress
  - Mark all S3-S4 tasks complete
  - Update progress to 100%

- [ ] 4.6.2 Verify release
  - Confirm: PyPI package installable
  - Confirm: Docker image runnable

**Acceptance**: v1.1.0 released, roadmap complete

---

**S3-S4 Definition of Done**:
- [ ] WebSocket server and client working
- [ ] Connection management robust
- [ ] Webhooks deliver with SSRF protection
- [ ] Retry logic functional
- [ ] All tests pass
- [ ] v1.1.0 on PyPI

**Total Sub-tasks**: ~40
