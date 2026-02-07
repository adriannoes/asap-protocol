# PRD: ASAP Protocol v1.2.0 — Trust Layer

> **Product Requirements Document**
>
> **Version**: 1.2.0
> **Created**: 2026-02-05
> **Last Updated**: 2026-02-05

---

## 1. Executive Summary

### 1.1 Purpose

v1.2.0 establishes the **Trust Layer** for the ASAP Protocol Agent Marketplace. This release delivers:
- **Signed Manifests**: Ed25519 cryptographic signatures for verifiable agent identity
- **Registry API**: Centralized agent discovery service
- **Evaluation Framework**: Protocol compliance testing (Shell) + Intelligence metrics (Brain)
- **Optional mTLS**: Enterprise-grade transport security

### 1.2 Strategic Context

v1.2.0 is the second step toward the Agent Marketplace (v2.0). See [roadmap-to-marketplace.md](../roadmap-to-marketplace.md) for evolution path.

**Key Strategic Decisions** (from strategy review):
- **SD-1**: Centralized registry first, federation later
- **SD-4**: Ed25519 for signing (64-byte signatures, MCP-aligned)
- **SD-5**: 3-tier PKI: Self-signed → Verified ($49/mo) → Enterprise
- **SD-6**: mTLS optional, never required

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
| Registry API | 10,000+ agents supported | P1 |
| ASAP Compliance Harness | 20+ protocol tests | P1 |
| Trust levels visible | In manifest and discovery | P1 |
| mTLS optional | Works when configured | P2 |

---

## 3. User Stories

### Agent Developer
> As an **agent developer**, I want to **sign my manifest with Ed25519** so that **other agents can verify my identity and prevent impersonation**.

### Agent Consumer
> As an **agent consumer**, I want to **search the registry by skill and trust level** so that **I can find reliable agents for my workflows**.

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

### 4.3 Registry API (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| REG-001 | POST /registry/agents (register) | MUST |
| REG-002 | GET /registry/agents/{id} | MUST |
| REG-003 | PUT /registry/agents/{id} (update) | MUST |
| REG-004 | DELETE /registry/agents/{id} | MUST |
| REG-005 | GET /registry/agents?skill=X | MUST |
| REG-006 | Pagination (page, per_page) | MUST |
| REG-007 | Trust level filtering | MUST |
| REG-008 | GET /registry/agents/{id}/reputation | SHOULD |

**Registry Architecture** (SD-1):
| Model | Decision |
|-------|----------|
| Centralized | ✅ Selected for v1.2-v2.0 |
| Federated | Deferred to v2.x+ |

**Why Centralized First**:
- Faster to build, easier quality control
- Developer experience priority (like npm/PyPI)
- Federation can be added when enterprises need private registries

---

### 4.4 ASAP Compliance Harness (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-001 | Pytest-based compliance suite | MUST |
| EVAL-002 | Handshake validation | MUST |
| EVAL-003 | Schema validation | MUST |
| EVAL-004 | State machine validation | MUST |
| EVAL-005 | SLA validation | SHOULD |
| EVAL-006 | Clear pass/fail output | MUST |
| EVAL-007 | DeepEval integration (optional) | MAY |

**Hybrid Strategy: Shell vs Brain**:
| Layer | Tool | Validates |
|-------|------|-----------|
| Shell (ASAP) | pytest | Handshake, Schema, State, SLA |
| Brain (optional) | DeepEval | Reasoning, Tool usage, Safety |

---

### 4.5 Optional mTLS (P2)

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
| Delegation tokens | Part of Economics Layer | v1.3.0 |
| Usage metering | Part of Economics Layer | v1.3.0 |
| Payment processing | Part of Marketplace | v2.0 |
| Federation protocol | After centralized proves ROI | v2.x+ |

---

## 6. Technical Considerations

### 6.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| cryptography | ≥41.0 | Ed25519 signing |
| deepeval | ≥0.21 (optional) | Intelligence evals |

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
├── registry/
│   ├── __init__.py
│   ├── models.py         # Data models
│   ├── api.py            # REST endpoints
│   ├── storage.py        # Storage backend
│   ├── reputation.py     # Reputation
│   └── client.py         # SDK
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
- Registry is optional (well-known discovery still works)
- mTLS is explicitly optional

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Signed manifests | 80% of registered agents |
| Registry query latency | <100ms (p95) |
| Compliance harness coverage | 20+ tests |
| Test coverage | ≥95% |
| Documentation | 100% API coverage |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ed25519 library issues | Low | High | Use battle-tested cryptography package |
| Registry scaling | Medium | Medium | Design for horizontal scaling |
| Adoption friction | Medium | High | Make signing simple with CLI |
| mTLS complexity | Low | Medium | Provide example certs and docs |

---

## 9. Open Questions (Resolved)

| ID | Question | Decision |
|----|----------|----------|
| Q1 | Signing algorithm? | Ed25519 (SD-4) |
| Q2 | Registry centralized or federated? | Centralized first (SD-1) |
| Q3 | mTLS required? | Optional only (SD-6) |
| Q4 | Verified badge pricing? | $49/month (SD-5) |
| Q5 | Compliance as separate package? | Yes (asap-compliance) |

---

## 10. Related Documents

- **Tasks**: [tasks-v1.2.0-roadmap.md](../../dev-planning/tasks/v1.2.0/tasks-v1.2.0-roadmap.md)
- **PKI Details**: [tasks-v1.2.0-pki-detailed.md](../../dev-planning/tasks/v1.2.0/tasks-v1.2.0-pki-detailed.md)
- **Registry Details**: [tasks-v1.2.0-registry-detailed.md](../../dev-planning/tasks/v1.2.0/tasks-v1.2.0-registry-detailed.md)
- **Evals Details**: [tasks-v1.2.0-evals-detailed.md](../../dev-planning/tasks/v1.2.0/tasks-v1.2.0-evals-detailed.md)
- **Roadmap**: [roadmap-to-marketplace.md](../roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../vision-agent-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-05 | 1.0.0 | Initial PRD aligned with strategic decisions |
