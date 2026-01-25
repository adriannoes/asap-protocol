# Security Guide

> Comprehensive security guidance for implementing and operating ASAP protocol agents.

---

## Overview

The ASAP protocol is designed with security as a foundational concern. This guide covers:

- **Authentication**: How agents verify identity
- **Request Signing**: Cryptographic integrity for messages
- **TLS/HTTPS**: Transport layer security requirements
- **Rate Limiting**: Per-sender request rate controls
- **Request Size Limits**: Protection against oversized payloads
- **Threat Model**: Common attack vectors and mitigations

---

## Authentication

ASAP supports multiple authentication schemes configured via the agent's manifest. The `AuthScheme` model defines the supported methods.

### Supported Authentication Schemes

| Scheme | Description | Use Case |
|--------|-------------|----------|
| `bearer` | Bearer token authentication | API keys, JWT tokens |
| `oauth2` | OAuth 2.0 with authorization code or client credentials | Enterprise integrations |
| `mtls` | Mutual TLS with client certificates | High-security environments |
| `none` | No authentication (development only) | Local testing |

### Manifest Configuration

Authentication is declared in the agent manifest's `auth` field:

```python
from asap.models.entities import AuthScheme, Manifest

auth = AuthScheme(
    schemes=["bearer", "oauth2"],
    oauth2={
        "authorization_url": "https://auth.example.com/authorize",
        "token_url": "https://auth.example.com/token",
        "scopes": ["asap:execute", "asap:read"]
    }
)

manifest = Manifest(
    id="urn:asap:agent:secure-agent",
    name="Secure Agent",
    version="1.0.0",
    description="Agent with authentication",
    capabilities=capability,
    endpoints=endpoint,
    auth=auth
)
```

### Required Headers

When making requests to authenticated agents, include the appropriate headers:

#### Bearer Token

```http
POST /asap HTTP/1.1
Host: agent.example.com
Content-Type: application/json
Authorization: Bearer <token>
```

#### OAuth 2.0

```http
POST /asap HTTP/1.1
Host: agent.example.com
Content-Type: application/json
Authorization: Bearer <access_token>
```

### Implementing Authentication

The ASAP protocol provides built-in authentication middleware for securing agent communication. Authentication is optional and configured via the manifest.

#### Quick Start with Bearer Tokens

```python
from asap.models.entities import Manifest, AuthScheme, Capability, Endpoint, Skill
from asap.transport.server import create_app

# 1. Configure authentication in manifest
manifest = Manifest(
    id="urn:asap:agent:secure-agent",
    name="Secure Agent",
    version="1.0.0",
    description="Agent with authentication",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="secure-task", description="Secure task processing")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="https://api.example.com/asap"),
    auth=AuthScheme(schemes=["bearer"]),  # Enable Bearer token authentication
)

# 2. Implement token validation function
def validate_bearer_token(token: str) -> str | None:
    """Validate Bearer token and return agent ID if valid.
    
    Args:
        token: The Bearer token from Authorization header
        
    Returns:
        Agent ID (URN) if token is valid, None otherwise
    """
    # Example: Validate against database
    user = database.verify_token(token)
    if user and user.is_active:
        return user.agent_id  # e.g., "urn:asap:agent:client-123"
    
    return None

# 3. Create app with authentication
app = create_app(manifest, token_validator=validate_bearer_token)

# Run with uvicorn:
# uvicorn myapp:app --host 0.0.0.0 --port 8000
```

#### How It Works

1. **Manifest Declaration**: Set `auth=AuthScheme(schemes=["bearer"])` in manifest
2. **Token Validation**: Provide a `token_validator` function to `create_app()`
3. **Automatic Verification**: Middleware validates every request:
   - Checks for `Authorization: Bearer <token>` header
   - Calls your `token_validator` with the token
   - Returns HTTP 401 if token is invalid or missing
   - Verifies `envelope.sender` matches authenticated identity
   - Returns HTTP 403 if sender is spoofed

#### Custom Token Validation

Integrate with any authentication system (JWT, OAuth2, database, etc.):

```python
import jwt
from datetime import datetime

def validate_jwt_token(token: str) -> str | None:
    """Validate JWT token and extract agent ID."""
    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            key=PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_exp": True}
        )
        
        # Verify custom claims
        if payload.get("iss") != "https://auth.example.com":
            return None
        
        # Extract agent ID
        return payload.get("sub")  # e.g., "urn:asap:agent:user-456"
        
    except jwt.InvalidTokenError:
        return None

app = create_app(manifest, token_validator=validate_jwt_token)
```

#### OAuth2 Integration

For OAuth2 workflows, implement token introspection:

```python
import httpx

async def validate_oauth2_token(token: str) -> str | None:
    """Validate OAuth2 token via introspection endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://auth.example.com/oauth/introspect",
            data={"token": token},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not data.get("active"):
            return None
        
        # Map OAuth2 subject to agent URN
        return f"urn:asap:agent:{data['sub']}"

app = create_app(manifest, token_validator=validate_oauth2_token)
```

#### Client-Side Authentication

When calling authenticated endpoints, include the Bearer token:

```python
from asap.transport.client import ASAPClient
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest

async with ASAPClient("https://api.example.com") as client:
    envelope = Envelope(
        sender="urn:asap:agent:client-123",
        recipient="urn:asap:agent:secure-agent",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-1",
            skill_id="secure-task",
            input={"data": "sensitive-info"},
        ),
    )
    
    # Add authentication header to httpx client
    client._client.headers["Authorization"] = f"Bearer {my_token}"
    
    response = await client.send(envelope)
```

#### Security Best Practices

1. **Always use HTTPS** in production (client enforces this by default)
2. **Rotate tokens regularly** to limit exposure window
3. **Use short-lived tokens** (15-60 minutes) with refresh mechanism
4. **Validate sender identity** (middleware does this automatically)
5. **Log authentication failures** for security monitoring
6. **Rate limit authentication attempts** to prevent brute force

#### Disabling Authentication (Development Only)

```python
# Manifest without auth - authentication is skipped
manifest = Manifest(
    # ... other fields ...
    auth=None,  # No authentication required
)

app = create_app(manifest)  # No token_validator needed
```

⚠️ **Warning**: Only disable authentication for local development. Production deployments **must** use authentication.

---

## Request Signing

Request signing provides cryptographic proof of message origin and integrity, preventing tampering and ensuring non-repudiation.

### Signing Workflow

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   Sender    │     │    Message      │     │  Recipient  │
└─────────────┘     └─────────────────┘     └─────────────┘
       │                    │                      │
       │  1. Create envelope                       │
       ├──────────►│                               │
       │                    │                      │
       │  2. Sign envelope with private key        │
       ├──────────►│                               │
       │                    │                      │
       │  3. Add signature to extensions           │
       ├──────────►│                               │
       │                    │                      │
       │           4. Send signed envelope         │
       ├───────────────────────────────────────────►
       │                    │                      │
       │           5. Verify signature with public key
       │                    │                      ◄─
       │           6. Process if valid             │
       │                    │                      ◄─
```

### Signature Format

Signatures are included in the envelope's `extensions` field:

```python
from datetime import datetime, timezone
from asap.models.envelope import Envelope

envelope = Envelope(
    asap_version="0.1",
    sender="urn:asap:agent:sender",
    recipient="urn:asap:agent:recipient",
    payload_type="task.request",
    payload={"skill_id": "research", "input": {}},
    extensions={
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "key-2024-01",
            "value": "<base64-encoded-signature>",
            "signed_at": datetime.now(timezone.utc).isoformat()
        }
    }
)
```

### Signing Implementation

```python
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def sign_envelope(envelope: Envelope, private_key: Ed25519PrivateKey) -> Envelope:
    """Sign an envelope and add signature to extensions."""
    # Canonical JSON representation (excluding signature field)
    canonical = envelope.model_dump(mode="json", exclude={"extensions"})
    message = json.dumps(canonical, sort_keys=True).encode()
    
    # Sign the message
    signature = private_key.sign(message)
    signature_b64 = base64.b64encode(signature).decode()
    
    # Add signature to extensions
    extensions = envelope.extensions or {}
    extensions["signature"] = {
        "algorithm": "Ed25519",
        "key_id": "key-2024-01",
        "value": signature_b64,
        "signed_at": datetime.now(timezone.utc).isoformat()
    }
    
    return envelope.model_copy(update={"extensions": extensions})
```

### Verification Steps

Recipients verify signatures before processing:

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def verify_envelope(envelope: Envelope, public_key: Ed25519PublicKey) -> bool:
    """Verify envelope signature."""
    if not envelope.extensions or "signature" not in envelope.extensions:
        return False
    
    sig_data = envelope.extensions["signature"]
    signature = base64.b64decode(sig_data["value"])
    
    # Reconstruct canonical message
    canonical = envelope.model_dump(mode="json", exclude={"extensions"})
    message = json.dumps(canonical, sort_keys=True).encode()
    
    try:
        public_key.verify(signature, message)
        return True
    except InvalidSignature:
        return False
```

### Key Distribution

Public keys for signature verification should be distributed via:

1. **Manifest**: Include public key in the manifest's `signature` field
2. **Well-Known Endpoint**: `/.well-known/asap/keys.json`
3. **Key Server**: Centralized key management system

---

## TLS/HTTPS Requirements

All production ASAP deployments must use TLS 1.2 or higher.

### Minimum Requirements

| Requirement | Value |
|-------------|-------|
| TLS Version | 1.2+ (1.3 recommended) |
| Certificate | Valid, not self-signed |
| Cipher Suites | AEAD ciphers (AES-GCM, ChaCha20-Poly1305) |
| HSTS | Enabled with max-age ≥ 31536000 |

### Certificate Validation

The ASAP client validates server certificates by default:

```python
from asap.transport.client import ASAPClient

# Production: Certificate validation enabled (default)
async with ASAPClient(base_url="https://agent.example.com") as client:
    response = await client.send(envelope)

# Development only: Disable certificate validation (NOT FOR PRODUCTION)
async with ASAPClient(
    base_url="https://localhost:8443",
    verify_ssl=False  # DANGER: Only for local development
) as client:
    response = await client.send(envelope)
```

### Mutual TLS (mTLS)

For high-security deployments, configure mutual TLS:

```python
import httpx

# Client certificate configuration
client = httpx.AsyncClient(
    cert=("/path/to/client.crt", "/path/to/client.key"),
    verify="/path/to/ca-bundle.crt"
)
```

---

## Rate Limiting

Rate limiting protects ASAP agents from denial-of-service (DoS) attacks by limiting the number of requests per sender within a time window. The ASAP protocol server includes built-in rate limiting using per-sender tracking.

### Default Configuration

The default rate limit is **100 requests per minute** per sender. This can be configured via:

- **Environment variable**: `ASAP_RATE_LIMIT` (e.g., `"200/minute"`, `"10/second"`)
- **Application parameter**: `rate_limit` parameter in `create_app()`

### Configuration

```python
from asap.transport.server import create_app
from asap.models.entities import Manifest

# Configure via environment variable
# export ASAP_RATE_LIMIT="200/minute"

# Or configure programmatically
app = create_app(
    manifest,
    rate_limit="200/minute"  # 200 requests per minute per sender
)
```

### Rate Limit Format

The rate limit string follows the format: `<number>/<unit>` where unit can be:
- `second` or `sec`
- `minute` or `min`
- `hour` or `hr`
- `day`

Examples:
- `"100/minute"` - 100 requests per minute
- `"10/second"` - 10 requests per second
- `"1000/hour"` - 1000 requests per hour

### How It Works

1. **Sender Identification**: The rate limiter extracts the sender from the ASAP envelope (`envelope.sender`). If the envelope is not yet parsed, it falls back to the client IP address.

2. **Per-Sender Tracking**: Each sender (agent URN or IP) has an independent rate limit counter.

3. **Window-Based Limiting**: Uses a sliding window to track requests within the time period.

4. **Automatic Rejection**: When the limit is exceeded, the server returns HTTP 429 (Too Many Requests) with a JSON-RPC error response.

### Response Format

When rate limit is exceeded, the server returns:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32000,
    "message": "Rate limit exceeded",
    "data": {
      "error": "Rate limit exceeded: 100 per 1 minute",
      "retry_after": 45
    }
  }
}
```

The response includes:
- **HTTP Status**: 429 (Too Many Requests)
- **Retry-After Header**: Number of seconds until the rate limit resets
- **JSON-RPC Error**: Standard error format with rate limit details

### Production Recommendations

1. **Adjust Limits Based on Workload**: 
   - High-throughput agents: `200-500/minute`
   - Interactive agents: `50-100/minute`
   - Resource-intensive agents: `10-50/minute`

2. **Use Distributed Storage**: For multi-instance deployments, configure slowapi to use Redis:
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   import redis
   
   redis_client = redis.Redis(host='localhost', port=6379, db=0)
   limiter = Limiter(
       key_func=_get_sender_from_envelope,
       storage_uri="redis://localhost:6379"
   )
   ```

3. **Monitor Rate Limit Hits**: Track `asap_rate_limit_exceeded_total` metric to identify potential attacks or legitimate traffic spikes.

4. **Implement Graduated Responses**: Consider implementing different limits for different sender types (trusted vs. untrusted).

### Example: Custom Rate Limit Configuration

```python
import os
from asap.transport.server import create_app

# Read from environment or use default
rate_limit = os.getenv("ASAP_RATE_LIMIT", "100/minute")

app = create_app(
    manifest,
    rate_limit=rate_limit
)
```

### Testing Rate Limits

To test rate limiting behavior:

```python
import asyncio
import httpx

async def test_rate_limit():
    """Test that rate limiting rejects excessive requests."""
    async with httpx.AsyncClient() as client:
        # Send 101 requests rapidly
        for i in range(101):
            response = await client.post(
                "http://localhost:8000/asap",
                json={
                    "jsonrpc": "2.0",
                    "method": "asap.send",
                    "params": {
                        "envelope": {
                            "asap_version": "0.1",
                            "sender": "urn:asap:agent:test-client",
                            "recipient": "urn:asap:agent:server",
                            "payload_type": "task.request",
                            "payload": {"test": "data"}
                        }
                    },
                    "id": f"test-{i}"
                }
            )
            
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
                assert "Rate limit exceeded" in response.json()["error"]["message"]

asyncio.run(test_rate_limit())
```

---

## Request Size Limits

Request size limits protect agents from memory exhaustion attacks by rejecting oversized payloads before they are fully processed. The ASAP protocol server enforces a maximum request size to prevent DoS attacks.

### Default Configuration

The default maximum request size is **10MB (10,485,760 bytes)**. This can be configured via:

- **Environment variable**: `ASAP_MAX_REQUEST_SIZE` (in bytes, e.g., `"5242880"` for 5MB)
- **Application parameter**: `max_request_size` parameter in `create_app()`

### Configuration

```python
from asap.transport.server import create_app
from asap.models.constants import MAX_REQUEST_SIZE

# Use default (10MB)
app = create_app(manifest)

# Configure via environment variable
# export ASAP_MAX_REQUEST_SIZE="5242880"  # 5MB

# Or configure programmatically
app = create_app(
    manifest,
    max_request_size=5 * 1024 * 1024  # 5MB in bytes
)
```

### How It Works

The server validates request size in two stages:

1. **Content-Length Header Check**: If the `Content-Length` header is present, the server checks it before reading the request body. This allows early rejection without consuming bandwidth.

2. **Actual Body Size Check**: After reading the request body, the server validates the actual size. This catches cases where the `Content-Length` header is missing or incorrect.

### Error Response

When a request exceeds the size limit, the server returns:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32000,
    "message": "Request too large",
    "data": {
      "error": "Request size (15728640 bytes) exceeds maximum (10485760 bytes)"
    }
  }
}
```

The response includes:
- **HTTP Status**: 413 (Payload Too Large)
- **JSON-RPC Error**: Standard error format with size details

### Rationale

The 10MB default limit balances:
- **Functionality**: Allows large payloads for legitimate use cases (file uploads, batch operations)
- **Security**: Prevents memory exhaustion from malicious oversized requests
- **Performance**: Enables early rejection before full request processing

### Production Recommendations

1. **Adjust Based on Use Case**:
   - File processing agents: `50-100MB`
   - API gateway agents: `1-5MB`
   - Real-time agents: `1MB or less`

2. **Configure at Multiple Layers**:
   - **ASGI Server**: Set `--limit-max-requests` in uvicorn/gunicorn
   - **Reverse Proxy**: Configure nginx/traefik with `client_max_body_size`
   - **Application**: Use `max_request_size` parameter

3. **Monitor Size Violations**: Track rejected requests to identify potential attacks or legitimate needs for larger limits.

### Example: Multi-Layer Size Protection

```python
# Application level (ASAP server)
app = create_app(
    manifest,
    max_request_size=10 * 1024 * 1024  # 10MB
)

# Run with uvicorn size limit
# uvicorn app:app --limit-max-requests 10485760  # 10MB
```

```nginx
# nginx configuration
http {
    client_max_body_size 10M;
    
    server {
        location /asap {
            proxy_pass http://localhost:8000;
        }
    }
}
```

### Testing Size Limits

To test size limit enforcement:

```python
import httpx

def test_size_limit():
    """Test that oversized requests are rejected."""
    # Create a payload that exceeds 10MB
    large_payload = {"data": "x" * (11 * 1024 * 1024)}  # 11MB
    
    envelope = {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:client",
        "recipient": "urn:asap:agent:server",
        "payload_type": "task.request",
        "payload": large_payload
    }
    
    rpc_request = {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": envelope},
        "id": "test-1"
    }
    
    # Serialize to JSON
    import json
    request_json = json.dumps(rpc_request)
    request_bytes = request_json.encode("utf-8")
    
    # Send with Content-Length header
    response = httpx.post(
        "http://localhost:8000/asap",
        content=request_bytes,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(request_bytes))
        }
    )
    
    assert response.status_code == 413
    assert "exceeds maximum" in response.json()["error"]["data"]["error"]
```

---

## Threat Model

### Attack Vectors and Mitigations

| Threat | Attack Vector | Mitigation |
|--------|---------------|------------|
| **Eavesdropping** | Network interception | TLS encryption |
| **Tampering** | Message modification | Request signing |
| **Spoofing** | Identity impersonation | Authentication + signing |
| **Replay** | Message replay attacks | Timestamps + nonces |
| **Injection** | Malicious payload content | Input validation |
| **DoS** | Resource exhaustion | Rate limiting |
| **Man-in-the-Middle** | TLS interception | Certificate pinning |

### Replay Attack Prevention

ASAP uses timestamps and optional nonces to prevent replay attacks:

```python
from datetime import datetime, timezone, timedelta

def is_request_valid(envelope: Envelope, max_age_seconds: int = 300) -> bool:
    """Check if request is within acceptable time window."""
    now = datetime.now(timezone.utc)
    request_time = envelope.timestamp
    
    # Reject requests older than max_age
    if now - request_time > timedelta(seconds=max_age_seconds):
        return False
    
    # Reject requests from the future (with small tolerance)
    if request_time - now > timedelta(seconds=30):
        return False
    
    return True
```

### Rate Limiting

The ASAP protocol server includes built-in rate limiting (see [Rate Limiting](#rate-limiting) section above). For custom implementations, you can integrate with external rate limiting services:

```python
# Example: Custom rate limiting middleware
from fastapi import Request, HTTPException
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def custom_rate_limit(request: Request):
    """Custom rate limiting using Redis."""
    sender = _get_sender_from_envelope(request)
    key = f"rate_limit:{sender}"
    
    # Use Redis INCR with expiration
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)  # 60 second window
    
    if count > 100:  # 100 requests per minute
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

For most use cases, the built-in rate limiting is recommended (see [Rate Limiting](#rate-limiting) section).

### Input Validation

Always validate payload content before processing:

```python
from pydantic import ValidationError
from asap.models.payloads import TaskRequest

def validate_payload(envelope: Envelope) -> TaskRequest:
    """Validate and parse TaskRequest payload."""
    try:
        return TaskRequest(**envelope.payload)
    except ValidationError as e:
        raise MalformedEnvelopeError(
            reason="Invalid TaskRequest payload",
            details={"validation_errors": e.errors()}
        )
```

---

## Security Checklist

### Production Deployment

- [ ] TLS 1.2+ enabled on all endpoints
- [ ] Valid SSL certificates (not self-signed)
- [ ] HSTS headers configured
- [ ] Authentication required for all endpoints
- [ ] Rate limiting enabled and configured appropriately
- [ ] Request size limits configured (default: 10MB)
- [ ] Request signing implemented
- [ ] Audit logging enabled
- [ ] Secrets stored in environment variables
- [ ] Input validation on all payloads
- [ ] Certificate rotation process defined

### Development Environment

- [ ] Use `localhost` or private networks only
- [ ] Never use production credentials
- [ ] Clear separation from production data
- [ ] Self-signed certificates marked as development-only

---

## Related Documentation

- [Error Handling](error-handling.md) - ASAP error taxonomy
- [Transport](transport.md) - HTTP/JSON-RPC binding details
- [Observability](observability.md) - Logging and tracing
