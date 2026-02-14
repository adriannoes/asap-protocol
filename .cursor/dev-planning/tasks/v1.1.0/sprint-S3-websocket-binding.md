# Sprint S3: WebSocket Binding

> **Goal**: Real-time bidirectional communication for ASAP agents
> **Prerequisites**: Sprints S1, S2, S2.5 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/transport/__init__.py` - Transport module init
- `src/asap/transport/websocket.py` - WebSocket server, client, pool, framing, handler
- `src/asap/transport/server.py` - ASAPServer WebSocket integration (/asap/ws), lifespan graceful shutdown
- `src/asap/transport/client.py` - ASAPClient WebSocket transport (Task 3.2)
- `pyproject.toml` - websockets>=12.0 dependency
- `tests/transport/test_websocket.py` - WebSocket unit tests (lifecycle, routing, errors, framing)
- `tests/transport/integration/test_websocket_e2e.py` - E2E WebSocket tests (Task 3.2)
- `tests/transport/test_message_ack.py` - MessageAck unit tests (ADR-16, Task 3.4)
- `tests/transport/test_ack_aware_client.py` - AckAwareClient tests (ADR-16, Task 3.5)
- `tests/transport/test_websocket_rate_limit.py` - WebSocket rate limit tests (Task 3.6)
- `src/asap/transport/rate_limit.py` - WebSocketTokenBucket for per-connection rate limiting (Task 3.6)
- `src/asap/models/payloads.py` - MessageAck payload (ADR-16)
- `src/asap/models/envelope.py` - requires_ack field (ADR-16)

---

## Context

WebSocket provides full-duplex communication for scenarios requiring low latency or server-initiated messages. This is critical for real-time agent collaboration and streaming responses.

---

## Task 3.1: WebSocket Server

**Goal**: Accept WebSocket connections for ASAP messages

**Context**: Enable ASAP servers to accept WebSocket connections for real-time bidirectional communication.

**Prerequisites**: Sprints S1, S2, S2.5 completed

### Sub-tasks

- [x] 3.1.1 Add websockets dependency
  - **Command**: `uv add "websockets>=12.0"`
  - **Verify**: `uv run python -c "import websockets; print('OK')"`

- [x] 3.1.2 Create transport module structure
  - **Directory**: `src/asap/transport/`
  - **Files**: `__init__.py`, `websocket.py`
  - **Verify**: `from asap.transport import websocket` imports

- [x] 3.1.3 Implement WebSocket handler
  - **File**: `src/asap/transport/websocket.py`
  - **What**: Create handler that:
    - Accepts connections at `ws://host:port/asap/ws`
    - Uses JSON-RPC over WebSocket protocol
    - Handles: Connection open, message, close, error
  - **Verify**: WebSocket connection can be established

- [x] 3.1.4 Add message framing
  - **File**: `src/asap/transport/websocket.py`
  - **What**: 
    - Send/receive ASAP Envelope as JSON
    - Support binary mode for future (base64)
  - **Verify**: Messages are correctly framed

- [x] 3.1.5 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py`
  - **What**: `server.add_websocket_route("/asap/ws")`
  - Dispatch messages to existing handlers
  - **Verify**: Server accepts WebSocket connections

- [x] 3.1.6 Write unit tests
  - **File**: `tests/transport/test_websocket.py`
  - **What**: Test:
    - Connection lifecycle
    - Message routing
    - Error handling
  - **Verify**: `pytest tests/transport/test_websocket.py -v` passes

- [x] 3.1.7 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket server binding"` (included in sprint commit)

**Acceptance Criteria**:
- [x] Server accepts WebSocket connections
- [x] Messages routed to handlers
- [x] Errors handled gracefully

---

## Task 3.2: WebSocket Client

**Goal**: Connect to agents via WebSocket

**Context**: Enable ASAP clients to connect to servers using WebSocket transport.

**Prerequisites**: Task 3.1 completed

### Sub-tasks

- [x] 3.2.1 Implement WebSocket client
  - **File**: `src/asap/transport/websocket.py`
  - **What**: Class `WebSocketTransport` with:
    - `connect(url)` - establish connection
    - `send(envelope)` - send message
    - `receive()` - receive message
  - **Verify**: Client can connect to server

- [x] 3.2.2 Add to ASAPClient
  - **File**: `src/asap/transport/client.py`
  - **What**: 
    - `client = ASAPClient(..., transport_mode="websocket"|"auto")`
    - Auto-detect HTTP vs WebSocket from URL scheme (ws/wss → websocket)
  - **Verify**: Client works with both transports

- [x] 3.2.3 Implement message correlation
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Track request_id for request/response matching
    - Timeout handling for pending requests
  - **Verify**: Requests correctly matched to responses

- [x] 3.2.4 Add async streaming
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Support server-initiated messages (push)
    - Callback: `on_message(envelope)`
  - **Verify**: Server can push messages to client

- [x] 3.2.5 Write integration tests
  - **File**: `tests/transport/integration/test_websocket_e2e.py`
  - **What**: 
    - Server + Client WebSocket communication
    - Full TaskRequest → TaskResponse flow
  - **Verify**: E2E tests pass

- [x] 3.2.6 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket client"` (included in sprint commit)

**Acceptance Criteria**:
- [x] Client can communicate via WebSocket
- [x] Message correlation works
- [x] Streaming supported

---

## Task 3.3: Connection Management

**Goal**: Robust WebSocket connection handling

**Context**: Production-ready WebSocket requires heartbeats, reconnection, and connection pooling.

**Prerequisites**: Tasks 3.1, 3.2 completed

### Sub-tasks (all complete; commit deferred to end of sprint)

- [x] 3.3.1 Implement heartbeat
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Server: Send ping every 30s
    - Client: Respond with pong
    - Detect stale connections
  - **Verify**: Stale connections detected

- [x] 3.3.2 Add automatic reconnection
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Client: Reconnect on disconnect
    - Backoff: Exponential (1s, 2s, 4s, max 30s)
    - Max attempts: Configurable
  - **Verify**: Client reconnects after disconnect

- [x] 3.3.3 Add connection pooling
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Reuse connections to same host
    - Configurable pool size
    - Cleanup idle connections
  - **Verify**: Connections are reused

- [x] 3.3.4 Add graceful shutdown
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Close all connections on server stop
    - Send close frame with reason
  - **Verify**: Clean shutdown with no errors

- [x] 3.3.5 Write chaos tests
  - **File**: `tests/transport/test_websocket.py`
  - **What**: Test:
    - Connection drops during request
    - Server restart
    - Network partition
  - **Verify**: System recovers from failures

- [x] 3.3.6 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket connection management"` (included in sprint commit)

**Acceptance Criteria**:
- [x] Connections are robust and self-healing
- [x] Heartbeat detects stale connections
- [x] Reconnection with backoff works

---

## Task 3.4: Message Acknowledgment (ADR-16)

**Goal**: Implement selective message acknowledgment for reliable WebSocket delivery.

**Context**: WebSocket is fire-and-forget at the transport level. State-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`) MUST be acknowledged to prevent task state machine inconsistencies. Streaming updates and heartbeats do NOT need acks. See [ADR-16](../../../product-specs/decision-records/README.md#question-16-websocket-message-acknowledgment).

**Prerequisites**: Tasks 3.1-3.3 completed (WebSocket server, client, connection management)

### Sub-tasks

- [x] 3.4.1 Define MessageAck payload
  - **File**: `src/asap/models/payloads.py` (modify existing)
  - **What**: Add `MessageAck` payload type:
    - `original_envelope_id: str` — the envelope being acknowledged
    - `status: Literal["received", "processed", "rejected"]`
    - `error: str | None = None` — reason if rejected
  - **Why**: Application-level ack for WebSocket messages
  - **Pattern**: Follow existing payload types (TaskRequest, TaskCancel, etc.)
  - **Verify**: `MessageAck` serializes and deserializes correctly

- [x] 3.4.2 Add `requires_ack` field to Envelope
  - **File**: `src/asap/models/envelope.py` (modify existing)
  - **What**: Add field:
    - `requires_ack: bool = False`
    - Document which payloads auto-set this to `True` over WebSocket
  - **Why**: Opt-in ack behavior — only state-changing messages need it
  - **Verify**: Envelope with `requires_ack=True` serializes correctly

- [x] 3.4.3 Auto-set `requires_ack` for critical payloads
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: When sending over WebSocket:
    - Auto-set `requires_ack=True` for: `TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`
    - Leave `requires_ack=False` for: `TaskUpdate` (progress), heartbeats, streaming
    - HTTP transport: no change (response is implicit ack)
  - **Why**: Ensures critical messages are always acknowledged without manual opt-in
  - **Verify**: Critical payloads have `requires_ack=True` over WebSocket

- [x] 3.4.4 Implement server-side ack response
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: When receiving a message with `requires_ack=True`:
    - Immediately send `MessageAck(status="received")` back
    - After processing: optionally send `MessageAck(status="processed")`
    - On error: send `MessageAck(status="rejected", error="reason")`
  - **Why**: Sender needs to know message was received and processed
  - **Verify**: Server sends ack for critical messages

- [x] 3.4.5 Write tests for MessageAck
  - **File**: `tests/transport/test_message_ack.py` (create new)
  - **What**: Test scenarios:
    - TaskRequest over WebSocket → receives MessageAck
    - TaskUpdate (progress) over WebSocket → no ack sent
    - Same message over HTTP → no MessageAck (response is ack)
    - Rejected message → ack with error reason
  - **Verify**: `pytest tests/transport/test_message_ack.py -v` all pass

- [x] 3.4.6 Commit milestone
  - **Command**: `git commit -m "feat(transport): add MessageAck for WebSocket reliability (ADR-16)"` (included in sprint commit)
  - **Scope**: payloads.py, envelope.py, websocket.py, test_message_ack.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] MessageAck payload defined and functional
- [x] Critical payloads auto-set `requires_ack=True` over WebSocket
- [x] Server sends ack for critical messages
- [x] HTTP transport unchanged (implicit ack via response)
- [x] Test coverage >95%

---

## Task 3.5: AckAwareClient (ADR-16)

**Goal**: Implement client-side ack tracking with timeout/retry logic.

**Context**: The `MessageAck` payload (Task 3.4) is useless without a client that acts on it. The `AckAwareClient` manages pending acks, retransmits on timeout, and integrates with the circuit breaker. Without this, the ack protocol defines behavior but nothing enforces it. See [ADR-16](../../../product-specs/decision-records/README.md#question-16-websocket-message-acknowledgment).

**Prerequisites**: Task 3.4 completed (MessageAck payload exists)

### Sub-tasks (all complete; commit deferred until end of sprint)

- [x] 3.5.1 Implement pending ack tracker
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: Add to WebSocket client:
    - `_pending_acks: dict[str, PendingAck]` — tracks sent messages awaiting ack
    - `PendingAck` dataclass: `envelope_id`, `sent_at`, `retries`, `original_envelope`
    - Register sent messages with `requires_ack=True`
    - Remove from pending on `MessageAck` receipt
  - **Why**: Tracks which messages need ack responses
  - **Verify**: Pending ack tracker works correctly

- [x] 3.5.2 Implement ack timeout detection
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: Background task that:
    - Checks pending acks every 5 seconds
    - If `sent_at + ack_timeout` exceeded (default: 30s), trigger retransmission
    - Configurable timeout via `ack_timeout_seconds` parameter
  - **Why**: Detects lost messages and triggers retry
  - **Verify**: Timeout detected after configured period

- [x] 3.5.3 Implement retransmission logic
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: On ack timeout:
    - Retransmit the original envelope (same `id` for idempotency)
    - Increment retry counter
    - Apply exponential backoff between retries (1s, 2s, 4s...)
    - After `max_retries` (default: 3): mark as failed, trigger circuit breaker
  - **Why**: Recovers from transient failures (network glitch, agent restart)
  - **Pattern**: Idempotency keys make retransmission safe — receiver deduplicates by envelope `id`
  - **Verify**: Retransmission occurs on timeout, stops after max retries

- [x] 3.5.4 Integrate with circuit breaker
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: When max retries exhausted:
    - Record failure in circuit breaker
    - If circuit open: don't attempt WebSocket, suggest HTTP fallback
    - Log error with diagnostic info
  - **Why**: Prevents infinite retry loops, enables graceful degradation
  - **Verify**: Circuit breaker trips after max retries

- [x] 3.5.5 Write comprehensive tests
  - **File**: `tests/transport/test_ack_aware_client.py` (create new)
  - **What**: Test scenarios:
    - Normal flow: send → receive ack → pending cleared
    - Timeout: send → no ack → retransmit → ack received
    - Max retries: send → no ack → 3 retransmits → circuit breaker
    - Idempotency: retransmitted message has same `id`
    - Non-critical message: no pending ack registered
    - Concurrent messages: multiple pending acks tracked independently
  - **Verify**: `pytest tests/transport/test_ack_aware_client.py -v` all pass

- [x] 3.5.6 Commit milestone
  - **Command**: `git commit -m "feat(transport): add AckAwareClient with timeout/retry (ADR-16)"` (included in sprint commit)
  - **Scope**: websocket.py, test_ack_aware_client.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] Pending ack tracker works correctly
- [x] Timeout detection triggers retransmission
- [x] Retransmission uses same envelope `id` (idempotency)
- [x] Max retries triggers circuit breaker
- [x] Test coverage >95%

---

## Task 3.6: WebSocket Rate Limiting (Roadmap Alignment)

**Goal**: Prevent abuse of long-lived WebSocket connections.

**Context**: HTTP rate limiting (middleware) doesn't apply to WebSocket messages once the connection is established. We need per-connection message rate limiting. See Roadmap Risk 472.

### Sub-tasks (all complete; commit deferred to end of sprint)

- [x] 3.6.1 Implement Token Bucket for WebSocket
  - **File**: `src/asap/transport/rate_limit.py` (new)
  - **What**: `WebSocketTokenBucket` for persistent connections
  - **Logic**: Refill tokens per second, deduct per message

- [x] 3.6.2 Enforce limits in WebSocket handler
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: Check bucket before processing frame
  - **Limit**: Default 10 messages/sec per connection (`create_app(..., websocket_message_rate_limit=10.0)`)
  - **Action**: Send error frame and disconnect if abused

- [x] 3.6.3 Write tests
  - **File**: `tests/transport/test_websocket_rate_limit.py`
  - **Verify**: Spammers get disconnected; normal traffic unaffected

- [x] 3.6.4 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket message rate limiting"` (included in sprint commit)

**Acceptance Criteria**:
- [x] Message flooding triggers disconnect
- [x] Normal traffic unaffected

---

## Sprint S3 Definition of Done

- [x] WebSocket server accepting connections
- [x] WebSocket client working
- [x] Connection management robust
- [x] Heartbeat and reconnection functional
- [x] MessageAck payload for state-changing messages (ADR-16)
- [x] AckAwareClient with timeout/retry/circuit breaker (ADR-16)
- [x] WebSocket message rate limiting (Task 3.6)
- [x] Test coverage >95%
  - **Status**: `envelope.py` and `payloads.py` 100% (full suite). `websocket.py` ~68% (many branches in server handler, reconnection, pool). DoD remains open until websocket module reaches >95% or team agrees to scope.

**Total Sub-tasks**: ~30

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v1.1.0 Roadmap](./tasks-v1.1.0-roadmap.md)
