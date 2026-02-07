# Sprint T3: Registry API Core

> **Goal**: Centralized agent discovery service
> **Prerequisites**: Sprints T1-T2 completed (PKI, Trust Levels)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `src/asap/registry/__init__.py` - Registry module init
- `src/asap/registry/models.py` - Data models
- `src/asap/registry/api.py` - REST endpoints
- `src/asap/registry/storage.py` - Storage backend
- `tests/registry/__init__.py` - Registry test package
- `tests/registry/test_api.py` - API tests

---

## Context

The Registry is the centralized discovery service for ASAP agents. It stores signed manifests, enables search by skill/capability, and provides trust information. This is the foundation for the Agent Marketplace.

---

## Task 3.1: Data Model

**Goal**: Define Pydantic models for registry data structures.

**Prerequisites**: T2 completed (TrustLevel enum exists)

### Sub-tasks

- [ ] 3.1.1 Create registry module
  - **File**: `src/asap/registry/__init__.py` (create new)
  - **File**: `src/asap/registry/models.py` (create new)
  - **Pattern**: Follow structure of `src/asap/crypto/` module
  - **Verify**: `from asap.registry import models` imports without error

- [ ] 3.1.2 Define AgentRegistration model
  ```python
  class AgentRegistration(BaseModel):
      id: str  # URN
      signed_manifest: SignedManifest
      trust_level: TrustLevel
      registered_at: datetime
      updated_at: datetime
      status: RegistrationStatus
      skills: List[str]
      capabilities: Dict[str, Any]
  ```

- [ ] 3.1.3 Define RegistrationStatus enum
  ```python
  class RegistrationStatus(str, Enum):
      ACTIVE = "active"
      PENDING = "pending"  # Awaiting verification
      SUSPENDED = "suspended"
      REVOKED = "revoked"
  ```

- [ ] 3.1.4 Implement storage interface
  - **Interface**: `RegistryStorage` ABC
  - **Methods**: `save`, `get`, `delete`, `list`, `search`

- [ ] 3.1.5 Implement in-memory storage
  - For development and testing
  - Optional: SQLite for persistence

- [ ] 3.1.6 Write tests
  - Test: Model validation
  - Test: Storage operations

- [ ] 3.1.7 Commit
  - **Command**: `git commit -m "feat(registry): add data models and storage"`

**Acceptance Criteria**:
- [ ] Data models defined and tested
- [ ] Storage interface implemented

---

## Task 3.2: CRUD Endpoints

**Goal**: RESTful API for agent management

### Sub-tasks

- [ ] 3.2.1 Create API module
  - **File**: `src/asap/registry/api.py`

- [ ] 3.2.2 Implement POST /registry/agents
  - **Input**: SignedManifest
  - **Validate**: Signature before accepting
  - **Return**: AgentRegistration

- [ ] 3.2.3 Implement GET /registry/agents/{id}
  - **Return**: AgentRegistration
  - **404**: If not found

- [ ] 3.2.4 Implement PUT /registry/agents/{id}
  - **Update**: Manifest (re-validate signature)
  - **Require**: Same public key

- [ ] 3.2.5 Implement DELETE /registry/agents/{id}
  - **Require**: Signed deletion request
  - **Status**: Mark as revoked

- [ ] 3.2.6 Add authentication
  - **Require**: OAuth2 for mutations
  - **Allow**: Anonymous reads

- [ ] 3.2.7 Write integration tests
  - Test: Full CRUD lifecycle
  - Test: Auth required for writes

- [ ] 3.2.8 Commit
  - **Command**: `git commit -m "feat(registry): add CRUD endpoints"`

**Acceptance Criteria**:
- [ ] Agents can register and update
- [ ] Auth enforced for writes

---

## Task 3.3: Search API

**Goal**: Query agents by skill and capability

### Sub-tasks

- [ ] 3.3.1 Implement GET /registry/agents
  - **Query params**: `skill`, `trust_level`, `capability`
  - **Pagination**: `page`, `per_page`

- [ ] 3.3.2 Implement skill-based search
  - **Parameter**: `?skill=code_review`
  - **Match**: Agents with matching skill

- [ ] 3.3.3 Implement capability filtering
  - **Parameter**: `?capability.max_latency_ms=<5000`
  - **Filter**: Agents meeting criteria

- [ ] 3.3.4 Implement trust level filtering
  - **Parameter**: `?trust_level=verified`
  - **Filter**: Only verified agents

- [ ] 3.3.5 Add sorting
  - **Options**: `registered_at`, `reputation`, `name`
  - **Default**: Reputation descending

- [ ] 3.3.6 Write tests
  - Test: Various query combinations
  - Test: Pagination works

- [ ] 3.3.7 Commit
  - **Command**: `git commit -m "feat(registry): add search and filtering"`

**Acceptance Criteria**:
- [ ] Search returns relevant agents
- [ ] Filtering works correctly
- [ ] Pagination implemented

---

## Task 3.4: Bootstrap from Lite Registry (SD-11)

**Goal**: Seed the Registry with agents from v1.1 `registry.json`.

**Context**: v1.1 used a static file on GitHub Pages. v1.2 must import these agents so they don't lose visibility.

### Sub-tasks

- [ ] 3.4.1 Implement import script
  - **Input**: URL to `registry.json`
  - **Action**: Fetch, parse, and validate each agent
  - **Storage**: Save valid agents to Registry DB
  - **Status**: Mark imported agents as "Verified" (if valid) or "Pending"

- [ ] 3.4.2 Auto-run on first deployment
  - **Goal**: Registry is not empty on launch
  - **Verify**: `registry.json` agents appear in GET /registry/agents

- [ ] 3.4.3 Commit
  - **Command**: `git commit -m "feat(registry): add bootstrap from v1.1 lite registry"`

**Acceptance Criteria**:
- [ ] v1.1 agents are present in v1.2 Registry
- [ ] Import handles duplicates gracefully


---

## Sprint T3 Definition of Done

- [ ] Registry API functional
- [ ] CRUD operations working
- [ ] Search and filtering working
- [ ] Test coverage >95%

**Total Sub-tasks**: ~18
