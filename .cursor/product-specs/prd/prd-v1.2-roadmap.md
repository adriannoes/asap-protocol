# PRD: ASAP Protocol v1.2.0 — Verified Identity

> **Product Requirements Document**
>
> **Version**: 1.2.0
> **Created**: 2026-02-05
> **Last Updated**: 2026-02-12

---

## 1. Executive Summary

### 1.1 Purpose

v1.2.0 establishes **Verified Identity** for the ASAP Protocol Agent Marketplace. This release delivers:
- **Signed Manifests**: Ed25519 cryptographic signatures for verifiable agent identity
- **Compliance Harness**: Protocol compliance testing (Shell)
- **Optional mTLS**: Enterprise-grade transport security

> [!NOTE]
> **Lean Marketplace Pivot**: Registry API Backend and DeepEval Intelligence are deferred. See [deferred-backlog.md](../strategy/deferred-backlog.md).

### 1.2 Strategic Context

v1.2.0 is the second step toward the Agent Marketplace (v2.0). See [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md) for evolution path.

**Key Strategic Decisions** (from strategy review):
- **SD-4**: Ed25519 for signing (64-byte signatures, MCP-aligned)
- **SD-5**: 3-tier PKI: Self-signed → Verified ($49/mo) → Enterprise
- **SD-6**: mTLS optional, never required
- **SD-11**: Lite Registry (v1.1) provides discovery — no backend API needed yet

### 1.3 Target Audience (ICP)

| Priority | Segment | Why |
|----------|---------|-----|
| 1 | AI Startups | Need verified agents for enterprise clients |
| 2 | Individual Developers | Want to list agents in registry |
| Future | Enterprise | Will use Verified/Enterprise tiers |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Ed25519 manifest signing | Signature verification <5ms | P1 |
| ASAP Compliance Harness | 20+ protocol tests | P1 |
| Trust levels visible | In manifest and discovery | P1 |
| mTLS optional | Works when configured | P2 |

---

## 3. User Stories

### Agent Developer
> As an **agent developer**, I want to **sign my manifest with Ed25519** so that **other agents can verify my identity and prevent impersonation**.

### Agent Consumer
> As an **agent consumer**, I want to **search the Lite Registry by skill** so that **I can find agents for my workflows**.

### Enterprise Client
> As an **enterprise client**, I want to **filter by Verified agents** so that **I only use agents that passed ASAP review**.

### Protocol Maintainer
> As a **protocol maintainer**, I want to **run compliance tests against any agent** so that **I can verify they correctly implement ASAP**.

---

## 4. Functional Requirements

### 4.1 Ed25519 PKI (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| PKI-001 | Ed25519 keypair generation | MUST |
| PKI-002 | Key serialization (PEM, Base64) | MUST |
| PKI-003 | Manifest signing function | MUST |
| PKI-004 | Signature verification | MUST |
| PKI-005 | CLI: asap manifest sign | MUST |
| PKI-006 | CLI: asap manifest verify | MUST |
| PKI-007 | Key rotation support | SHOULD |

**Signed Manifest Schema**:
```json
{
  "manifest": {
    "id": "urn:asap:agent:example",
    "version": "1.0.0"
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "base64...",
    "value": "base64... (64 bytes)",
    "trust_level": "self-signed"
  }
}
```

**Why Ed25519** (SD-4):
| Option | Considered | Outcome |
|--------|------------|---------|
| Ed25519 | ✅ Selected | Modern, fast, 64-byte signatures, MCP-aligned |
| ECDSA | Rejected | Multiple curves = complexity |
| RSA | Rejected | Slow, 256+ byte signatures |

---

### 4.2 Trust Levels (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRUST-001 | TrustLevel enum (self-signed, verified, enterprise) | MUST |
| TRUST-002 | Display trust level in manifest | MUST |
| TRUST-003 | ASAP CA for Verified signing | MUST |
| TRUST-004 | Enterprise CA integration | SHOULD |
| TRUST-005 | Trust level filtering in search | MUST |

**3-Tier PKI Model** (SD-5):
| Level | Badge | Cost | Signing |
|-------|-------|------|---------|
| Self-signed | None | Free | Agent's key |
| Verified | ✓ | $49/month | ASAP-signed |
| Enterprise | Custom | TBD | Org CA |

---

### 4.3 ASAP Compliance Harness (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-001 | Pytest-based compliance suite | MUST |
| EVAL-002 | Handshake validation | MUST |
| EVAL-003 | Schema validation | MUST |
| EVAL-004 | State machine validation | MUST |
| EVAL-005 | SLA validation | SHOULD |
| EVAL-006 | Clear pass/fail output | MUST |

**Shell-only strategy**: Protocol compliance via ASAP-native pytest harness.

| Layer | Tool | Validates |
|-------|------|-----------|
| Shell (ASAP) | pytest | Handshake, Schema, State, SLA |

---

### 4.4 Optional mTLS (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| MTLS-001 | SSL context with client certs | MUST |
| MTLS-002 | Server-side mTLS configuration | MUST |
| MTLS-003 | Client-side cert provision | MUST |
| MTLS-004 | Default: disabled (never required) | MUST |
| MTLS-005 | Documentation for cert generation | MUST |

**Why Optional** (SD-6):
| Option | Decision |
|--------|----------|
| mTLS required | Rejected (high friction, blocks adoption) |
| mTLS optional | ✅ Selected (enterprise can enable, others ignore) |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Registry API Backend | Lite Registry sufficient for MVP | v2.1 (deferred) |
| DeepEval Intelligence | Marketplace doesn't need AI quality scoring | v2.2+ (deferred) |
| Delegation tokens | Part of Observability Layer | v1.3.0 |
| Usage metering | Part of Observability Layer | v1.3.0 |
| Payment processing | Part of Marketplace | v2.0 |
| Federation protocol | After centralized proves ROI | v2.x+ |

---

## 6. Technical Considerations

### 6.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| cryptography | ≥41.0 | Ed25519 signing |

### 6.2 New Packages

| Package | Description |
|---------|-------------|
| asap-compliance | Separate PyPI package for compliance testing |

### 6.3 Code Structure

```
src/asap/
├── crypto/
│   ├── __init__.py
│   ├── keys.py           # Key generation
│   ├── signing.py        # Manifest signing
│   └── trust.py          # Trust levels
└── transport/
    └── mtls.py           # mTLS support

asap-compliance/          # Separate package
├── asap_compliance/
│   ├── harness.py
│   └── validators/
│       ├── handshake.py
│       ├── schema.py
│       └── state.py
```

### 6.4 Backward Compatibility

- Unsigned manifests still accepted (fallback to self-signed)
- Lite Registry (v1.1) continues to work alongside signed manifests
- mTLS is explicitly optional

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Signed manifests | 80% of registered agents |
| Compliance harness coverage | 20+ tests |
| Test coverage | ≥95% |
| Documentation | 100% API coverage |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ed25519 library issues | Low | High | Use battle-tested cryptography package |
| Adoption friction | Medium | High | Make signing simple with CLI |
| mTLS complexity | Low | Medium | Provide example certs and docs |

---

## 9. Open Questions (Resolved)

| ID | Question | Decision |
|----|----------|----------|
| Q1 | Signing algorithm? | Ed25519 (SD-4) |
| Q2 | Registry in v1.2? | Deferred (Lean Marketplace pivot, SD-11 Lite Registry sufficient) |
| Q3 | mTLS required? | Optional only (SD-6) |
| Q4 | Verified badge pricing? | $49/month (SD-5) |
| Q5 | Compliance as separate package? | Yes (asap-compliance) |
| Q6 | DeepEval in v1.2? | Deferred to v2.2+ (Lean Marketplace pivot) |

---

## 10. Prerequisites from v1.1.0

v1.2 builds on interfaces and infrastructure delivered in v1.1.0:

| v1.1 Deliverable | v1.2 Usage | Reference |
|-------------------|------------|-----------|
| Health endpoint (`/.well-known/asap/health`) | Registry uses health check to verify agent liveness before listing | SD-10, ADR-14 |
| `ttl_seconds` in Manifest | Registry tracks agent freshness and marks stale agents | SD-10, ADR-14 |
| `SnapshotStore` interface + SQLite impl | Registry storage follows same interface pattern | SD-9, ADR-13 |
| Well-known discovery | Registry extends (not replaces) well-known discovery | SD-7 |

---

## 11. Related Documents

- **Tasks**: [tasks-v1.2.0-roadmap.md](../../dev-planning/tasks/v1.2.0/tasks-v1.2.0-roadmap.md)
- **PKI Details**: [Sprint T1](../../dev-planning/tasks/v1.2.0/sprint-T1-ed25519-pki.md), [Sprint T2](../../dev-planning/tasks/v1.2.0/sprint-T2-trust-levels-mtls.md)
- **Evals Details**: [Sprint T3](../../dev-planning/tasks/v1.2.0/sprint-T3-compliance-harness.md), [Sprint T4](../../dev-planning/tasks/v1.2.0/sprint-T4-testing-release.md)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **State Management Decision**: [ADR-13](../decision-records/01-architecture.md)
- **Liveness Decision**: [ADR-14](../decision-records/01-architecture.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-05 | 1.0.0 | Initial PRD aligned with strategic decisions |
| 2026-02-07 | 1.1.0 | Added prerequisites section referencing v1.1 deliverables (SD-9, SD-10) |
| 2026-02-12 | 1.2.0 | **Lean Marketplace pivot**: Renamed to "Verified Identity", removed Registry API (deferred v2.1) and DeepEval (deferred v2.2+), removed §4.3 Registry, simplified compliance harness to Shell-only, updated non-goals, related docs |
