# Sprint M1: Production Registry

> **Goal**: Deploy production-grade Registry service
> **Prerequisites**: v1.3.0 completed
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `src/asap/registry/models.py` - Database models
- `src/asap/registry/routes.py` - API endpoints
- `alembic/` - Database migrations
- `Dockerfile` - Production container

---

## Context

This sprint upgrades the Registry from a dev-only service to a production-grade component with PostgreSQL, proper indexing, and trust scoring.

---

## Task 1.1: Production Database

### Sub-tasks

- [ ] 1.1.1 Design PostgreSQL schema
  - agents, manifests, trust_scores, reputation

- [ ] 1.1.2 Create migrations
  - Using Alembic or similar

- [ ] 1.1.3 Set up connection pooling
  - asyncpg with pool

- [ ] 1.1.4 Implement backup strategy

- [ ] 1.1.5 Write tests

**Acceptance Criteria**:
- [ ] Schema deployed and verified
- [ ] Tests pass with Postgres

---

## Task 1.2: Registry Deployment

### Sub-tasks

- [ ] 1.2.1 Create production Dockerfile

- [ ] 1.2.2 Configure Railway/Fly.io

- [ ] 1.2.3 Set up environment variables

- [ ] 1.2.4 Configure auto-scaling

- [ ] 1.2.5 Add health endpoints

**Acceptance Criteria**:
- [ ] Service healthy in production

---

## Task 1.3: Trust Score Integration

### Sub-tasks

- [ ] 1.3.1 Connect to Trust service

- [ ] 1.3.2 Compute scores on registration

- [ ] 1.3.3 Update scores periodically

- [ ] 1.3.4 Display in API responses

**Acceptance Criteria**:
- [ ] Agents have trust scores

---

## Task 1.4: Full-Text Search

### Sub-tasks

- [ ] 1.4.1 Add PostgreSQL tsvector columns

- [ ] 1.4.2 Create search indexes

- [ ] 1.4.3 Implement search endpoint

- [ ] 1.4.4 Add relevance ranking

**Acceptance Criteria**:
- [ ] Search returns relevant results

---

## Sprint M1 Definition of Done

- [ ] Registry production-ready
- [ ] Database backups configured
- [ ] Trust scores operational
- [ ] Full-text search working

**Total Sub-tasks**: ~18
