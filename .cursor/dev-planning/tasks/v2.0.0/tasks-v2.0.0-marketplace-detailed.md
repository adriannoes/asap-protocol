# Tasks: ASAP v2.0.0 Marketplace Core (M1-M2) - Detailed

> **Sprints**: M1-M2 - Production Registry and Service Integration
> **Goal**: Production-ready marketplace backend

---

## Sprint M1: Production Registry

### Task 1.1: Production Database

- [ ] 1.1.1 Design PostgreSQL schema
  - agents, manifests, trust_scores, reputation

- [ ] 1.1.2 Create migrations
  - Using Alembic or similar

- [ ] 1.1.3 Set up connection pooling
  - asyncpg with pool

- [ ] 1.1.4 Implement backup strategy

- [ ] 1.1.5 Write tests

---

### Task 1.2: Registry Deployment

- [ ] 1.2.1 Create production Dockerfile

- [ ] 1.2.2 Configure Railway/Fly.io

- [ ] 1.2.3 Set up environment variables

- [ ] 1.2.4 Configure auto-scaling

- [ ] 1.2.5 Add health endpoints

---

### Task 1.3: Trust Score Integration

- [ ] 1.3.1 Connect to Trust service

- [ ] 1.3.2 Compute scores on registration

- [ ] 1.3.3 Update scores periodically

- [ ] 1.3.4 Display in API responses

---

### Task 1.4: Full-Text Search

- [ ] 1.4.1 Add PostgreSQL tsvector columns

- [ ] 1.4.2 Create search indexes

- [ ] 1.4.3 Implement search endpoint

- [ ] 1.4.4 Add relevance ranking

---

## Sprint M2: Service Integration

### Task 2.1: OAuth2 Integration

- [ ] 2.1.1 Add OAuth2 middleware to Registry

- [ ] 2.1.2 Protect mutation endpoints

- [ ] 2.1.3 Allow public reads

- [ ] 2.1.4 Test token validation

---

### Task 2.2: Metering Integration

- [ ] 2.2.1 Track Registry API calls

- [ ] 2.2.2 Connect to Metering service

- [ ] 2.2.3 Emit usage events

---

### Task 2.3: SLA Integration

- [ ] 2.3.1 Include SLA in agent responses

- [ ] 2.3.2 Add SLA filter to search

- [ ] 2.3.3 Display compliance status

---

### Task 2.4: Audit Integration

- [ ] 2.4.1 Log registrations

- [ ] 2.4.2 Log updates

- [ ] 2.4.3 Log deletions

- [ ] 2.4.4 Test audit trail

---

**M1-M2 Definition of Done**:
- [ ] Registry production-ready
- [ ] All services integrated
- [ ] Load test passes

**Total Sub-tasks**: ~35
