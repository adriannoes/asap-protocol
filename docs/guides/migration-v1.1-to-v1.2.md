# Migration Guide: v1.1 → v1.2

Upgrade steps for moving from ASAP Protocol v1.1.0 to v1.2.0.

## Overview

v1.2.0 adds **Verified Identity** features while remaining backward compatible with v1.1.0:

- Ed25519 signed manifests
- Trust levels (self-signed, verified, enterprise)
- Optional mTLS for transport
- Compliance harness (`asap-compliance` package)

**No breaking changes.** Existing agents and clients continue to work without modification.

## Upgrade Steps

### 1. Update dependencies

```bash
uv add "asap-protocol>=1.2.0"
# or
pip install --upgrade asap-protocol
```

### 2. (Optional) Add signed manifests

If you want verifiable agent identity:

1. Generate a keypair: `asap keys generate -o agent-key.pem`
2. Sign your manifest: `asap manifest sign -k agent-key.pem manifest.json -o signed.json`
3. Serve the signed manifest from `GET /.well-known/asap/manifest.json`

The server's `create_app(manifest)` accepts a plain `Manifest`. To serve a signed manifest, you need to return the signed JSON from the well-known endpoint (e.g. by using a custom route or extending the server).

### 3. (Optional) Enable client-side verification

If you want clients to verify signed manifests:

```python
from asap.transport.client import ASAPClient

trusted_keys = {
    "https://agent.example.com/.well-known/asap/manifest.json": "base64-public-key",
}
async with ASAPClient(
    "https://agent.example.com",
    verify_signatures=True,
    trusted_manifest_keys=trusted_keys,
) as client:
    manifest = await client.get_manifest()
```

### 4. (Optional) Add mTLS

For enterprise deployments with mutual TLS:

```python
from asap.transport.mtls import MTLSConfig, create_ssl_context
from asap.transport.server import create_app

mtls_config = MTLSConfig(
    cert_file="/path/to/cert.pem",
    key_file="/path/to/key.pem",
    ca_certs="/path/to/ca.pem",  # Optional
)
app = create_app(manifest, mtls_config=mtls_config)
```

### 5. (Optional) Run compliance tests

Validate your agent with the compliance harness:

```bash
uv add asap-compliance
pytest --asap-agent-url https://your-agent.example.com -m asap_compliance
```

## What Stays the Same

- All v1.1 APIs (OAuth2, WebSocket, Discovery, State Storage, Webhooks)
- Envelope and payload schemas
- JSON-RPC binding
- Lite Registry and well-known discovery
- Plain (unsigned) manifests still accepted everywhere

## Deferred Items (not in v1.2)

- **Registry API**: Centralized agent registry backend (v2.1)
- **DeepEval integration**: Intelligence layer for compliance (v2.2+)

## See Also

- [Identity Signing](identity-signing.md) — How to sign manifests
- [Compliance Testing](compliance-testing.md) — Validate agents
- [mTLS](../security/mtls.md) — Mutual TLS configuration
