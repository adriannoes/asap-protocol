# ASAP Protocol: Security Decisions

> **Category**: Security & Trust
> **Focus**: Auth, PKI, Threats

---

## Question 8: Is MVP Security Sufficient?

### The Question
Section 10.1 defines MVP security (TLS, bearer tokens, scopes). Is this adequate for initial deployments?

### Analysis

**Threat Assessment for MVP**:

| Threat | MVP Mitigation | Gap |
|--------|----------------|-----|
| Eavesdropping | TLS 1.3 | ✅ Covered |
| Replay attacks | Idempotency keys | ⚠️ Keys expire, not cryptographic |
| Spoofing | Bearer tokens | ⚠️ Token theft risk |
| Man-in-middle | TLS | ✅ Covered |
| Privilege escalation | Scopes | ⚠️ Scope enforcement in spec, not protocol |

**Industry Baseline** (2025):
- mTLS becoming standard for service-to-service
- Signed JWTs preferred over opaque tokens
- Zero-trust architecture expected for enterprise

### Expert Assessment

**MVP security is adequate IF**:
- Deployments are within trust boundaries
- Network security complements protocol security
- Token management follows best practices

**Upgrade urgency**:
- Signed messages: High (v0.2)
- mTLS: Medium (v0.3)
- Zero-trust: Low (v1.1)

### Recommendation: **KEEP with enhancement**

Add HMAC-signed request bodies as optional MVP feature.

### Spec Amendment

> [!NOTE]
> Added to Section 10.1: Optional request signing via `X-ASAP-Signature` header using HMAC-SHA256. Enables integrity verification without full PKI. Recommended for production deployments.

---

## Question 17: Trust Model and Identity Binding in v1.1

### The Question
OAuth2 (v1.1) proves "I have valid credentials from an IdP", but NOT "I am the agent I claim to be". Without signed manifests (v1.2), how do we prevent agent impersonation? And how do we bind JWT identity to ASAP agent identity given that IdP subject IDs (`google-oauth2|12345`) don't match agent IDs (`urn:asap:agent:bot`)?

### Analysis

**The trust gap**: v1.1 OAuth2 provides authentication and authorization (scopes), but not identity verification. This is the SAME trust model as every web API today — OAuth2 is equivalent to API keys with scopes. The real identity verification comes in v1.2 with Ed25519 signed manifests.

**The identity mapping problem**: IdP-generated `sub` claims (e.g., `google-oauth2|12345`, `auth0|abc123`) will never match ASAP `agent_id` values (e.g., `urn:asap:agent:research-v1`). A strict `sub == agent_id` binding is impossible in practice.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| Accept and document explicitly | ✅ Selected (part 1) | Honest, sets expectations, no false security |
| **Custom Claims binding** | ✅ Selected (part 2) | Flexible, portable, standard JWT practice |
| Strict sub == agent_id | Rejected | Impossible with standard IdPs |
| Accelerate Ed25519 to v1.1 | Rejected | Scope creep, v1.1 already has 5 sprints |

### Expert Assessment

**Custom Claims** is the most flexible solution: agents configure their IdP to include a custom claim (default: `https://github.com/adriannoes/asap-protocol/agent_id`) in the JWT. The ASAP server validates this claim matches the requesting agent's manifest `id`. Future: `https://asap-protocol.com/agent_id` will be the canonical namespace when the domain is available. For environments where custom claims aren't possible, a configurable allowlist mapping (`ASAP_AUTH_SUBJECT_MAP`) provides a fallback.

### Decision

> [!IMPORTANT]
> **ADR-17**: v1.1 Trust Model uses **Custom Claims binding** for identity mapping, with explicit documentation of security limitations.
>
> **Identity Binding** (two approaches, both supported):
> 1. **Custom Claims** (recommended): Agent configures IdP to include `https://github.com/adriannoes/asap-protocol/agent_id: urn:asap:agent:bot` in JWT. Server validates claim matches manifest `id`.
> 2. **Allowlist fallback**: `ASAP_AUTH_SUBJECT_MAP = {"urn:asap:agent:bot": "auth0|abc123"}` for environments without custom claims support.
>
> **Security Model documentation**:
> - v1.1 provides authentication (valid credentials) and authorization (scopes), but NOT identity verification
> - For agent identity verification, use v1.2 signed manifests (Ed25519)
> - This mirrors industry practice: OAuth2 for auth, PKI for identity, incrementally layered
>
> **Rationale**: Custom Claims are portable (work across IdPs), standards-based (RFC 7519 allows private claims), and more flexible than hardcoded config. The allowlist fallback covers edge cases. Explicit security documentation prevents false expectations.
>
> **Impact**: Custom Claims validation added as sub-task in Sprint S1. Security Model documentation added to Sprint S4 release materials.
>
> **Date**: 2026-02-07

---

## Question 20: Security Hardening Strategy for Ed25519 PKI

### The Question
As we implement the Ed25519 PKI in v1.2.0 (Sprint T1), how do we address common implementation pitfalls like signature malleability, JSON canonicalization, and secure key storage without over-engineering the MVP?

### Analysis

**Risks Identified (2026 Deep Dive)**:
1.  **Signature Malleability**: Ed25519 signatures can be modified (s + l) without invalidating them.
2.  **JSON Canonicalization**: Standard JSON serializers are not deterministic (key order, whitespace), breaking signatures.
3.  **Key Storage**: Storing private keys in plaintext files is risky, but integrating system keyrings (Keychain/Windows Credential Manager) adds significant cross-platform complexity to the CLI.

### Expert Assessment

**Canonicalization**:
- "Sorting keys" is insufficient for cryptographic operations.
- **Decision**: Adopt **JCS (JSON Canonicalization Scheme - RFC 8785)** using the `jcs` library. This is the internet standard for deterministic JSON.

**Verification**:
- **Decision**: Enforce **RFC 8032 Strict Mode** in verification logic. Signatures must be rejected if `s >= l` or if they contain non-canonical encodings.
- **Decision**: Add `alg: "ed25519"` to the `SignatureBlock` schema to prevent algorithm substitution attacks (crypto-agility).

**Key Storage**:
- While system keyrings are superior, they introduce dependency hell (libsecret on Linux, win32 credential API) that can stall early adopters.
- **Decision**: Start with **Filesystem Storage with Permission Checks**. The CLI MUST refuse to write/read private keys if file permissions are too open (enforce `0600`).
- **Deferred**: Native Keyring integration is marked as an **Optional/Future** enhancement.

### Recommendation: **HARDEN Core, SIMPLIFY Storage**

### Decision

> [!IMPORTANT]
> **ADR-20**: Adopted **JCS (RFC 8785)** for manifest canonicalization and **Strict Ed25519 Verification** (RFC 8032) to prevent malleability.
>
> **Key Storage Strategy**:
> - **v1.2 MVP**: Filesystem storage with strict permission enforcement (`chmod 0600`).
> - **Future**: Native System Keyring integration (deferred to reduce initial dependency complexity).
>
> **Rationale**: Prioritizes protocol security (immutable signatures) while keeping the developer experience simple (no complex OS-level dependencies for the CLI yet).
>
> **Impact**: Added `jcs` dependency to Sprint T1. Added strict verification requirements. Deferral of Keyring noted in roadmap.
>
> **Date**: 2026-02-13
