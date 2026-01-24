# Transport Layer Guide

> HTTP/JSON-RPC binding details for ASAP protocol communication.

---

## Overview

ASAP uses HTTP as the transport layer with JSON-RPC 2.0 as the message framing protocol. This provides:

- **Standard HTTP semantics**: Familiar request/response model
- **JSON-RPC 2.0**: Structured RPC with error handling and correlation
- **Agent Discovery**: Well-known manifest endpoint for capability discovery

---

## Endpoints

### POST `/asap` - Message Endpoint

The primary endpoint for all ASAP protocol messages. Accepts JSON-RPC 2.0 wrapped envelopes.

#### Request Format

```http
POST /asap HTTP/1.1
Host: agent.example.com
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "asap.send",
  "params": {
    "envelope": {
      "asap_version": "0.1",
      "sender": "urn:asap:agent:coordinator",
      "recipient": "urn:asap:agent:research-v1",
      "payload_type": "task.request",
      "payload": {
        "conversation_id": "conv_01HX5K3MQVN8...",
        "skill_id": "web_research",
        "input": {
          "query": "Latest AI developments"
        }
      }
    }
  },
  "id": "req-123"
}
```

#### Response Format (Success)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "result": {
    "envelope": {
      "id": "env_01HX5K4P...",
      "asap_version": "0.1",
      "timestamp": "2024-01-15T10:30:00Z",
      "sender": "urn:asap:agent:research-v1",
      "recipient": "urn:asap:agent:coordinator",
      "payload_type": "task.response",
      "payload": {
        "task_id": "task_01HX5K4N...",
        "status": "completed",
        "result": {
          "summary": "Recent AI developments include..."
        }
      },
      "correlation_id": "env_original_request_id",
      "trace_id": "trace_01HX5K..."
    }
  },
  "id": "req-123"
}
```

#### Response Format (Error)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "error": "Missing 'envelope' in params"
    }
  },
  "id": "req-123"
}
```

> **Note**: JSON-RPC errors always return HTTP 200. The error is in the response body.

### GET `/.well-known/asap/manifest.json` - Discovery Endpoint

Returns the agent's manifest describing its capabilities and endpoints.

#### Request

```http
GET /.well-known/asap/manifest.json HTTP/1.1
Host: agent.example.com
```

#### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "urn:asap:agent:research-v1",
  "name": "Research Agent",
  "version": "1.0.0",
  "description": "Performs web research and summarization",
  "capabilities": {
    "asap_version": "0.1",
    "skills": [
      {
        "id": "web_research",
        "description": "Search and synthesize information from the web",
        "input_schema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          },
          "required": ["query"]
        },
        "output_schema": {
          "type": "object",
          "properties": {
            "summary": {"type": "string"},
            "sources": {"type": "array"}
          }
        }
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
  },
  "signature": null
}
```

---

## JSON-RPC 2.0 Specification

ASAP follows the [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification).

### Request Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jsonrpc` | string | Yes | Must be exactly `"2.0"` |
| `method` | string | Yes | Method name (`"asap.send"`) |
| `params` | object | Yes | Parameters containing the envelope |
| `id` | string\|int | Yes | Request identifier for correlation |

### Response Object (Success)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jsonrpc` | string | Yes | Must be exactly `"2.0"` |
| `result` | object | Yes | Response data with envelope |
| `id` | string\|int | Yes | Matches request id |

### Error Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jsonrpc` | string | Yes | Must be exactly `"2.0"` |
| `error` | object | Yes | Error details |
| `error.code` | int | Yes | Error code (negative integer) |
| `error.message` | string | Yes | Short description |
| `error.data` | any | No | Additional error information |
| `id` | string\|int\|null | Yes | Matches request id, or null |

---

## Error Code Mapping

### Standard JSON-RPC Errors

| Code | Name | Description | ASAP Context |
|------|------|-------------|--------------|
| `-32700` | Parse error | Invalid JSON | Malformed request body |
| `-32600` | Invalid request | Invalid JSON-RPC | Missing required fields |
| `-32601` | Method not found | Unknown method | Method is not `asap.send` |
| `-32602` | Invalid params | Invalid parameters | Missing envelope, invalid structure |
| `-32603` | Internal error | Server error | Unhandled exception |

### ASAP-Specific Error Mapping

| ASAP Error | JSON-RPC Code | When |
|------------|---------------|------|
| `MalformedEnvelopeError` | `-32602` | Invalid envelope structure |
| `InvalidTransitionError` | `-32602` | Invalid state transition |
| `TaskNotFoundError` | `-32602` | Task ID not found |
| `TaskAlreadyCompletedError` | `-32602` | Task in terminal state |
| `HandlerNotFoundError` | `-32601` | No handler for payload type |

### Error Response Examples

#### Parse Error (-32700)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32700,
    "message": "Parse error",
    "data": {"error": "Expecting property name enclosed in double quotes"}
  },
  "id": null
}
```

#### Invalid Request (-32600)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": {
      "validation_errors": [
        {"loc": ["method"], "msg": "Field required", "type": "missing"}
      ]
    }
  },
  "id": null
}
```

#### Method Not Found (-32601)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {"method": "asap.unknown"}
  },
  "id": "req-123"
}
```

#### Invalid Params (-32602)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "error": "Invalid envelope structure",
      "validation_errors": [
        {"loc": ["sender"], "msg": "Field required", "type": "missing"}
      ]
    }
  },
  "id": "req-123"
}
```

#### Internal Error (-32603)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "error": "Connection to database failed",
      "type": "DatabaseError"
    }
  },
  "id": "req-123"
}
```

---

## Using the Python Implementation

### Creating a Server

```python
from asap.models.entities import Manifest, Capability, Endpoint, Skill
from asap.transport.server import create_app
from asap.transport.handlers import HandlerRegistry

# Define agent manifest
manifest = Manifest(
    id="urn:asap:agent:my-agent",
    name="My Agent",
    version="1.0.0",
    description="Example ASAP agent",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo input back")],
        state_persistence=False
    ),
    endpoints=Endpoint(asap="http://localhost:8000/asap")
)

# Create custom handler
def my_task_handler(envelope, manifest):
    # Process TaskRequest and return TaskResponse envelope
    return create_response_envelope(envelope, result={"echo": envelope.payload})

# Register handlers
registry = HandlerRegistry()
registry.register("task.request", my_task_handler)

# Create FastAPI app
app = create_app(manifest, registry)

# Run with: uvicorn my_module:app --host 0.0.0.0 --port 8000
```

### Creating a Client

```python
from asap.transport.client import ASAPClient
from asap.models.envelope import Envelope

async def send_task_request():
    async with ASAPClient(base_url="http://localhost:8000") as client:
        # Create envelope
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload={
                "conversation_id": "conv_123",
                "skill_id": "echo",
                "input": {"message": "Hello, ASAP!"}
            }
        )
        
        # Send and receive response
        response = await client.send(envelope)
        print(f"Response: {response.payload}")
```

### Client Configuration

```python
from asap.transport.client import ASAPClient

# With custom timeout
async with ASAPClient(
    base_url="http://localhost:8000",
    timeout=30.0  # 30 seconds
) as client:
    response = await client.send(envelope)

# With retry configuration
async with ASAPClient(
    base_url="http://localhost:8000",
    max_retries=3,
    retry_delay=1.0  # 1 second between retries
) as client:
    response = await client.send(envelope)
```

---

## Manifest Schema Reference

### Manifest Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Agent URN (`urn:asap:agent:{name}`) |
| `name` | string | Yes | Human-readable name |
| `version` | string | Yes | Semantic version (e.g., `"1.0.0"`) |
| `description` | string | Yes | Agent description |
| `capabilities` | Capability | Yes | Agent capabilities |
| `endpoints` | Endpoint | Yes | Communication endpoints |
| `auth` | AuthScheme | No | Authentication configuration |
| `signature` | string | No | Manifest signature for verification |

### Capability Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asap_version` | string | Yes | ASAP protocol version |
| `skills` | Skill[] | Yes | Available skills |
| `state_persistence` | boolean | Yes | Supports snapshots |
| `streaming` | boolean | Yes | Supports streaming |
| `mcp_tools` | string[] | Yes | Available MCP tools |

### Skill Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique skill identifier |
| `description` | string | Yes | Skill description |
| `input_schema` | object | No | JSON Schema for input |
| `output_schema` | object | No | JSON Schema for output |

### Endpoint Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asap` | string | Yes | HTTP endpoint for messages |
| `events` | string | No | WebSocket for streaming |

### AuthScheme Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemes` | string[] | Yes | Supported auth methods |
| `oauth2` | object | No | OAuth2 configuration |

---

## Testing with cURL

### Discover Agent

```bash
curl -s http://localhost:8000/.well-known/asap/manifest.json | jq .
```

### Send Task Request

```bash
curl -X POST http://localhost:8000/asap \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "asap.send",
    "params": {
      "envelope": {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:test-client",
        "recipient": "urn:asap:agent:default-server",
        "payload_type": "task.request",
        "payload": {
          "conversation_id": "conv_test",
          "skill_id": "echo",
          "input": {"message": "Hello!"}
        }
      }
    },
    "id": "test-1"
  }' | jq .
```

### Check Server Health

```bash
# Start server
uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000

# Test manifest endpoint
curl -I http://localhost:8000/.well-known/asap/manifest.json
# Expected: HTTP/1.1 200 OK
```

---

## Related Documentation

- [Security](security.md) - Authentication and TLS
- [Error Handling](error-handling.md) - Error taxonomy
- [Observability](observability.md) - Logging and tracing
- [API Reference](api-reference.md) - Complete API documentation
