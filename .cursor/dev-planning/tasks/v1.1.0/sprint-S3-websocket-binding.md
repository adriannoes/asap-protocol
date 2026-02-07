# Sprint S3: WebSocket Binding

> **Goal**: Real-time bidirectional communication for ASAP agents
> **Prerequisites**: Sprints S1-S2 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/transport/__init__.py` - Transport module init
- `src/asap/transport/websocket.py` - WebSocket server and client
- `src/asap/transport/server.py` - ASAPServer WebSocket integration
- `src/asap/transport/client.py` - ASAPClient WebSocket transport
- `tests/transport/test_websocket.py` - WebSocket unit tests
- `tests/integration/test_websocket_e2e.py` - E2E WebSocket tests

---

## Context

WebSocket provides full-duplex communication for scenarios requiring low latency or server-initiated messages. This is critical for real-time agent collaboration and streaming responses.

---

## Task 3.1: WebSocket Server

**Goal**: Accept WebSocket connections for ASAP messages

**Context**: Enable ASAP servers to accept WebSocket connections for real-time bidirectional communication.

**Prerequisites**: Sprints S1-S2 completed

### Sub-tasks

- [ ] 3.1.1 Add websockets dependency
  - **Command**: `uv add "websockets>=12.0"`
  - **Verify**: `uv run python -c "import websockets; print('OK')"`

- [ ] 3.1.2 Create transport module structure
  - **Directory**: `src/asap/transport/`
  - **Files**: `__init__.py`, `websocket.py`
  - **Verify**: `from asap.transport import websocket` imports

- [ ] 3.1.3 Implement WebSocket handler
  - **File**: `src/asap/transport/websocket.py`
  - **What**: Create handler that:
    - Accepts connections at `ws://host:port/asap/ws`
    - Uses JSON-RPC over WebSocket protocol
    - Handles: Connection open, message, close, error
  - **Verify**: WebSocket connection can be established

- [ ] 3.1.4 Add message framing
  - **File**: `src/asap/transport/websocket.py`
  - **What**: 
    - Send/receive ASAP Envelope as JSON
    - Support binary mode for future (base64)
  - **Verify**: Messages are correctly framed

- [ ] 3.1.5 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py`
  - **What**: `server.add_websocket_route("/asap/ws")`
  - Dispatch messages to existing handlers
  - **Verify**: Server accepts WebSocket connections

- [ ] 3.1.6 Write unit tests
  - **File**: `tests/transport/test_websocket.py`
  - **What**: Test:
    - Connection lifecycle
    - Message routing
    - Error handling
  - **Verify**: `pytest tests/transport/test_websocket.py -v` passes

- [ ] 3.1.7 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket server binding"`

**Acceptance Criteria**:
- [ ] Server accepts WebSocket connections
- [ ] Messages routed to handlers
- [ ] Errors handled gracefully

---

## Task 3.2: WebSocket Client

**Goal**: Connect to agents via WebSocket

**Context**: Enable ASAP clients to connect to servers using WebSocket transport.

**Prerequisites**: Task 3.1 completed

### Sub-tasks

- [ ] 3.2.1 Implement WebSocket client
  - **File**: `src/asap/transport/websocket.py`
  - **What**: Class `WebSocketTransport` with:
    - `connect(url)` - establish connection
    - `send(envelope)` - send message
    - `receive()` - receive message
  - **Verify**: Client can connect to server

- [ ] 3.2.2 Add to ASAPClient
  - **File**: `src/asap/transport/client.py`
  - **What**: 
    - `client = ASAPClient(transport="websocket")`
    - Auto-detect HTTP vs WebSocket from URL scheme
  - **Verify**: Client works with both transports

- [ ] 3.2.3 Implement message correlation
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Track request_id for request/response matching
    - Timeout handling for pending requests
  - **Verify**: Requests correctly matched to responses

- [ ] 3.2.4 Add async streaming
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Support server-initiated messages (push)
    - Callback: `on_message(envelope)`
  - **Verify**: Server can push messages to client

- [ ] 3.2.5 Write integration tests
  - **File**: `tests/integration/test_websocket_e2e.py`
  - **What**: 
    - Server + Client WebSocket communication
    - Full TaskRequest → TaskResponse flow
  - **Verify**: E2E tests pass

- [ ] 3.2.6 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket client"`

**Acceptance Criteria**:
- [ ] Client can communicate via WebSocket
- [ ] Message correlation works
- [ ] Streaming supported

---

## Task 3.3: Connection Management

**Goal**: Robust WebSocket connection handling

**Context**: Production-ready WebSocket requires heartbeats, reconnection, and connection pooling.

**Prerequisites**: Tasks 3.1, 3.2 completed

### Sub-tasks

- [ ] 3.3.1 Implement heartbeat
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Server: Send ping every 30s
    - Client: Respond with pong
    - Detect stale connections
  - **Verify**: Stale connections detected

- [ ] 3.3.2 Add automatic reconnection
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Client: Reconnect on disconnect
    - Backoff: Exponential (1s, 2s, 4s, max 30s)
    - Max attempts: Configurable
  - **Verify**: Client reconnects after disconnect

- [ ] 3.3.3 Add connection pooling
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Reuse connections to same host
    - Configurable pool size
    - Cleanup idle connections
  - **Verify**: Connections are reused

- [ ] 3.3.4 Add graceful shutdown
  - **File**: `src/asap/transport/websocket.py`
  - **What**:
    - Close all connections on server stop
    - Send close frame with reason
  - **Verify**: Clean shutdown with no errors

- [ ] 3.3.5 Write chaos tests
  - **File**: `tests/transport/test_websocket.py`
  - **What**: Test:
    - Connection drops during request
    - Server restart
    - Network partition
  - **Verify**: System recovers from failures

- [ ] 3.3.6 Commit
  - **Command**: `git commit -m "feat(transport): add WebSocket connection management"`

**Acceptance Criteria**:
- [ ] Connections are robust and self-healing
- [ ] Heartbeat detects stale connections
- [ ] Reconnection with backoff works

---

## Sprint S3 Definition of Done

- [ ] WebSocket server accepting connections
- [ ] WebSocket client working
- [ ] Connection management robust
- [ ] Heartbeat and reconnection functional
- [ ] Test coverage >95%

**Total Sub-tasks**: ~18
