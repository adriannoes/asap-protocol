# ASAP Protocol: Protocol Decisions

> **Category**: Wire Protocol & Transport
> **Focus**: JSON-RPC, Envelopes, Errors, Reliability

---

## Question 2: Why JSON-RPC Over REST for Primary Binding?

### The Question
The spec recommends HTTP + JSON-RPC as the canonical binding (Section 13.1). Is this the right choice given REST's ubiquity?

### Analysis

| Criterion | JSON-RPC | REST | gRPC |
|-----------|----------|------|------|
| A2A/MCP alignment | ✅ Native match | ❌ Paradigm mismatch | ⚠️ Partial (A2A supports) |
| Browser support | ✅ Full | ✅ Full | ❌ Requires proxy |
| Streaming | ⚠️ Needs SSE/WS | ⚠️ Needs SSE/WS | ✅ Native |
| Method semantics | ✅ Explicit methods | ⚠️ Resource-oriented | ✅ Explicit methods |
| Schema validation | ⚠️ Manual | ⚠️ OpenAPI | ✅ Protobuf |
| Performance | Medium | Medium | High |
| Learning curve | Low | Very low | Medium-high |

### Expert Assessment

**Why JSON-RPC wins for ASAP**:
1. **A2A compatibility**: A2A uses JSON-RPC 2.0; alignment reduces bridging friction
2. **Method-centric**: Agents think in terms of "actions" (TaskRequest, TaskCancel), not "resources"
3. **Simpler async semantics**: JSON-RPC's request/response model maps cleanly to our async patterns
4. **MCP consistency**: MCP also uses JSON-RPC

**Why not REST**:
- Resource-oriented design feels forced for agent coordination
- Mapping task state machines to HTTP verbs (GET/PUT/PATCH) is awkward
- Over-fetching/under-fetching issues irrelevant for structured agent messages

**Why defer gRPC**:
- Adds Protobuf toolchain requirement
- Limited browser support complicates demos/debugging
- Performance gains matter less than adoption barriers for MVP

### Recommendation: **KEEP**

JSON-RPC is the correct choice. Add explicit rationale to spec.

### Spec Amendment

> [!NOTE]
> Added to Section 13.1: JSON-RPC selected for A2A/MCP ecosystem alignment and method-centric semantics that match agent interaction patterns. gRPC binding deferred to v0.2 for performance-critical deployments.

---

## Question 5: Is MCP Envelope Approach Optimal?

### The Question
Section 8 wraps MCP calls in ASAP envelopes (`McpToolCall`, `McpToolResult`). Is this the right integration pattern?

### Analysis

**Integration Patterns Considered**:

| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| **Envelope** (current) | ASAP wraps MCP | Clean separation, routing flexibility | Extra layer, translation overhead |
| **Passthrough** | Forward MCP unchanged | Zero overhead | Loses ASAP tracing/correlation |
| **Unified** | Merge into single protocol | Simplest conceptually | Massive spec, A2A/MCP conflict |
| **Sidecar** | MCP as separate channel | Independent scaling | Coordination complexity |

### Expert Assessment

**Envelope approach is correct because**:
1. **Correlation**: ASAP envelope carries `trace_id`, `correlation_id`
2. **Routing**: ASAP handles agent-to-agent routing; MCP handles tool execution
3. **Auth boundary**: ASAP auth may differ from MCP tool auth
4. **Observability**: Unified logging across both protocols

**Edge case concern**: What if MCP tool returns large binary data?

### Recommendation: **KEEP with clarification**

Add streaming support for large MCP responses.

### Spec Amendment

> [!NOTE]
> Added to Section 8.2: For large MCP tool results, the `McpToolResult` payload MAY contain a `stream_uri` instead of inline `result`, enabling chunked delivery via ASAP streaming mechanisms.

---

## Question 7: Is Error Model Complete?

### The Question
Section 13.4 mentions namespaced error codes but doesn't define core errors. Is the error model complete?

### Analysis

**Essential Error Categories**:
1. **Protocol errors** (malformed messages)
2. **Routing errors** (agent not found)
3. **Capability errors** (skill not available)
4. **Execution errors** (task failed)
5. **Resource errors** (quota exceeded)
6. **Security errors** (auth failed)

**A2A Error Codes** (for reference):
- `ContentTypeNotSupportedError`
- `UnsupportedOperationError`
- `TaskNotFoundError`
- `InvalidRequestError`

### Recommendation: **ADD**

Define core error taxonomy.

### Spec Amendment

> [!NOTE]
> Added Error Taxonomy to spec:

```
Core Error Codes:
├── asap:protocol
│   ├── malformed_envelope
│   ├── invalid_payload_type
│   └── version_mismatch
├── asap:routing
│   ├── agent_not_found
│   ├── agent_unreachable
│   └── conversation_expired
├── asap:capability
│   ├── skill_not_found
│   ├── skill_unavailable
│   └── input_validation_failed
├── asap:execution
│   ├── task_failed
│   ├── task_timeout
│   └── task_cancelled
├── asap:resource
│   ├── quota_exceeded
│   ├── rate_limited
│   └── storage_full
└── asap:security
    ├── auth_required
    ├── auth_invalid
    └── permission_denied
```

---

## Question 16: WebSocket Message Acknowledgment

### The Question
WebSocket is fire-and-forget at the transport level. HTTP has implicit acks (response = received), but WebSocket does not. If an agent crashes mid-message, the sender never knows. How do we ensure reliable delivery for state-changing messages over WebSocket?

### Analysis

**The problem**: Without application-level acknowledgment, WebSocket provides "at-most-once" delivery. For state-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`), this is insufficient — a lost message could leave the task state machine in an inconsistent state.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| Full ack for all messages | Rejected | Doubles traffic, overkill for streaming/progress |
| Auto-ack for all WebSocket messages | Rejected | Same traffic doubling issue |
| **Ack only for state-changing messages** | ✅ Selected | Balanced: critical messages reliable, streaming fast |
| Defer to v1.2 | Rejected | May disappoint enterprise users expecting reliability |

### Expert Assessment

State-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`) MUST be acknowledged — they affect the task state machine. Streaming updates (`TaskUpdate` with `progress`) and heartbeats do NOT need acks — they're ephemeral. This aligns with existing `correlation_id` field in Envelope.

**Critical addition**: The `MessageAck` payload is useless without an `AckAwareClient` that manages the timeout/retry loop. The client must track pending acks, retransmit on timeout (using same `id` for idempotency), and integrate with the circuit breaker for max retries.

### Decision

> [!IMPORTANT]
> **ADR-16**: Add **selective message acknowledgment** for WebSocket transport. State-changing payloads automatically set `requires_ack=True`. Receiver responds with `MessageAck` payload referencing the original `envelope_id`.
>
> **Components**:
> 1. `MessageAck` payload type with `original_envelope_id` and `status` fields
> 2. `requires_ack: bool = False` field on Envelope (auto-set for state-changing payloads over WebSocket)
> 3. `AckAwareClient` that manages timeout/retry loop:
>    - Tracks pending acks with configurable timeout (default: 30s)
>    - On timeout: retransmits same message with same `id` (idempotency key ensures safety)
>    - Configurable max retries before circuit breaker trips
> 4. HTTP transport continues to use synchronous response as implicit ack
>
> **Payloads requiring ack**: `TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`
> **Payloads NOT requiring ack**: `TaskUpdate` (progress), heartbeats, streaming
>
> **Rationale**: Balances reliability for critical messages with performance for streaming. Idempotency keys make retransmission safe. The `AckAwareClient` is essential — without it, the ack protocol defines behavior but nothing enforces it.
>
> **Impact**: Added as Tasks in Sprint S3 (WebSocket Binding).
>
> **Date**: 2026-02-07
