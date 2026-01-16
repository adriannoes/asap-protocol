# PRD: ASAP Protocol Python Implementation

## 1. Introduction/Overview

This PRD covers the implementation of **ASAP (Async Simple Agent Protocol)** as a Python library. ASAP is a protocol for agent-to-agent communication designed to be simpler than Google's A2A while maintaining MCP compatibility.

**Problem**: Existing agent protocols (A2A) are complex, have N² scalability issues, and lack native state persistence. Developers need a simpler, more scalable alternative.

**Solution**: A Python library implementing the ASAP protocol specification, enabling developers to build agents that communicate via typed messages over HTTP/JSON-RPC.

---

## 2. Goals

| Goal | Metric |
|------|--------|
| **Functional protocol** | Two agents can exchange TaskRequest → TaskUpdate → TaskResponse |
| **Type-safe models** | All 8 core entities have Pydantic models with JSON Schema export |
| **Validated messages** | All 12 payload types pass schema validation |
| **HTTP transport** | Working JSON-RPC 2.0 binding over HTTP |
| **State persistence** | Snapshot mode working for task state |

---

## 3. User Stories

### Developer Building an Agent
> As a **developer building an AI agent**, I want to **send task requests to other agents using typed Python objects** so that **I don't have to manually construct JSON payloads**.

### Developer Receiving Tasks
> As a **developer creating an agent that receives tasks**, I want to **validate incoming messages against the protocol schema** so that **I can reject malformed requests early**.

### Developer Debugging
> As a **developer debugging agent interactions**, I want to **see correlation IDs and trace IDs in all messages** so that **I can trace issues across agent boundaries**.

### Developer Persisting State
> As a **developer with long-running tasks**, I want to **save and restore task state via snapshots** so that **tasks can survive agent restarts**.

---

## 4. Functional Requirements

### 4.1 Core Models (Priority 1)

1. The library MUST provide Pydantic models for all 8 core entities:
   - `Agent`, `Manifest`, `Conversation`, `Task`, `Message`, `Part`, `Artifact`, `StateSnapshot`

2. The library MUST provide Pydantic models for all 5 Part types:
   - `TextPart`, `DataPart`, `FilePart`, `ResourcePart`, `TemplatePart`

3. The library MUST provide a unified `Envelope` model with all required fields:
   - `asap_version`, `id`, `correlation_id`, `trace_id`, `timestamp`, `sender`, `recipient`, `payload_type`, `payload`, `extensions`

4. All models MUST export valid JSON Schemas via `model_json_schema()`.

### 4.2 Payload Types (Priority 1)

5. The library MUST implement all 8 core payload types:
   - `TaskRequest`, `TaskResponse`, `TaskUpdate`, `TaskCancel`
   - `MessageSend`, `StateQuery`, `StateRestore`, `ArtifactNotify`

6. The library MUST implement all 4 MCP integration payloads:
   - `McpToolCall`, `McpToolResult`, `McpResourceFetch`, `McpResourceData`

7. Each payload MUST have a discriminator field `payload_type` for automatic deserialization.

### 4.3 Task State Machine (Priority 2)

8. The library MUST implement task states: `submitted`, `working`, `input_required`, `paused`, `completed`, `failed`, `cancelled`, `rejected`.

9. The library MUST validate state transitions according to the spec diagram.

10. The library MUST prevent invalid transitions (e.g., `completed` → `working`).

### 4.4 State Persistence (Priority 2)

11. The library MUST support `snapshot` mode for state persistence.

12. The library MUST provide `StateSnapshot` creation with auto-incrementing version.

13. The library SHOULD support `event-sourced` mode as optional feature.

### 4.5 HTTP Transport (Priority 3)

14. The library MUST provide a FastAPI-based server for receiving ASAP messages.

15. The library MUST provide an httpx-based client for sending ASAP messages.

16. Messages MUST be transported as JSON-RPC 2.0 requests.

17. The server MUST expose manifest at `/.well-known/asap/manifest.json`.

### 4.6 Observability (Priority 4)

18. All envelopes MUST auto-generate `id` if not provided (ULID format).

19. All envelopes MUST include `timestamp` in ISO 8601 format.

20. The library SHOULD provide helper for creating correlated messages.

---

## 5. Non-Goals (Out of Scope)

- ❌ WebSocket transport binding (future v1.2025.06)
- ❌ gRPC transport binding (future)
- ❌ Message broker integration (NATS, Kafka)
- ❌ Full MCP server implementation
- ❌ OAuth2 authentication (MVP uses Bearer tokens only)
- ❌ mTLS support
- ❌ Production-ready agent examples

---

## 6. Design Considerations

### Project Structure

```
asap-protocol/
└── src/
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── entities.py      # Agent, Task, Conversation, etc.
    │   ├── parts.py         # TextPart, DataPart, etc.
    │   ├── payloads.py      # TaskRequest, TaskResponse, etc.
    │   └── envelope.py      # Envelope wrapper
    ├── state/
    │   ├── __init__.py
    │   ├── machine.py       # State transitions
    │   └── snapshot.py      # Persistence
    ├── transport/
    │   ├── __init__.py
    │   ├── server.py        # FastAPI app
    │   └── client.py        # httpx client
    └── errors.py            # Error taxonomy
├── schemas/                      # Exported JSON Schemas
├── tests/
├── examples/
├── pyproject.toml
└── README.md
```

### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | ^2.0 | Models, validation, JSON Schema |
| fastapi | ^0.100 | HTTP server |
| httpx | ^0.25 | HTTP client |
├── examples/
├── pyproject.toml
└── README.md
```

### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | ^2.0 | Models, validation, JSON Schema |
| fastapi | ^0.100 | HTTP server |
| httpx | ^0.25 | HTTP client |
| uvicorn | ^0.24 | ASGI server |
| ulid-py | ^1.1 | ID generation |

---

## 7. Technical Considerations

### Pydantic Discriminated Unions

Payloads should use discriminated unions for automatic type detection:

```python
from pydantic import BaseModel, Field
from typing import Literal, Union

class TaskRequest(BaseModel):
    payload_type: Literal["TaskRequest"] = "TaskRequest"
    # ... fields

class TaskResponse(BaseModel):
    payload_type: Literal["TaskResponse"] = "TaskResponse"
    # ... fields

Payload = Union[TaskRequest, TaskResponse, ...]  # Discriminated union
```

### State Machine Pattern

```python
VALID_TRANSITIONS = {
    "submitted": {"working", "rejected"},
    "working": {"completed", "failed", "cancelled", "input_required", "paused"},
    # ... etc
}

def transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())
```

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Schema coverage | 100% | All entities export valid JSON Schema |
| Test coverage | >80% | pytest-cov report |
| E2E validation | Pass | Two agents complete TaskRequest → TaskResponse flow |
| Performance | <50ms | Single message round-trip on localhost |

---

## 9. Architectural Decisions

### 9.1 ID Format: ULID

| Option | Sortable | Size | Library |
|--------|----------|------|---------|
| **ULID** ✅ | Yes | 26 chars | `python-ulid` |
| UUIDv4 | No | 36 chars | stdlib |
| UUIDv7 | Yes | 36 chars | `uuid6` |

**Decision**: ULID

| Pros | Cons |
|------|------|
| Lexicographically sortable | Less native DB support |
| Compact (26 chars) | External dependency |
| Extractable timestamp | Less familiar to devs |

**Rationale**: ASAP needs temporal ordering for debugging. 26 chars is more compact in JSON. Timestamp extraction aids observability.

---

### 9.2 Client API: Async-first

| Option | API |
|--------|-----|
| **Async-first** ✅ | `await client.send(...)` |
| Sync-only | `client.send(...)` |

**Decision**: Async-first with sync wrapper

| Pros | Cons |
|------|------|
| Superior I/O performance | Requires asyncio knowledge |
| Natural for long-running agents | Simple scripts more verbose |
| Aligned with httpx async | -- |

**Usage**:
```python
# Primary (async)
async with ASAPClient(...) as client:
    response = await client.send_task(request)

# Convenience wrapper (sync)
response = send_task_sync(client, request)
```

---

### 9.3 Schema Publication: In-repo

| Option | Location |
|--------|----------|
| **In-repo** ✅ | `/schemas/*.json` |
| CDN/Website | asap-protocol.org |

**Decision**: In-repo `/schemas` + Pydantic export

| Pros | Cons |
|------|------|
| Versioned with code | Long URLs |
| PR review for changes | Not canonical |
| Zero extra infra | -- |

**Structure**:
```
schemas/
├── envelope.schema.json
├── payloads/
│   └── task-request.schema.json
└── entities/
    └── agent.schema.json
```

---

### 9.4 Error Responses: Hybrid

| Option | Format |
|--------|--------|
| Pure JSON-RPC | Standard errors only |
| ASAP Envelope | Custom `ErrorResponse` payload |
| **Hybrid** ✅ | JSON-RPC + ASAP codes in `data` |

**Decision**: Hybrid

| Pros | Cons |
|------|------|
| JSON-RPC 2.0 compliant | Slightly more complex |
| ASAP error codes in `data` | -- |
| Correlation tracking preserved | -- |

**Format**:
```json
{
  "jsonrpc": "2.0",
  "id": "req_123",
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": {
      "asap_error": "asap:protocol/malformed_envelope",
      "correlation_id": "corr_456"
    }
  }
}
```

---

## 10. Milestones

| Milestone | Deliverable | Est. Effort |
|-----------|-------------|-------------|
| M1: Models | All Pydantic models + schemas | 2 days |
| M2: State | Task state machine + snapshots | 1 day |
| M3: Transport | FastAPI server + httpx client | 2 days |
| M4: Integration | E2E test with 2 agents | 1 day |
| M5: Polish | Docs, examples, packaging | 1 day |

**Total estimated effort**: ~7 days

> **Note**: See [SPRINT_PLAN.md](../../docs/SPRINT_PLAN.md) for detailed task breakdown.