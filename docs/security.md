# Security Guide

> Comprehensive security guidance for implementing and operating ASAP protocol agents.

---

## Overview

The ASAP protocol is designed with security as a foundational concern. This guide covers:

- **Authentication**: How agents verify identity
- **Request Signing**: Cryptographic integrity for messages
- **TLS/HTTPS**: Transport layer security requirements
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

Implement rate limiting to prevent DoS attacks:

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

# Simple in-memory rate limiter (use Redis for production)
request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 100  # requests per minute
WINDOW = 60  # seconds

async def rate_limit(request: Request):
    """Rate limit requests by sender."""
    sender = request.headers.get("X-ASAP-Sender", request.client.host)
    now = time.time()
    
    # Clean old requests
    request_counts[sender] = [
        t for t in request_counts[sender] 
        if now - t < WINDOW
    ]
    
    if len(request_counts[sender]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    request_counts[sender].append(now)
```

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
- [ ] Rate limiting enabled
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
