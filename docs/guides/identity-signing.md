# Identity Signing (v1.2)

Ed25519 signed manifests provide verifiable agent identity. Agents can sign their manifests so that clients can verify authenticity and detect tampering.

## Overview

- **Algorithm**: Ed25519 (64-byte signatures)
- **Canonicalization**: JCS (RFC 8785) for deterministic JSON before signing
- **Trust levels**: Self-signed, Verified (simulated), Enterprise

## Quick Start

### 1. Generate a keypair

```bash
asap keys generate -o agent-key.pem
```

The key file is created with mode `0600` (owner read/write only).

### 2. Sign a manifest

```bash
asap manifest sign -k agent-key.pem manifest.json -o signed-manifest.json
```

Or output to stdout:

```bash
asap manifest sign -k agent-key.pem manifest.json
```

### 3. Verify a signed manifest

```bash
asap manifest verify signed-manifest.json
```

If the manifest includes `public_key`, verification uses it. Otherwise, pass `--public-key`:

```bash
asap manifest verify signed-manifest.json --public-key agent-key.pem
```

### 4. Show manifest info (trust level)

```bash
asap manifest info signed-manifest.json
```

Output includes Manifest ID, name, trust level, and ASAP version.

## Programmatic Usage

```python
from asap.crypto.keys import generate_keypair, load_private_key_from_file_sync
from asap.crypto.signing import sign_manifest, verify_manifest
from asap.models.entities import Manifest, Capability, Endpoint, Skill

manifest = Manifest(
    id="urn:asap:agent:my-agent",
    name="My Agent",
    version="1.0.0",
    description="Signed agent",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="https://api.example.com/asap"),
)

# Sign
private_key, _ = generate_keypair()
signed = sign_manifest(manifest, private_key)

# Verify
verify_manifest(signed)  # Uses public_key from signed manifest
```

## Client-Side Verification

`ASAPClient` can optionally verify signed manifests when fetching:

```python
from asap.transport.client import ASAPClient

# With trusted public key for a specific URL
trusted = {
    "https://api.example.com/.well-known/asap/manifest.json": "base64-public-key",
}
async with ASAPClient(
    "https://api.example.com",
    verify_signatures=True,
    trusted_manifest_keys=trusted,
) as client:
    manifest = await client.get_manifest()
```

If the manifest is signed and includes `public_key`, the client can verify without pre-configuring trusted keys (trust level is still self-signed unless the key is in an allowlist).

## Trust Levels

| Level | Description |
|-------|-------------|
| **self-signed** | Agent signs with its own key; `public_key` in manifest |
| **verified** | Simulated in v1.2; actual verification service in v2.0 |
| **enterprise** | CA-signed; requires `sign_with_ca` and enterprise PKI |

## CLI Reference

| Command | Description |
|---------|-------------|
| `asap keys generate -o FILE` | Generate Ed25519 keypair, write private key to FILE |
| `asap manifest sign -k KEY MANIFEST [--out FILE]` | Sign manifest JSON; output to file or stdout |
| `asap manifest verify SIGNED [--public-key KEY]` | Verify Ed25519 signature |
| `asap manifest info SIGNED` | Show manifest ID, name, trust level, ASAP version |

## See Also

- [mTLS](../security/mtls.md) — Optional mutual TLS for transport security
- [v1.1 Security Model](../security/v1.1-security-model.md) — OAuth2 trust limitations
- [Compliance Testing](compliance-testing.md) — Validate agents with asap-compliance
