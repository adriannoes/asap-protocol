# Migration Guide

> Migrating from A2A (Agent-to-Agent) and MCP (Model Context Protocol) to ASAP.

---

## Overview

ASAP (Agent State and Action Protocol) builds upon concepts from both A2A and MCP, providing a unified protocol for agent-to-agent communication. This guide helps developers migrate existing agents to ASAP.

### Protocol Comparison

| Feature | A2A | MCP | ASAP |
|---------|-----|-----|------|
| **Focus** | Agent communication | Tool/resource access | Unified agent protocol |
| **State Management** | Limited | None | First-class snapshots |
| **Message Format** | JSON | JSON-RPC | JSON-RPC + Envelope |
| **Discovery** | Agent Card | Server info | Manifest |
| **Task Lifecycle** | Basic | N/A | Full state machine |
| **Streaming** | SSE | Stdio/SSE | WebSocket (planned) |

---

## Envelope and Payload Mapping

### A2A to ASAP

#### A2A Message Structure

```json
{
  "type": "task",
  "id": "task-123",
  "from": "agent-a",
  "to": "agent-b",
  "content": {
    "action": "research",
    "input": {"query": "AI trends"}
  }
}
```

#### ASAP Envelope Structure

```json
{
  "id": "env_01HX5K4P...",
  "asap_version": "0.1",
  "timestamp": "2024-01-15T10:30:00Z",
  "sender": "urn:asap:agent:agent-a",
  "recipient": "urn:asap:agent:agent-b",
  "payload_type": "task.request",
  "payload": {
    "conversation_id": "conv_01HX5K3M...",
    "skill_id": "research",
    "input": {"query": "AI trends"}
  },
  "trace_id": "trace_01HX5K..."
}
```

#### Key Differences

| A2A Field | ASAP Field | Notes |
|-----------|------------|-------|
| `type` | `payload_type` | More specific typing |
| `id` | `id` | ULID format in ASAP |
| `from` | `sender` | URN format required |
| `to` | `recipient` | URN format required |
| `content` | `payload` | Structured per payload type |
| *(none)* | `asap_version` | Protocol versioning |
| *(none)* | `timestamp` | Auto-generated |
| *(none)* | `trace_id` | Distributed tracing |
| *(none)* | `correlation_id` | Request/response pairing |

### MCP to ASAP

#### MCP Tool Call

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "web_search",
    "arguments": {"query": "AI trends"}
  },
  "id": 1
}
```

#### ASAP MCP Tool Call

```json
{
  "jsonrpc": "2.0",
  "method": "asap.send",
  "params": {
    "envelope": {
      "asap_version": "0.1",
      "sender": "urn:asap:agent:coordinator",
      "recipient": "urn:asap:agent:tools-agent",
      "payload_type": "mcp.tool_call",
      "payload": {
        "request_id": "req_01HX5K...",
        "tool_name": "web_search",
        "arguments": {"query": "AI trends"},
        "mcp_context": {}
      }
    }
  },
  "id": "req-1"
}
```

#### Key Differences

| MCP Field | ASAP Field | Notes |
|-----------|------------|-------|
| `method` | `payload_type` | `mcp.tool_call` for tools |
| `params.name` | `payload.tool_name` | Tool identifier |
| `params.arguments` | `payload.arguments` | Same structure |
| *(none)* | `sender`/`recipient` | Agent identity |
| *(none)* | `mcp_context` | Additional context |

---

## Agent Card to Manifest

### A2A Agent Card

```json
{
  "name": "Research Agent",
  "description": "Performs web research",
  "url": "https://agent.example.com",
  "capabilities": ["research", "summarize"],
  "authentication": {
    "type": "bearer"
  }
}
```

### ASAP Manifest

```json
{
  "id": "urn:asap:agent:research-v1",
  "name": "Research Agent",
  "version": "1.0.0",
  "description": "Performs web research",
  "capabilities": {
    "asap_version": "0.1",
    "skills": [
      {
        "id": "research",
        "description": "Search and analyze information",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"}
      },
      {
        "id": "summarize",
        "description": "Summarize content",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"}
      }
    ],
    "state_persistence": true,
    "streaming": false,
    "mcp_tools": []
  },
  "endpoints": {
    "asap": "https://agent.example.com/asap",
    "events": null
  },
  "auth": {
    "schemes": ["bearer"],
    "oauth2": null
  }
}
```

### Key Improvements in ASAP

| Feature | A2A Agent Card | ASAP Manifest |
|---------|----------------|---------------|
| **Identity** | URL-based | URN-based (`urn:asap:agent:*`) |
| **Versioning** | None | Semantic versioning |
| **Skills** | String list | Structured with schemas |
| **State** | Not specified | `state_persistence` flag |
| **Endpoints** | Single URL | Multiple endpoints |
| **Validation** | None | JSON Schema for I/O |

---

## Payload Type Mapping

### Task Operations

| A2A Action | MCP Method | ASAP Payload Type |
|------------|------------|-------------------|
| `task.create` | N/A | `task.request` |
| `task.status` | N/A | `task.response` |
| `task.update` | N/A | `task.update` |
| `task.cancel` | N/A | `task.cancel` |

### MCP Operations

| MCP Method | ASAP Payload Type |
|------------|-------------------|
| `tools/call` | `mcp.tool_call` |
| `tools/call` (response) | `mcp.tool_result` |
| `resources/read` | `mcp.resource_fetch` |
| `resources/read` (response) | `mcp.resource_data` |

### Message Operations

| Operation | ASAP Payload Type |
|-----------|-------------------|
| Send message | `message.send` |
| Query state | `state.query` |
| Restore state | `state.restore` |
| Notify artifact | `artifact.notify` |

---

## Migration Checklist

### Phase 1: Preparation

- [ ] **Review current protocol usage**
  - Document all A2A/MCP endpoints in use
  - List all message types and payloads
  - Identify state management patterns

- [ ] **Plan agent identity**
  - Define URN format: `urn:asap:agent:{agent-name}`
  - Plan versioning strategy (semantic versioning)
  - Document skill definitions

- [ ] **Set up ASAP dependencies**
  ```bash
  # Install ASAP protocol library
  pip install asap-protocol
  # Or with uv
  uv add asap-protocol
  ```

### Phase 2: Manifest Creation

- [ ] **Create agent manifest**
  ```python
  from asap.models.entities import (
      Manifest, Capability, Endpoint, Skill, AuthScheme
  )
  
  manifest = Manifest(
      id="urn:asap:agent:my-agent",
      name="My Agent",
      version="1.0.0",
      description="Migrated from A2A/MCP",
      capabilities=Capability(
          asap_version="0.1",
          skills=[
              Skill(id="skill1", description="..."),
              # Add all skills
          ],
          state_persistence=True,  # Enable if needed
          streaming=False,
          mcp_tools=["tool1", "tool2"],  # MCP tools
      ),
      endpoints=Endpoint(asap="https://my-agent.example.com/asap"),
      auth=AuthScheme(schemes=["bearer"]),
  )
  ```

- [ ] **Expose manifest endpoint**
  ```python
  # Manifest will be available at:
  # GET /.well-known/asap/manifest.json
  ```

### Phase 3: Message Conversion

- [ ] **Update message sending**
  ```python
  # Before (A2A style)
  message = {"type": "task", "from": "agent-a", ...}
  response = requests.post(url, json=message)
  
  # After (ASAP)
  from asap.transport.client import ASAPClient
  from asap.models.envelope import Envelope
  
  envelope = Envelope(
      asap_version="0.1",
      sender="urn:asap:agent:agent-a",
      recipient="urn:asap:agent:agent-b",
      payload_type="task.request",
      payload={...}
  )
  
  async with ASAPClient(base_url=url) as client:
      response = await client.send(envelope)
  ```

- [ ] **Update message receiving**
  ```python
  # Use ASAP server with handler registry
  from asap.transport.server import create_app
  from asap.transport.handlers import HandlerRegistry
  
  registry = HandlerRegistry()
  registry.register("task.request", handle_task_request)
  
  app = create_app(manifest, registry)
  ```

### Phase 4: State Management

- [ ] **Implement state snapshots** (if using state persistence)
  ```python
  from asap.state.snapshot import InMemorySnapshotStore
  from asap.models.entities import StateSnapshot
  
  store = InMemorySnapshotStore()
  
  # Save state
  snapshot = StateSnapshot(
      id=generate_id(),
      task_id=task.id,
      version=1,
      data={"current_state": "..."},
      checkpoint=True,
      created_at=datetime.now(timezone.utc),
  )
  store.save(snapshot)
  
  # Restore state
  restored = store.get(task_id)
  ```

- [ ] **Use state machine for task lifecycle**
  ```python
  from asap.state.machine import transition, can_transition
  from asap.models.enums import TaskStatus
  
  # Validate and perform transition
  if can_transition(task.status, TaskStatus.COMPLETED):
      task = transition(task, TaskStatus.COMPLETED)
  ```

### Phase 5: Testing

- [ ] **Unit tests for new handlers**
  ```python
  import pytest
  from asap.transport.server import create_app
  from fastapi.testclient import TestClient
  
  def test_task_request():
      app = create_app(manifest)
      client = TestClient(app)
      
      response = client.post("/asap", json={
          "jsonrpc": "2.0",
          "method": "asap.send",
          "params": {"envelope": {...}},
          "id": "test-1"
      })
      
      assert response.status_code == 200
  ```

- [ ] **Integration tests**
  ```python
  @pytest.mark.asyncio
  async def test_full_flow():
      async with ASAPClient(base_url="http://localhost:8000") as client:
          response = await client.send(envelope)
          assert response.payload_type == "task.response"
  ```

- [ ] **Verify manifest discovery**
  ```bash
  curl http://localhost:8000/.well-known/asap/manifest.json
  ```

### Phase 6: Deployment

- [ ] **Update API documentation**
- [ ] **Configure monitoring** (trace IDs, logging)
- [ ] **Set up TLS** (required for production)
- [ ] **Configure authentication**
- [ ] **Gradual rollout**
  - Deploy ASAP endpoint alongside existing
  - Route traffic gradually
  - Monitor for errors
  - Deprecate old endpoints

---

## Common Migration Patterns

### Pattern 1: Dual-Protocol Support

Run both A2A/MCP and ASAP during transition:

```python
from fastapi import FastAPI

app = FastAPI()

# Legacy A2A endpoint
@app.post("/a2a")
async def handle_a2a(request: dict):
    # Convert to ASAP internally
    envelope = convert_a2a_to_asap(request)
    return await process_envelope(envelope)

# New ASAP endpoint
@app.post("/asap")
async def handle_asap(request: dict):
    return await process_envelope(request)
```

### Pattern 2: MCP Tool Wrapper

Wrap existing MCP tools for ASAP:

```python
from asap.transport.handlers import HandlerRegistry

def create_mcp_handler(mcp_tool_function):
    """Wrap MCP tool as ASAP handler."""
    def handler(envelope, manifest):
        tool_name = envelope.payload["tool_name"]
        arguments = envelope.payload["arguments"]
        
        # Call original MCP tool
        result = mcp_tool_function(tool_name, arguments)
        
        # Return ASAP response
        return create_tool_result_envelope(envelope, result)
    
    return handler

registry = HandlerRegistry()
registry.register("mcp.tool_call", create_mcp_handler(call_mcp_tool))
```

### Pattern 3: State Migration

Migrate existing state to ASAP snapshots:

```python
async def migrate_state(old_state_store, new_snapshot_store):
    """Migrate state from old format to ASAP snapshots."""
    for task_id, state in old_state_store.items():
        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=task_id,
            version=1,
            data=state,
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        new_snapshot_store.save(snapshot)
```

---

## Upgrading ASAP Protocol Versions

### Version History

ASAP Protocol has evolved through the following releases:
- **v0.1.0** (2026-01-23): Initial alpha release with core models, state management, and HTTP transport
- **v0.3.0** (2026-01-26): Test infrastructure refactoring and stability improvements
- **v0.5.0** (2026-01-28): Security-hardened release with authentication, DoS protection, and comprehensive security features

### Upgrading from v0.1.0 or v0.3.0 to v0.5.0

v0.5.0 is a **security-hardened release** with zero breaking changes. All existing code from v0.1.0 and v0.3.0 will work without modifications.

**Upgrade Paths:**
- **v0.1.0 → v0.5.0**: Direct upgrade supported (tested and verified)
- **v0.3.0 → v0.5.0**: Direct upgrade supported (tested and verified)
- **v0.1.0 → v0.3.0 → v0.5.0**: Sequential upgrade also supported

#### What's New in v0.5.0

- **Security Features** (all opt-in):
  - Bearer token authentication
  - Timestamp validation (5-minute window)
  - Optional nonce validation for replay attack prevention
  - Rate limiting (100 req/min, configurable)
  - Request size limits (10MB, configurable)
  - HTTPS enforcement (client-side)
  - Secure logging (automatic sanitization)

- **Retry Logic**:
  - Exponential backoff with jitter
  - Circuit breaker pattern
  - `Retry-After` header support

- **Code Quality**:
  - Full mypy strict compliance
  - Enhanced error handling
  - Improved test coverage (95.90%)

#### Upgrade Steps

1. **Update Dependencies**:
   ```bash
   pip install --upgrade asap-protocol==0.5.0
   # or
   uv add asap-protocol==0.5.0
   ```

2. **Verify Compatibility**:
   Your existing code should work without changes:
   ```python
   # This code from v0.1.0/v0.3.0 still works in v0.5.0
   from asap.models.entities import Manifest, Capability, Endpoint, Skill
   from asap.transport.handlers import HandlerRegistry, create_echo_handler
   from asap.transport.server import create_app
   
   manifest = Manifest(
       id="urn:asap:agent:my-agent",
       name="My Agent",
       version="1.0.0",
       description="My agent",
       capabilities=Capability(
           asap_version="0.1",
           skills=[Skill(id="echo", description="Echo skill")],
           state_persistence=False,
       ),
       endpoints=Endpoint(asap="http://127.0.0.1:8000/asap"),
   )
   
   registry = HandlerRegistry()
   registry.register("task.request", create_echo_handler())
   app = create_app(manifest, registry)
   ```

3. **Opt-in to Security Features** (optional):
   ```python
   from asap.models.entities import AuthScheme
   from asap.transport.middleware import BearerTokenValidator
   
   # Add authentication (optional)
   def validate_token(token: str) -> str | None:
       if token == "my-secret-token":
           return "urn:asap:agent:client"
       return None
   
   manifest = Manifest(
       # ... existing manifest ...
       auth=AuthScheme(schemes=["bearer"])  # Enable authentication
   )
   
   app = create_app(
       manifest,
       registry,
       token_validator=validate_token,  # Add token validator
       rate_limit="10/second;100/minute", # Burst + sustained rate limiting
       require_nonce=True                # Enable nonce validation
   )
   ```

4. **Test Your Upgrade**:
   ```bash
   # Run compatibility tests
   uv run python -m pytest tests/compatibility/ -v
   ```

#### Backward Compatibility

- ✅ **No breaking changes**: All v0.1.0 and v0.3.0 APIs remain unchanged
- ✅ **Security features are opt-in**: Existing deployments continue to work
- ✅ **Default behavior unchanged**: Rate limiting and size limits have safe defaults
- ✅ **Examples still work**: All example code from previous versions is compatible

#### Migration Checklist

- [ ] Update `asap-protocol` to v0.5.0
- [ ] Run existing tests to verify compatibility
- [ ] Review security features and opt-in as needed
- [ ] Update documentation if using new security features
- [ ] Test in staging environment before production deployment

#### What Changed Between Versions

**v0.1.0 → v0.3.0** (2026-01-26):
- Test infrastructure refactoring
- Improved test stability and isolation
- Fixed rate limiter initialization issues
- Enhanced test organization (unit/integration/E2E separation)

**v0.3.0 → v0.5.0** (2026-01-28):
- Security hardening (authentication, DoS protection, replay prevention)
- Retry logic with exponential backoff
- Secure logging with automatic sanitization
- Enhanced code quality (mypy strict compliance)
- Improved test coverage (95.90%)

#### Need Help?

- See [Security Guide](security.md) for authentication setup
- See [Transport Guide](transport.md) for retry configuration
- Run compatibility tests: `tests/compatibility/test_v0_1_0_compatibility.py`
- Check [CHANGELOG.md](../../CHANGELOG.md) for detailed changes

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Invalid agent URN` | URN format incorrect | Use `urn:asap:agent:{name}` |
| `Missing correlation_id` | Response without correlation | Add `correlation_id` to responses |
| `Method not found` | Wrong JSON-RPC method | Use `asap.send` |
| `Invalid envelope` | Missing required fields | Check `sender`, `recipient`, `payload_type` |

### Validation

Use CLI to validate messages:

```bash
# Export schemas for reference
asap export-schemas --output-dir ./schemas

# List available schemas
asap list-schemas

# Show specific schema
asap show-schema Envelope
```

---

## Related Documentation

- [Transport](transport.md) - HTTP/JSON-RPC details
- [Security](security.md) - Authentication setup
- [State Management](state-management.md) - Snapshots and lifecycle
- [API Reference](api-reference.md) - Complete API docs
