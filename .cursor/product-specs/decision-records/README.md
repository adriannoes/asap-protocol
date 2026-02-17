# ASAP Protocol: Decision Records (ADR) Index

> **Status**: Living Documentation

This directory contains the Architectural Decision Records (ADR) for the ASAP Protocol. These documents capture critical design choices, trade-offs, and rationale.

## Categories

### [01-architecture.md](./01-architecture.md)
Core architectural patterns and structural decisions.
- **Q1**: State Persistence (Event Sourcing vs Snapshots)
- **Q3**: Network Topology (P2P vs Client-Server)
- **Q4**: Consistency Models (Causal vs Eventual)
- **Q13**: State Management Strategy (Hybrid)
- **Q14**: Agent Liveness Protocol (Health Checks)

### [02-protocol.md](./02-protocol.md)
Wire protocol details, message formats, and transport behavior.
- **Q2**: Transport Binding (JSON-RPC)
- **Q5**: Integration Pattern (Envelope)
- **Q7**: Error Taxonomy
- **Q16**: WebSocket Reliability (Message Acks)

### [03-security.md](./03-security.md)
Authentication, identity verification, and threat mitigation.
- **Q8**: MVP Security Model
- **Q17**: Trust Model (OAuth2 vs Identity)
- **Q20**: Security Hardening (Ed25519 + JCS)

### [04-technology.md](./04-technology.md)
Implementation choices, libraries, and tech stack.
- **Q9**: Implementation Language (Python)
- **Q11**: Web App Stack (Next.js)
- **Q12**: OAuth Library Selection (Authlib)

### [05-product-strategy.md](./05-product-strategy.md)
Product roadmap, feature prioritization, and ecosystem strategy.
- **Q6**: Versioning Strategy (CalVer)
- **Q10**: Evaluation Strategy (Shell vs Brain)
- **Q15**: Lite Registry (Discovery Gap)
- **Q18**: Agent Registration Flow (GitHub PRs)
- **Q19**: Design Strategy (Design-First)
- **Q21**: Pricing Strategy (Free vs Paid)

### Planning Documents (dev-planning/)

- **[v2.0-marketplace-usage-foundation.md](../../dev-planning/tasks/v2.0.0/v2.0-marketplace-usage-foundation.md)** — Usage storage (local vs central), control model, evolution path to marketplace. Reference when building v2.0 central dashboard.

---

## Contributing
To add a new decision:
1. Create a new file or append to the appropriate category.
2. Follow the standard ADR format: Question > Analysis > Expert Assessment > decision.
3. Update this index.
