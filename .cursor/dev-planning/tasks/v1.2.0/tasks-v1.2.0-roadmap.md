# Tasks: ASAP Protocol v1.2.0 Roadmap

> **High-level task overview** for v1.2.0 milestone (Trust Layer)
>
> **Parent PRD**: [roadmap-to-marketplace.md](../../product-specs/roadmap-to-marketplace.md)
> **Prerequisite**: v1.1.0 released
> **Target Version**: v1.2.0
> **Focus**: Signed Manifests (Ed25519), Registry API, Evals, mTLS (optional)
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [T1-T2: PKI & Manifest Signing](./tasks-v1.2.0-pki-detailed.md)
> - [T3-T4: Registry API](./tasks-v1.2.0-registry-detailed.md)
> - [T5-T6: Evals & Release](./tasks-v1.2.0-evals-detailed.md)

---

## Strategic Context

v1.2.0 establishes the Trust Layer for the marketplace:
- **Signed Manifests**: Verifiable agent identity using Ed25519 (per SD-4)
- **Registry API**: Centralized discovery service (per SD-1)
- **Evals Framework**: Protocol compliance testing (Shell) + Intelligence (Brain)
- **mTLS**: Optional transport security (per SD-6)

---

## Sprint T1: Ed25519 PKI Foundation

**Goal**: Implement cryptographic signing infrastructure (per SD-4, SD-5)

### Tasks

- [ ] 1.1 Implement key generation and management
  - Goal: Ed25519 keypair generation, storage, rotation
  - Deliverable: `src/asap/crypto/keys.py`
  - Details: [PKI Detailed - Task 1.1](./tasks-v1.2.0-pki-detailed.md#task-11-key-management)

- [ ] 1.2 Implement manifest signing
  - Goal: Sign manifests with Ed25519
  - Deliverable: `src/asap/crypto/signing.py`
  - Details: [PKI Detailed - Task 1.2](./tasks-v1.2.0-pki-detailed.md#task-12-manifest-signing)

- [ ] 1.3 Implement signature verification
  - Goal: Verify signed manifests
  - Deliverable: Verification in client
  - Details: [PKI Detailed - Task 1.3](./tasks-v1.2.0-pki-detailed.md#task-13-signature-verification)

### Definition of Done
- [ ] Ed25519 key generation working
- [ ] Manifests signed with 64-byte signatures
- [ ] Verification rejects tampering
- [ ] Test coverage >95%

---

## Sprint T2: Trust Levels & mTLS

**Goal**: Implement 3-tier trust levels and optional mTLS (per SD-5, SD-6)

### Tasks

- [ ] 2.1 Implement trust level model
  - Goal: Self-signed, Verified ($49/mo), Enterprise levels
  - Deliverable: Trust level enum and validation
  - Details: [PKI Detailed - Task 2.1](./tasks-v1.2.0-pki-detailed.md#task-21-trust-levels)

- [ ] 2.2 Add Verified badge simulation
  - Goal: ASAP-signed manifests for "Verified" agents
  - Note: Actual verification service is v2.0
  - Details: [PKI Detailed - Task 2.2](./tasks-v1.2.0-pki-detailed.md#task-22-verified-badge)

- [ ] 2.3 Implement optional mTLS
  - Goal: Mutual TLS for transport security
  - Constraint: Optional, never required (SD-6)
  - Details: [PKI Detailed - Task 2.3](./tasks-v1.2.0-pki-detailed.md#task-23-mtls-support)

### Definition of Done
- [ ] Trust levels displayed in manifest
- [ ] mTLS optional and configurable
- [ ] Enterprise CA support ready

---

## Sprint T3: Registry API Core

**Goal**: Implement centralized registry service (per SD-1)

### Tasks

- [ ] 3.1 Implement registry data model
  - Goal: Agent registration storage
  - Deliverable: `src/asap/registry/models.py`
  - Details: [Registry Detailed - Task 3.1](./tasks-v1.2.0-registry-detailed.md#task-31-data-model)

- [ ] 3.2 Implement registry CRUD endpoints
  - Goal: Register, update, delete, get agents
  - Deliverable: RESTful API
  - Details: [Registry Detailed - Task 3.2](./tasks-v1.2.0-registry-detailed.md#task-32-crud-endpoints)

- [ ] 3.3 Implement search and filtering
  - Goal: Search by skill, capability, trust level
  - Deliverable: Query API
  - Details: [Registry Detailed - Task 3.3](./tasks-v1.2.0-registry-detailed.md#task-33-search-api)

### Definition of Done
- [ ] Agents can register with signed manifests
- [ ] Search returns matching agents
- [ ] API documented

---

## Sprint T4: Registry Features

**Goal**: Add reputation and advanced features

### Tasks

- [ ] 4.1 Implement basic reputation
  - Goal: Store and retrieve reputation scores
  - Deliverable: Reputation endpoint
  - Details: [Registry Detailed - Task 4.1](./tasks-v1.2.0-registry-detailed.md#task-41-reputation-system)

- [ ] 4.2 Add registry client SDK
  - Goal: Python SDK for registry operations
  - Deliverable: `src/asap/registry/client.py`
  - Details: [Registry Detailed - Task 4.2](./tasks-v1.2.0-registry-detailed.md#task-42-registry-client)

- [ ] 4.3 Integrate discovery with registry
  - Goal: Client.discover() uses registry if available
  - Fallback: Well-known URI (v1.1)
  - Details: [Registry Detailed - Task 4.3](./tasks-v1.2.0-registry-detailed.md#task-43-discovery-integration)

### Definition of Done
- [ ] Reputation queryable
- [ ] SDK simplifies registry ops
- [ ] Discovery prefers registry

---

## Sprint T5: ASAP Compliance Harness

**Goal**: Implement Shell evaluation (protocol compliance)

### Tasks

- [ ] 5.1 Create compliance test suite
  - Goal: Pytest-based compliance tests
  - Deliverable: `asap-compliance/` package
  - Details: [Evals Detailed - Task 5.1](./tasks-v1.2.0-evals-detailed.md#task-51-compliance-suite)

- [ ] 5.2 Implement handshake validation
  - Goal: Validate agent handshake correctness
  - Details: [Evals Detailed - Task 5.2](./tasks-v1.2.0-evals-detailed.md#task-52-handshake-validation)

- [ ] 5.3 Implement schema validation
  - Goal: Verify Pydantic schema compliance
  - Details: [Evals Detailed - Task 5.3](./tasks-v1.2.0-evals-detailed.md#task-53-schema-validation)

- [ ] 5.4 Implement state machine validation
  - Goal: Verify correct state transitions
  - Details: [Evals Detailed - Task 5.4](./tasks-v1.2.0-evals-detailed.md#task-54-state-machine-validation)

### Definition of Done
- [ ] Compliance harness runnable against any agent
- [ ] Clear pass/fail output
- [ ] Documentation for agent developers

---

## Sprint T6: DeepEval Integration & Release

**Goal**: Add Intelligence evaluation and release v1.2.0

### Tasks

- [ ] 6.1 Integrate DeepEval (optional)
  - Goal: Intelligence metrics for Brain evaluation
  - Deliverable: DeepEval adapter
  - Details: [Evals Detailed - Task 6.1](./tasks-v1.2.0-evals-detailed.md#task-61-deepeval-integration)

- [ ] 6.2 Run comprehensive testing
  - Goal: All tests pass
  - Details: [Evals Detailed - Task 6.2](./tasks-v1.2.0-evals-detailed.md#task-62-comprehensive-testing)

- [ ] 6.3 Prepare release materials
  - Goal: CHANGELOG, docs, version bump
  - Details: [Evals Detailed - Task 6.3](./tasks-v1.2.0-evals-detailed.md#task-63-release-preparation)

- [ ] 6.4 Build and publish
  - Goal: PyPI, GitHub, Docker
  - Details: [Evals Detailed - Task 6.4](./tasks-v1.2.0-evals-detailed.md#task-64-build-and-publish)

### Definition of Done
- [ ] Compliance harness published
- [ ] DeepEval integration documented
- [ ] v1.2.0 on PyPI

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| T1 | 3 | Ed25519 PKI | 5-7 |
| T2 | 3 | Trust Levels + mTLS | 4-6 |
| T3 | 3 | Registry API Core | 6-8 |
| T4 | 3 | Registry Features | 4-6 |
| T5 | 4 | Compliance Harness | 5-7 |
| T6 | 4 | DeepEval + Release | 4-6 |

**Total**: 20 high-level tasks across 6 sprints

---

## Progress Tracking

**Overall Progress**: 0/20 tasks completed (0%)

**Sprint Status**:
- ⬜ T1: 0/3 tasks (0%)
- ⬜ T2: 0/3 tasks (0%)
- ⬜ T3: 0/3 tasks (0%)
- ⬜ T4: 0/3 tasks (0%)
- ⬜ T5: 0/4 tasks (0%)
- ⬜ T6: 0/4 tasks (0%)

**Last Updated**: 2026-02-05

---

## Related Documents

- **Detailed Tasks**: See sprint files listed at top
- **Parent Roadmap**: [roadmap-to-marketplace.md](../../product-specs/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../product-specs/vision-agent-marketplace.md)
- **Strategic Decisions**: SD-1, SD-4, SD-5, SD-6 in roadmap
