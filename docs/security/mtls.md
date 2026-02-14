# mTLS (Mutual TLS) Setup

Optional mutual TLS for ASAP transport (SD-6). mTLS provides certificate-based authentication for both client and server in enterprise deployments. **mTLS is optional and never required.**

## Overview

- **Server**: Presents its certificate to clients; optionally requires client certificates.
- **Client**: Presents its certificate to the server; verifies the server's certificate.
- **Use cases**: Enterprise networks, zero-trust architectures, regulated industries.

## Certificate Generation

### Self-Signed CA and Certificates (Development/Testing)

```bash
# Create CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=ASAP-Test-CA"

# Server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256

# Client certificate
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=asap-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 365 -sha256
```

### Production

Use your organization's PKI or a public CA. Ensure:
- Server cert has correct SAN (Subject Alternative Name) for your hostname.
- Client certs are issued by a CA the server trusts.
- Keys are stored with restrictive permissions (e.g. `chmod 600`).

## Server Configuration

### 1. Create mTLS Config

```python
from asap.transport.mtls import MTLSConfig
from asap.transport.server import create_app
from asap.models.entities import Manifest, Capability, Endpoint, Skill

mtls_config = MTLSConfig(
    cert_file="server.crt",
    key_file="server.key",
    ca_certs="ca.crt",  # CA to verify client certs; omit to skip client verification
)

manifest = Manifest(
    id="urn:asap:agent:my-agent",
    name="My Agent",
    version="1.0.0",
    description="mTLS-protected agent",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="https://localhost:8443/asap"),
)
app = create_app(manifest, mtls_config=mtls_config)
```

### 2. Run Uvicorn with SSL

```python
import uvicorn
from asap.transport.mtls import mtls_config_to_uvicorn_kwargs

# Get uvicorn SSL kwargs from mtls_config
ssl_kwargs = mtls_config_to_uvicorn_kwargs(mtls_config)

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8443,
    **ssl_kwargs,
)
```

Or via CLI:

```bash
uvicorn asap.transport.server:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile server.key \
  --ssl-certfile server.crt \
  --ssl-ca-certs ca.crt \
  --ssl-cert-reqs 2
```

(`--ssl-cert-reqs 2` = `CERT_REQUIRED`)

## Client Configuration

```python
from asap.transport.client import ASAPClient
from asap.transport.mtls import MTLSConfig

mtls_config = MTLSConfig(
    cert_file="client.crt",
    key_file="client.key",
    ca_certs="ca.crt",  # CA to verify server; omit for system default
)

async with ASAPClient(
    "https://localhost:8443",
    mtls_config=mtls_config,
) as client:
    response = await client.send(envelope)
```

## WebSocket with mTLS

Both HTTP and WebSocket transports support mTLS. When `mtls_config` is provided to `ASAPClient`, it applies to:
- HTTP requests (POST /asap)
- WebSocket connections (wss://)
- Manifest fetches

## Backward Compatibility

- Servers without `mtls_config` run as before (plain HTTP or TLS without client certs).
- Clients without `mtls_config` connect without presenting a client certificate.
- mTLS is opt-in; existing deployments are unaffected.

## Security Notes

- Store private keys with `chmod 600`; never commit them.
- Use environment variables or secrets managers for paths in production.
- Rotate certificates before expiry; monitor expiration dates.
- For `ca_certs`, use a CA that only signs known clients/servers.
