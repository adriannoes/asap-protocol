# ASAP Protocol: Product Strategy Decisions

> **Category**: Strategy & Roadmap
> **Focus**: Versioning, Evals, Marketplace, Design

---

## Question 6: Is CalVer Appropriate for Protocol Versioning?

### The Question
Section 9.3 proposes CalVer (2025.01 format). Is this suitable for a protocol spec?

### Analysis

**Versioning Strategies**:

| Strategy | Example | When to Use |
|----------|---------|-------------|
| **SemVer** | 1.2.3 | Breaking change clarity |
| **CalVer** | 2025.01 | Time-based releases |
| **Hybrid** | 1.2025.01 | Both dimensions |

**Industry Practice**:
- HTTP: Version numbers (1.0, 1.1, 2, 3)
- JSON-RPC: 2.0 (static for 15+ years)
- GraphQL: No versioning (evolved carefully)
- MCP: Date-based (2025-11-25)
- A2A: Semantic-ish (v1.0 DRAFT)
- A2A: Semantic-ish (v1.0 DRAFT)

### Expert Assessment

**CalVer advantages**:
- Communicates recency (2025.06 obviously newer than 2024.01)
- Encourages regular spec reviews
- Aligns with MCP's date-based approach

**CalVer disadvantages**:
- Doesn't communicate breaking vs non-breaking
- May create pressure for unnecessary annual changes
- Protocol users prefer stability signals

### Recommendation: **MODIFY**

Adopt **hybrid approach**: Major.CalVer

```
Format: <major>.<YYYY>.<MM>
Examples:
  1.2025.01 – Initial stable release
  1.2025.06 – Additive update
  2.2026.01 – Breaking changes
```

### Spec Amendment

> [!NOTE]
> Modified Section 9.3: Adopted hybrid versioning `Major.YYYY.MM`. Major version indicates breaking changes; CalVer portion indicates release timing. v1.2025.01 is target for first stable release.

---

## Question 10: Build vs Buy for Agent Evals?

### The Question
Should ASAP build a custom native evaluation framework or integrate with existing market solutions (DeepEval, Ragas, Arize)?

### Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **Build (Native)** | Total control, strict protocol alignment | High effort, reinventing LLM metrics wheel |
| **Buy/Integrate** | Immediate SOTA metrics, community maintenance | Dependency risk, "black box" logic |

### Expert Assessment

**Hybrid Strategy ("Shell vs Brain")**:
- **Protocol Compliance (Shell)**: MUST be native. We cannot rely on third parties to validate our specific binary formats, state transitions, or schemas.
- **Intelligence (Brain)**: SHOULD be delegated. Metrics like "Hallucination" or "Coherence" are commoditized and complex to maintain.

### Recommendation: **HYBRID**

Use **DeepEval** (Open Source) as the standard library for Intelligence Evals. Build a lightweight **ASAP Compliance Harness** using `pytest` for Protocol Evals.

### Spec Amendment

> [!NOTE]
> Added to Vision (Section 4): Adopted Hybrid Evaluation Strategy. Protocol Compliance is internal (Shell); Intelligence Evaluation is external via DeepEval (Brain).
>
> **Update (2026-02-12, Lean Marketplace Pivot)**: DeepEval integration deferred to v2.2+. v1.2 focuses exclusively on Protocol Compliance (Shell) using the ASAP Compliance Harness. See [../strategy/deferred-backlog.md](../strategy/deferred-backlog.md#2-deepeval-intelligence-layer-originally-v12-sprint-t61).

---

## Question 15: Lite Registry for v1.1 Discovery Gap

### The Question
v1.1 introduces agent identity (OAuth2) and direct discovery (`.well-known`), but defers the Registry API to v2.1. This creates a "Discovery Abyss" — agents have identity but no one can find them unless they already know the URL. How do we bridge this gap without building the full Registry early?

### Analysis

**The problem**: In v1.1, the network effect is zero. A developer can build and authenticate an agent, but there's no central place to list or discover agents. The "Marketplace" story feels hollow until v1.2.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Static JSON on GitHub Pages** | ✅ Selected | Zero infrastructure, PR-based social proof, machine-readable |
| DNS-based discovery | Rejected | Complex for developers, no browsing/search capability |
| Do nothing | Rejected | Kills early adoption momentum |

### Expert Assessment

A static `registry.json` hosted on GitHub Pages mirrors patterns that worked well in the Go ecosystem (before `proxy.golang.org`) and `awesome-*` lists. Developers submit agents via PR, creating community engagement and quality control through code review. The v2.1 Registry API can seed itself from this file when scale demands a backend.

**Critical refinement**: Since v1.1 introduces WebSocket alongside HTTP, agents may have multiple endpoints. The schema must support a `endpoints` dict (not a single `url` string).

### Decision

> [!IMPORTANT]
> **ADR-15**: Bridge the v1.1 "Discovery Abyss" with a **Static Lite Registry** — a `registry.json` file hosted on GitHub Pages. Agents are listed via PR. The SDK provides a `discover_from_registry(registry_url)` method.
>
> **Schema** (multi-endpoint):
> ```json
> {
>   "version": "1.0",
>   "updated_at": "2026-02-07T00:00:00Z",
>   "agents": [
>     {
>       "id": "urn:asap:agent:example",
>       "name": "Example Agent",
>       "description": "Code review and summarization agent",
>       "endpoints": {
>         "http": "https://agent.example.com/asap",
>         "ws": "wss://agent.example.com/asap/ws",
>         "manifest": "https://agent.example.com/.well-known/asap/manifest.json"
>       },
>       "skills": ["code_review", "summarization"],
>       "asap_version": "1.1.0"
>     }
>   ]
> }
> ```
>
> **Rationale**: Zero-cost infrastructure, creates early community engagement, and provides a migration path to the v2.1 Registry API Backend. Multi-endpoint schema supports HTTP + WebSocket transports introduced in v1.1.
>
> **Impact**: Added as Task in Sprint S2 (Well-Known Discovery). SDK method added to `ASAPClient`.
>
> **Update (2026-02-12, Lean Marketplace Pivot)**: Lite Registry continues as the primary data source through v2.0 (Web App reads from `registry.json`). Full Registry API Backend deferred to v2.1. The Lite Registry proved sufficient and reduces infrastructure complexity. See [../strategy/deferred-backlog.md](../strategy/deferred-backlog.md#1-registry-api-backend-originally-v12-sprints-t3t4).
>
> **Date**: 2026-02-07

---

## Question 18: Agent Registration — How Do Agents Get Listed?

### The Question
The Lean Marketplace (v2.0) Web App reads from the Lite Registry (`registry.json`), but registration still requires developers to manually create GitHub PRs. This creates friction: developers must know Git, format JSON correctly, and wait for PR review. If the marketplace is the "front door" for agents, shouldn't it handle registration end-to-end?

### Analysis

**The gap**: The marketplace is currently **read-only**. It can display agents but cannot register them. This transfers complexity to the developer and undermines the marketplace as the central hub.

**Options evaluated**:

| Option | Effort | DX | Infra Cost | Risk |
|--------|--------|-----|------------|------|
| **A. GitHub OAuth + API** (automated PR) | Low (1-2 days) | Good — form-based | Zero (uses GitHub as backend) | Low |
| B. Supabase/BaaS | Medium (3-5 days) | Good — form-based | Low ($) | Medium — new dependency |
| C. Vercel Edge Functions + DB | Medium (3-5 days) | Good — form-based | Low ($) | Medium — new infra |
| D. Manual PR (status quo) | Zero | Poor — requires Git knowledge | Zero | High — adoption friction |
| E. Full Registry API Backend | High (2+ weeks) | Best — full CRUD | Medium ($$) | Low — but overkill for MVP |

### Expert Assessment

**Option A is the sweet spot** for v2.0. It uses GitHub as a "free backend" while providing a polished developer experience:

1. Developer clicks "Register Agent" on the marketplace
2. Authenticates via GitHub OAuth (popup)
3. Fills out a form (name, endpoints, skills)
4. Marketplace validates the input (schema check, endpoint reachability)
5. Marketplace creates a PR via GitHub API on behalf of the developer
6. Developer never sees `registry.json` or writes JSON manually

This pattern is well-established — Homebrew (`brew tap`), Terraform Registry, and VS Code Marketplace all use similar GitHub-backed submission flows.

### Decision

> [!IMPORTANT]
> **ADR-18**: Agent registration in the v2.0 marketplace uses **GitHub OAuth + automated PR creation**. The developer authenticates with GitHub, fills a form, and the marketplace creates the PR automatically. **Mandatory review** is required before merge — a maintainer must approve each registration.
>
> **Merge strategy**: Start with **mandatory review** to maintain quality control during early growth. Evolve to **hybrid auto-merge** when the compliance harness (v1.2) can validate agents automatically:
>
> | Phase | Merge Policy | When |
> |-------|-------------|------|
> | v2.0 Launch | **Mandatory review** — maintainer approves each PR | Day 1 |
> | v2.0+ (hybrid) | **Auto-merge** if agent passes automated validation (schema, health, compliance); **manual review** if validation fails | When compliance harness is integrated with CI |
>
> **Why not auto-merge from day one?**
> - Compliance Harness (v1.2) won't be integrated into the registration CI pipeline at launch
> - Manual review prevents spam, malicious endpoints, and low-quality listings
> - At early scale (< 100 agents), review is manageable
>
> **What the developer sees**:
> ```
> Register Agent → GitHub Login → Fill Form → "Submitted! ✅"
>                                                └→ Under review (typically < 24h)
> ```
>
> **What happens behind the scenes**:
> ```
> Marketplace → Forks repo (if needed) → Updates registry.json
>            → Creates PR via GitHub API → Maintainer reviews → Merge → Agent listed
> ```
>
> **Migration to hybrid**: When compliance harness CI is ready, add a GitHub Action that runs validation on the PR. If all checks pass, auto-merge via `@dependabot merge` pattern. If checks fail, flag for manual review.
>
> **Rationale**: Zero additional infrastructure, leverages existing GitHub ecosystem (OAuth, API, Actions), provides audit trail via PR history, and the marketplace becomes the true "front door" for agent registration.
>
> **Impact**: Added as tasks in v2.0 Sprint M3 (Web App). GitHub OAuth setup + registration form + PR automation.
>
> **Date**: 2026-02-12
>
> **Update (2026-02-16)**: Refined to **IssueOps** pattern. Instead of a direct PR, the Web App submits a **GitHub Issue** (via URL or API). A GitHub Action then triggers to validate and create the commit/PR. This allows for better error feedback (comments on Issue) and leveraging GitHub's native governance tools.


---

## Question 19: Design Strategy — How to Guarantee a Premium UX?

### The Question
The system prompt explicitly requires the marketplace to "WOW the user" and feel "extremely premium". However, the project is currently engineering-led. Without a specific strategy, the UI risks becoming functional but generic ("engineer-art").

### Analysis

**The Risk**: Jumping straight to code results in:
-   Inconsistent layouts
-   Poor visual hierarchy
-   Lack of "delight" (micro-interactions)
-   Refactoring loops when the UI feels "off"

**Options**:
A. **Code-First**: Build components on the fly. (Fastest start, poorest result)
B. **Design-First**: Mandatory wireframes and high-fidelity mockups before coding. (Slower start, better result)

### Expert Assessment
For a marketplace, **trust is visual**. A sloppy or generic UI suggests low-quality agents. Therefore, design is not just aesthetics; it is a core functional requirement for trust.

### Decision

> [!IMPORTANT]
> **ADR-19**: The Marketplace (v2.0) adopts a **Design-First Workflow**. Frontend implementation **cannot begin** until high-fidelity mockups are approved for that feature.
>
> **Workflow**:
> 1. **Wireframes** (Excalidraw): Map the user journey and information architecture.
> 2. **Mockups** (Figma/V0): Define visual hierarchy, spacing, and "premium" details.
> 3. **Implementation** (Code): Translate approved designs to Shadcn/Tailwind.
>
> **Rationale**: Prevents low-quality UI, reduces churn during implementation, and ensures the "premium" requirement is met.
>
> **Impact**: Added "Design Phase" tasks to v2.0 Sprint M1.
>
> **Date**: 2026-02-12

---

## Question 21: Pricing Strategy — Free vs Paid at Launch?

### The Question
Should the v2.0 Marketplace launch with a revenue model (Verified Badge = $49/mo) or as a free ecosystem?

### Analysis

**The Goal**: Maximize agent adoption and directory growth.

**Options**:
1.  **Paid Verified Badge ($49/mo)**: Generates immediate revenue but creates friction. Requires Stripe integration, tax compliance, and support.
2.  **Free Verified Badge**: Trust is awarded based on merit/security, not payment. Higher operational load (manual review) but zero friction for developers.

### Expert Assessment

**Adoption is the scarcity** in a new two-sided marketplace. Charging for the "Verified" status early on penalizes early adopters who add value to the network.
Furthermore, integrating payments (Stripe) adds significant scope (webhooks, subscriptions, tax handling) to the MVP, delaying launch.

### Decision

> [!IMPORTANT]
> **ADR-21**: The v2.0 Marketplace launches with a **Free** pricing model.
>
> 1.  **Stripe Removed**: Payment processing logic (Sprint M3) is removed from v2.0 scope.
> 2.  **Verified Badge**: Retained as a trust signal, but awarded via **Usage-Based Merit** and **Manual Review** (IssueOps). It is not purchasable.
> 3.  **Monetization**: Deferred to v3.0 (when the network effect is established).
>
> **Rationale**: Prioritizes adoption and reduces MVP complexity ("Lean Marketplace").
>
> **Date**: 2026-02-16
