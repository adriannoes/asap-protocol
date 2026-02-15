# Tasks: ASAP Protocol v1.2.0 Roadmap

> **High-level task overview** for v1.2.0 milestone (Verified Identity)
>
> **Parent PRD**: [prd-v1.2-roadmap.md](../../../product-specs/prd/prd-v1.2-roadmap.md)
> **Prerequisite**: v1.1.0 released
> **Target Version**: v1.2.0
> **Focus**: Signed Manifests (Ed25519), Compliance Harness, mTLS (optional)
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [T1: Ed25519 PKI Foundation](./sprint-T1-ed25519-pki.md)
> - [T2: Trust Levels & mTLS](./sprint-T2-trust-levels-mtls.md)
> - [T3: Compliance Harness](./sprint-T3-compliance-harness.md)
> - [T4: Testing & Release](./sprint-T4-testing-release.md)
>
> **Lean Marketplace Pivot**: Registry API (formerly T3/T4) and DeepEval (formerly T6) have been deferred. See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

---

## Strategic Context

v1.2.0 establishes Verified Identity for the marketplace:
- **Signed Manifests**: Verifiable agent identity using Ed25519 (per SD-4)
- **Compliance Harness**: Protocol compliance testing (Shell-only)
- **mTLS**: Optional transport security (per SD-6)

> [!NOTE]
> **Deferred from v1.2**: Registry API Backend (to v2.1), DeepEval Intelligence (to v2.2+). Lite Registry (v1.1) provides discovery. See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

### Prerequisites from v1.1.0

| v1.1 Deliverable | v1.2 Usage |
|-------------------|------------|
| Health endpoint (`/.well-known/asap/health`) | Compliance harness validates agent liveness (SD-10) |
| `ttl_seconds` in Manifest | Compliance harness validates freshness |
| Lite Registry (`registry.json`) | Continues as discovery mechanism (SD-11) |
| Well-known discovery | Extended with signed manifests |

---

## Sprint T1: Ed25519 PKI Foundation ✅

**Goal**: Implement cryptographic signing infrastructure (per SD-4, SD-5)

### Tasks

- [x] 1.1 Implement key generation and management
  - Goal: Ed25519 keypair generation, storage, rotation
  - Deliverable: `src/asap/crypto/keys.py`
  - Details: [PKI Detailed - Task 1.1](./sprint-T1-ed25519-pki.md#task-11-key-management)

- [x] 1.2 Implement manifest signing
  - Goal: Sign manifests with Ed25519
  - Deliverable: `src/asap/crypto/signing.py`
  - Details: [PKI Detailed - Task 1.2](./sprint-T1-ed25519-pki.md#task-12-manifest-signing)

- [x] 1.3 Implement signature verification
  - Goal: Verify signed manifests
  - Deliverable: Verification in client
  - Details: [PKI Detailed - Task 1.3](./sprint-T1-ed25519-pki.md#task-13-signature-verification)

### Definition of Done
- [x] Ed25519 key generation working
- [x] Manifests signed with 64-byte signatures
- [x] Verification rejects tampering
- [x] Test coverage >95%

---

## Sprint T2: Trust Levels & mTLS ✅

**Goal**: Implement 3-tier trust levels and optional mTLS (per SD-5, SD-6)

### Tasks

- [x] 2.1 Implement trust level model
  - Goal: Self-signed, Verified ($49/mo), Enterprise levels
  - Deliverable: Trust level enum and validation
  - Details: [PKI Detailed - Task 2.1](./sprint-T2-trust-levels-mtls.md#task-21-trust-levels)

- [x] 2.2 Add Verified badge simulation
  - Goal: ASAP-signed manifests for "Verified" agents
  - Note: Actual verification service is v2.0
  - Details: [PKI Detailed - Task 2.2](./sprint-T2-trust-levels-mtls.md#task-22-verified-badge)

- [x] 2.3 Implement optional mTLS
  - Goal: Mutual TLS for transport security
  - Constraint: Optional, never required (SD-6)
  - Details: [PKI Detailed - Task 2.3](./sprint-T2-trust-levels-mtls.md#task-23-mtls-support)

### Definition of Done
- [x] Trust levels displayed in manifest
- [x] mTLS optional and configurable
- [x] Enterprise CA support ready

---

## Sprint T3: ASAP Compliance Harness

**Goal**: Implement Shell evaluation (protocol compliance)

### Tasks

- [x] 3.1 Create compliance test suite
  - Goal: Pytest-based compliance tests
  - Deliverable: `asap-compliance/` package
  - Details: [Evals Detailed - Task 3.1](./sprint-T3-compliance-harness.md#task-31-compliance-suite)

- [x] 3.2 Implement handshake validation
  - Goal: Validate agent handshake correctness
  - Details: [Evals Detailed - Task 3.2](./sprint-T3-compliance-harness.md#task-32-handshake-validation)

- [x] 3.3 Implement schema validation
  - Goal: Verify Pydantic schema compliance
  - Details: [Evals Detailed - Task 3.3](./sprint-T3-compliance-harness.md#task-33-schema-validation)

- [x] 3.4 Implement state machine validation
  - Goal: Verify correct state transitions
  - Details: [Evals Detailed - Task 3.4](./sprint-T3-compliance-harness.md#task-34-state-machine-validation)

### Definition of Done
- [x] Compliance harness runnable against any agent
- [x] Clear pass/fail output
- [x] Documentation for agent developers (`docs/guides/compliance-testing.md`, `docs/guides/identity-signing.md`, `docs/guides/migration-v1.1-to-v1.2.md`)

---

## Sprint T4: Testing & Release

**Goal**: Comprehensive testing and release v1.2.0

### Tasks

- [x] 4.1 Run comprehensive testing
  - Goal: All tests pass, integration tests with v1.1 features
  - Details: [Release Detailed - Task 4.1](./sprint-T4-testing-release.md#task-41-comprehensive-testing)

- [x] 4.2 Prepare release materials
  - Goal: CHANGELOG, docs, version bump
  - Details: [Release Detailed - Task 4.2](./sprint-T4-testing-release.md#task-42-release-preparation)

- [x] 4.3 Build and publish
  - Goal: PyPI, GitHub, Docker
  - Details: [Release Detailed - Task 4.3](./sprint-T4-testing-release.md#task-43-build-and-publish)

### Definition of Done
- [x] Compliance harness published (asap-compliance on PyPI)
- [x] v1.2.0 on PyPI
- [x] Documentation complete

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| T1 | 3 | Ed25519 PKI | 5-7 |
| T2 | 3 | Trust Levels + mTLS | 4-6 |
| T3 | 4 | Compliance Harness | 5-7 |
| T4 | 3 | Testing + Release | 4-6 |

**Total**: 13 high-level tasks across 4 sprints

---

## Progress Tracking

**Overall Progress**: 13/13 tasks completed (100%) ✅

**Sprint Status**:
- ✅ T1: 3/3 tasks (100%) — merged PR #42
- ✅ T2: 3/3 tasks (100%) — Trust Levels, Verified badge, mTLS (branch t2-trust-levels)
- ✅ T3: 4/4 tasks (100%) — Compliance Harness (branch t3-compliance-harness)
- ✅ T4: 3/3 tasks (100%) — v1.2.0 released (PyPI, GitHub, Docker)

**Last Updated**: 2026-02-15

---

## Related Documents

- **Detailed Tasks**: See sprint files listed at top
- **Parent PRD**: [prd-v1.2-roadmap.md](../../../product-specs/prd/prd-v1.2-roadmap.md)
- **Deferred Backlog**: [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md)
- **Parent Roadmap**: [roadmap-to-marketplace.md](../../../product-specs/strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../../product-specs/strategy/vision-agent-marketplace.md)
- **Strategic Decisions**: SD-4, SD-5, SD-6, SD-11 in roadmap

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-05 | Initial task roadmap |
| 2026-02-12 | **Lean Marketplace pivot**: Removed Registry sprints (T3/T4) and DeepEval sprint (T6), renumbered Compliance Harness to T3 and Testing/Release to T4, reduced from 6 sprints (20 tasks) to 4 sprints (13 tasks) |
| 2026-02-13 | **Sprint T1 complete**: Ed25519 PKI (key management, signing, verification) merged via PR #42 |
| 2026-02-13 | **Sprint T2 complete**: Trust Levels (2.1), Verified badge simulation (2.2), optional mTLS (2.3) on branch t2-trust-levels |
| 2026-02-15 | **Sprint T4 progress**: 4.1 comprehensive testing ✅, 4.2 release materials ✅; 4.3 build/publish pending (tag v1.2.0 + asap-compliance publish) |
| 2026-02-15 | **v1.2.0 released**: PyPI (asap-protocol + asap-compliance), GitHub Release, Docker ghcr.io. Trusted Publishing configured for asap-compliance. Sprint T4 complete. |
