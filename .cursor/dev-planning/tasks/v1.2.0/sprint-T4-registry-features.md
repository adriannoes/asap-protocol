# Sprint T4: Registry Features

> **Goal**: Advanced registry features and client SDK
> **Prerequisites**: Sprint T3 completed (Registry Core)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `src/asap/registry/reputation.py` - Reputation system
- `src/asap/registry/client.py` - Client SDK
- `src/asap/transport/client.py` - Discovery integration
- `tests/registry/test_reputation.py` - Reputation tests
- `tests/registry/test_client.py` - Client SDK tests

---

## Context

This sprint adds advanced features to the registry: reputation tracking for agent quality and a client SDK for easy integration.

---

## Task 4.1: Reputation System

**Goal**: Basic reputation tracking

**Prerequisites**: Sprint T3 completed

### Sub-tasks

- [ ] 4.1.1 Create reputation module
  - **File**: `src/asap/registry/reputation.py`

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
  - **Return**: Current reputation score
  - **Components**: Breakdown of score

- [ ] 4.1.4 Implement reputation update
  - POST event from interactions
  - Recalculate score

- [ ] 4.1.5 Add reputation to search results
  - **Include**: Score in agent listings
  - **Sort**: By reputation

- [ ] 4.1.6 Write tests
  - Test: Score calculation
  - Test: Updates affect score

- [ ] 4.1.7 Commit
  - **Command**: `git commit -m "feat(registry): add reputation system"`

**Acceptance Criteria**:
- [ ] Reputation scores available
- [ ] Scores affect search ranking

---

## Task 4.2: Registry Client SDK

**Goal**: Python SDK for registry operations

### Sub-tasks

- [ ] 4.2.1 Create client module
  - **File**: `src/asap/registry/client.py`

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
  - **Command**: `git commit -m "feat(registry): add client SDK"`

**Acceptance Criteria**:
- [ ] SDK simplifies registry access
- [ ] Retry and caching work

---

## Task 4.3: Discovery Integration

**Goal**: Unified discovery (Registry + Well-known)

### Sub-tasks

- [ ] 4.3.1 Update ASAPClient.discover()
  - **Priority**: Registry if configured
  - **Fallback**: Well-known URI (v1.1)

- [ ] 4.3.2 Add registry URL configuration
  - **Config**: `ASAP_REGISTRY_URL`
  - **Default**: None (use well-known)

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
  - **Emit**: Discovery source (registry/wellknown)
  - **Log**: Discovery time

- [ ] 4.3.5 Write tests
  - Test: Registry preferred
  - Test: Fallback to well-known

- [ ] 4.3.6 Commit
  - **Command**: `git commit -m "feat(registry): integrate with discovery"`

**Acceptance Criteria**:
- [ ] Discovery uses registry when available
- [ ] Fallback works correctly

---

## Task 4.4: Mark Sprint T4 Complete

### Sub-tasks

- [ ] 4.4.1 Update roadmap progress
- [ ] 4.4.2 Document API reference

**Acceptance Criteria**:
- [ ] T3-T4 complete, ready for T5-T6

---

## Sprint T4 Definition of Done

- [ ] Reputation system basic
- [ ] Client SDK published
- [ ] Discovery integrated
- [ ] Test coverage >95%

**Total Sub-tasks**: ~17
