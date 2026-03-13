# ASAP Protocol: Decision Records (ADR) Index

> **Status**: Living Documentation
>
> **Unified Index**: See [ADR-INDEX.md](./ADR-INDEX.md) for a single reference mapping both ADR collections (`docs/adr/` and this directory) and clarifying numbering collisions.

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
- **Q23**: Mypy Strategy (src, scripts, tests)
- **Q25**: SDK Cache Strategy (bilateral — registry 5min / revocation no-cache) — ADR-25

### [05-product-strategy.md](./05-product-strategy.md)
Product roadmap, feature prioritization, and ecosystem strategy.
- **Q6**: Versioning Strategy (CalVer)
- **Q10**: Evaluation Strategy (Shell vs Brain)
- **Q15**: Lite Registry (Discovery Gap)
- **Q18**: Agent Registration Flow (GitHub PRs)
- **Q19**: Design Strategy (Design-First)
- **Q21**: Pricing Strategy (Free vs Paid)
- **Q22**: Register-Agent Template and Registry Metadata (Trust, Discovery, “Other Platforms”)
- **Q24**: `asap-mcp-server` — Python (pip) vs TypeScript (npm) — ADR-24
- **Q26**: Cross-Platform Domain & Branding Strategy (ASAP Protocol + Agent Builder) — ADR-26

### Planning Documents (dev-planning/ and prd/)

- **[v2.0-marketplace-usage-foundation.md](../../dev-planning/tasks/v2.0.0/v2.0-marketplace-usage-foundation.md)** — Usage storage (local vs central), control model, evolution path to marketplace. Reference when building v2.0 central dashboard.
- **[prd-v2.1-ecosystem.md](../prd/prd-v2.1-ecosystem.md)** — Consumer SDK, LangChain/CrewAI/MCP integrations, Category/Tags, Revocation, PyPI. Tasks: [tasks-v2.1.0-roadmap.md](../../dev-planning/tasks/v2.1.0/tasks-v2.1.0-roadmap.md).
- **[prd-v2.2-scale.md](../prd/prd-v2.2-scale.md)** — Registry API Backend, Auto-Registration, Audit Logging, DeepEval.
- **[prd-cross-platform-integration-asap.md](../prd/prd-cross-platform-integration-asap.md)** — Cross-platform integration (ASAP Protocol side). Agent Builder link, SSO, Dashboard card.
- **[prd-cross-platform-integration-agentic.md](../prd/prd-cross-platform-integration-agentic.md)** — Cross-platform integration (Agent Builder side). Registry replacement, back-navigation, design unification.
- **[prd-v3.0-economy.md](../prd/prd-v3.0-economy.md)** — Economy Settlement, Stripe, Credits, Clearing House, ASAP Cloud.

---

## Contributing
To add a new decision:
1. Create a new file or append to the appropriate category.
2. Follow the standard ADR format: Question > Analysis > Expert Assessment > decision.
3. Update this index.
