# Sprint T4: Testing & Release

> **Goal**: Comprehensive testing and v1.2.0 release
> **Prerequisites**: Sprints T1-T3 completed (PKI, Trust Levels, Compliance Harness)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)
>
> **Note**: This sprint was created during the Lean Marketplace Pivot. Release tasks previously in T6 (now deferred) have been moved here. DeepEval integration has been deferred to v2.2+.

---

## Task 4.1: Comprehensive Testing

**Goal**: All tests pass with v1.1 integration

### Sub-tasks

- [x] 4.1.1 Run full test suite
  - Unit, integration, and E2E tests
  - Ensure v1.2 features work with v1.1 (OAuth2, WebSocket, SQLite)

- [x] 4.1.2 Cross-version compatibility testing
  - Verify signed manifests work with existing discovery
  - Verify compliance harness against sample agents

- [x] 4.1.3 Performance testing
  - Ed25519 signing/verification benchmarks
  - JCS canonicalization overhead benchmarks
  - Compliance harness execution time

**Acceptance Criteria**:
- [ ] Test coverage >95% for new code
- [ ] No regressions in v1.1 features

---

## Task 4.2: Release Preparation

**Goal**: CHANGELOG, docs, version bump

### Sub-tasks

- [x] 4.2.1 Update CHANGELOG.md
  - Document all v1.2.0 features
  - Note deferred items (Registry API, DeepEval)

- [x] 4.2.2 Update README.md
  - Updated quick start with signing
  - Compliance harness usage guide

- [x] 4.2.3 Update Official Docs (MkDocs)
  - **New Page**: `docs/guides/identity-signing.md`
  - **New Page**: `docs/guides/compliance-testing.md`
  - **New Page**: `docs/guides/migration-v1.1-to-v1.2.md`
  - **Update**: `docs/index.md` CLI section with new commands
  - **Reference**: https://adriannoes.github.io/asap-protocol

- [x] 4.2.4 Version bump
  - `pyproject.toml` → 1.2.0
  - `asap-compliance/pyproject.toml` → 1.2.0
  - Update `__version__` in both packages

- [x] 4.2.5 Update AGENTS.md
  - Document new crypto module
  - Document compliance harness

- [x] 4.2.6 Create migration guide
  - v1.1 → v1.2 upgrade steps

**Acceptance Criteria**:
- [x] All docs up to date
- [x] Version bumped

---

## Task 4.3: Build and Publish

**Goal**: PyPI, GitHub, Docker

### Sub-tasks

- [ ] 4.3.1 Run CI pipeline
  - All checks pass

- [ ] 4.3.2 Create GitHub release
  - Tag v1.2.0
  - Release notes

- [ ] 4.3.3 Publish to PyPI
  - `asap-protocol` package
  - `asap-compliance` package

- [ ] 4.3.4 Update Docker image
  - Build and push v1.2.0

**Acceptance Criteria**:
- [ ] v1.2.0 on PyPI
- [ ] GitHub release created
- [ ] Docker image available

---

## Sprint T4 Definition of Done

- [ ] All tests pass
- [ ] CHANGELOG updated
- [ ] v1.2.0 published to PyPI
- [ ] Compliance harness published as separate package
- [ ] Documentation complete

**Total Sub-tasks**: ~13

## Relevant Files (Task 4.1 + 4.2)
- `tests/integration/test_cross_version_compatibility.py` – Cross-version compatibility tests
- `asap-compliance/tests/test_handshake.py` – Signed manifest handshake test
- `benchmarks/benchmark_crypto.py` – Ed25519, JCS, compliance benchmarks
- `benchmarks/RESULTS.md` – v1.2.0 crypto benchmark section
- `CHANGELOG.md` – v1.2.0 release notes
- `README.md` – Quick start signing, compliance harness
- `docs/guides/identity-signing.md` – Identity signing guide
- `docs/guides/compliance-testing.md` – Compliance testing guide
- `docs/guides/migration-v1.1-to-v1.2.md` – Migration guide
- `docs/index.md` – CLI section updated
- `mkdocs.yml` – New guides in nav
- `AGENTS.md` – Crypto, compliance, mTLS documented
- `pyproject.toml`, `asap-compliance/pyproject.toml` – Version 1.2.0

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v1.2.0 Roadmap](./tasks-v1.2.0-roadmap.md)
