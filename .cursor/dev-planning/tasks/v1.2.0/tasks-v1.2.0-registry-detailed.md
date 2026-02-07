# Tasks: ASAP v1.2.0 Registry API (T3-T4) - Detailed

> **Sprints**: T3-T4 - Registry service and features
> **Goal**: Centralized agent discovery service
> **Prerequisites**: T1-T2 completed (PKI, Signing, Trust Levels)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint T3: Registry Core
- `src/asap/registry/__init__.py` - Registry module init
- `src/asap/registry/models.py` - Data models
- `src/asap/registry/api.py` - REST endpoints
- `src/asap/registry/storage.py` - Storage backend
- `tests/registry/test_api.py` - API tests

### Sprint T4: Registry Features
- `src/asap/registry/reputation.py` - Reputation system
- `src/asap/registry/client.py` - Client SDK
- `tests/registry/test_reputation.py` - Reputation tests
- `tests/registry/test_client.py` - Client SDK tests

---

## Sprint T3: Registry API Core

**Context**: The Registry is the centralized discovery service for ASAP agents. It stores signed manifests, enables search by skill/capability, and provides trust information. This is the foundation for the Agent Marketplace.

### Task 3.1: Data Model

**Goal**: Define Pydantic models for registry data structures.

**Context**: The registry stores agent registrations (signed manifests + metadata). These models define the API contract for all registry operations.

**Prerequisites**: T2 completed (TrustLevel enum exists)

#### Sub-tasks

- [ ] 3.1.1 Create registry module
  - **File**: `src/asap/registry/__init__.py` (create new)
  - **File**: `src/asap/registry/models.py` (create new)
  - **What**: Create registry module with data model skeleton
  - **Why**: Separates registry concerns, enables future storage backends
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
  - Interface: `RegistryStorage` ABC
  - Method: `save`, `get`, `delete`, `list`, `search`

- [ ] 3.1.5 Implement in-memory storage
  - For development and testing
  - Optional: SQLite for persistence

- [ ] 3.1.6 Write tests
  - Test: Model validation
  - Test: Storage operations

- [ ] 3.1.7 Commit
  - Command: `git commit -m "feat(registry): add data models and storage"`

**Acceptance**: Data models defined and tested

---

### Task 3.2: CRUD Endpoints

**Goal**: RESTful API for agent management

- [ ] 3.2.1 Create API module
  - File: `src/asap/registry/api.py`

- [ ] 3.2.2 Implement POST /registry/agents
  - Input: SignedManifest
  - Validate: Signature before accepting
  - Return: AgentRegistration

- [ ] 3.2.3 Implement GET /registry/agents/{id}
  - Return: AgentRegistration
  - 404: If not found

- [ ] 3.2.4 Implement PUT /registry/agents/{id}
  - Update: Manifest (re-validate signature)
  - Require: Same public key

- [ ] 3.2.5 Implement DELETE /registry/agents/{id}
  - Require: Signed deletion request
  - Status: Mark as revoked

- [ ] 3.2.6 Add authentication
  - Require: OAuth2 for mutations
  - Allow: Anonymous reads

- [ ] 3.2.7 Write integration tests
  - Test: Full CRUD lifecycle
  - Test: Auth required for writes

- [ ] 3.2.8 Commit
  - Command: `git commit -m "feat(registry): add CRUD endpoints"`

**Acceptance**: Agents can register and update

---

### Task 3.3: Search API

**Goal**: Query agents by skill and capability

- [ ] 3.3.1 Implement GET /registry/agents
  - Query params: `skill`, `trust_level`, `capability`
  - Pagination: `page`, `per_page`

- [ ] 3.3.2 Implement skill-based search
  - Parameter: `?skill=code_review`
  - Match: Agents with matching skill

- [ ] 3.3.3 Implement capability filtering
  - Parameter: `?capability.max_latency_ms=<5000`
  - Filter: Agents meeting criteria

- [ ] 3.3.4 Implement trust level filtering
  - Parameter: `?trust_level=verified`
  - Filter: Only verified agents

- [ ] 3.3.5 Add sorting
  - Options: `registered_at`, `reputation`, `name`
  - Default: Reputation descending

- [ ] 3.3.6 Write tests
  - Test: Various query combinations
  - Test: Pagination works

- [ ] 3.3.7 Commit
  - Command: `git commit -m "feat(registry): add search and filtering"`

**Acceptance**: Search returns relevant agents

---

## Sprint T4: Registry Features

### Task 4.1: Reputation System

**Goal**: Basic reputation tracking

- [ ] 4.1.1 Create reputation module
  - File: `src/asap/registry/reputation.py`

- [ ] 4.1.2 Define ReputationScore model
  ```python
  class ReputationScore(BaseModel):
      agent_id: str
      score: float  # 0.0 - 5.0
      components: ReputationComponents
      updated_at: datetime
  
  class ReputationComponents(BaseModel):
      success_rate: float
      response_time: float
      sla_compliance: float
  ```

- [ ] 4.1.3 Implement GET /registry/agents/{id}/reputation
  - Return: Current reputation score
  - Components: Breakdown of score

- [ ] 4.1.4 Implement reputation update
  - POST event from interactions
  - Recalculate score

- [ ] 4.1.5 Add reputation to search results
  - Include: Score in agent listings
  - Sort: By reputation

- [ ] 4.1.6 Write tests
  - Test: Score calculation
  - Test: Updates affect score

- [ ] 4.1.7 Commit
  - Command: `git commit -m "feat(registry): add reputation system"`

**Acceptance**: Reputation scores available

---

### Task 4.2: Registry Client SDK

**Goal**: Python SDK for registry operations

- [ ] 4.2.1 Create client module
  - File: `src/asap/registry/client.py`

- [ ] 4.2.2 Implement RegistryClient
  ```python
  class RegistryClient:
      def register(self, signed_manifest) -> str:
          """Register an agent, return ID"""
      
      def search(self, skill=None, trust_level=None) -> List[AgentInfo]:
          """Search for agents"""
      
      def get_reputation(self, agent_id) -> ReputationScore:
          """Get agent reputation"""
  ```

- [ ] 4.2.3 Add automatic retry
  - Retry on 5xx errors
  - Exponential backoff

- [ ] 4.2.4 Add caching
  - Cache search results (short TTL)
  - Cache reputation (5 min)

- [ ] 4.2.5 Write tests
  - Test: All operations
  - Test: Retry logic

- [ ] 4.2.6 Commit
  - Command: `git commit -m "feat(registry): add client SDK"`

**Acceptance**: SDK simplifies registry access

---

### Task 4.3: Discovery Integration

**Goal**: Unified discovery (Registry + Well-known)

- [ ] 4.3.1 Update ASAPClient.discover()
  - Priority: Registry if configured
  - Fallback: Well-known URI (v1.1)

- [ ] 4.3.2 Add registry URL configuration
  - Config: `ASAP_REGISTRY_URL`
  - Default: None (use well-known)

- [ ] 4.3.3 Implement discovery chain
  ```python
  def discover(agent_id_or_url):
      if registry_configured:
          try:
              return registry.get(agent_id)
          except NotFound:
              pass
      return wellknown.discover(url)
  ```

- [ ] 4.3.4 Add discovery events
  - Emit: Discovery source (registry/wellknown)
  - Log: Discovery time

- [ ] 4.3.5 Write tests
  - Test: Registry preferred
  - Test: Fallback to well-known

- [ ] 4.3.6 Commit
  - Command: `git commit -m "feat(registry): integrate with discovery"`

**Acceptance**: Discovery uses registry when available

---

## Task 4.4: Mark Sprints T3-T4 Complete

- [ ] 4.4.1 Update roadmap progress
- [ ] 4.4.2 Document API reference

**Acceptance**: T3-T4 complete, ready for T5-T6

---

**T3-T4 Definition of Done**:
- [ ] Registry API functional
- [ ] Search and filtering working
- [ ] Reputation system basic
- [ ] Client SDK published
- [ ] Discovery integrated
- [ ] Test coverage >95%

**Total Sub-tasks**: ~35
