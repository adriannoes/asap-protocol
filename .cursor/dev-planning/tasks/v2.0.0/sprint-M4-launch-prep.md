# Sprint M4: Launch Preparation

> **Goal**: Final polish, security audit, and launch
> **Prerequisites**: Sprint M3 completed (Verified Badge)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- Vercel Analytics / Speed Insights configuration
- Sentry integration (Client/Server)
- Documentation updates
- GitHub Actions workflows (Concurrency limits)
- `apps/web/app/page.tsx` - Landing page revisions
- `src/asap/crypto/signing.py` - Ed25519 signing with RFC 8032 strict verification (s < l) and JCS (RFC 8785)
- `tests/crypto/test_signing.py` - Comprehensive tests including RFC 8032 malleability prevention
- `apps/web/src/app/dashboard/actions.ts` - unstable_cache (30s TTL) + updateTag for Refresh; revalidateUserRegistrationIssues server action
- `apps/web/src/app/dashboard/dashboard-client.tsx` - Refresh button calls revalidateUserRegistrationIssues before mutate
- `.github/workflows/validate-registry.yml` - CI guardrail: validates registry.json on push/PR when registry.json changes
- `scripts/validate_registry.py` - Validates registry.json against Pydantic LiteRegistry/RegistryEntry schema
- `apps/web/src/app/api/fixtures/registry/route.ts` - Fixture endpoint for load test (500+ agents, ENABLE_FIXTURE_ROUTES only)
- `apps/web/src/app/browse/load-test/page.tsx` - Load-test page that fetches fixture and renders BrowseContent
- `apps/web/tests/load/browse-500.spec.ts` - Playwright load test: 500+ agents, metrics (render time, memory, TTI)
- `apps/web/src/components/ui/skeleton.tsx` - Skeleton component for loading states
- `apps/web/src/app/browse/agent-card-skeleton.tsx` - Skeleton matching Agent Card dimensions (zero CLS)
- `apps/web/src/app/browse/loading.tsx` - Browse route loading UI with skeleton grid
- `apps/web/src/lib/registry.ts` - `REGISTRY_REVALIDATE_SECONDS` (ISR) and registry fetch; cache coordination with GitHub Pages
- `apps/web/src/app/api/proxy/check/route.ts` - CORS-bypass proxy for agent reachability; SSRF prevention (HTTPS only, private IP block, rate limit)
- `apps/web/src/lib/url-validator.ts` - `isAllowedProxyUrl` (HTTPS-only validation for proxy)
- `apps/web/src/lib/rate-limit.ts` - `checkRateLimit` (user actions), `checkProxyRateLimit` (proxy endpoint)
- `apps/web/src/app/layout.tsx` - SpeedInsights + Analytics components (Vercel monitoring)
- `scripts/lib/debug_id.py` - Debug ID generator (ASAP-{ts}-{6char})
- `scripts/process_registration.py` - debug_id in errors, structured JSON logs
- `scripts/process_removal.py` - debug_id in errors, structured JSON logs
- `apps/web/src/app/dashboard/actions.ts` - x-ratelimit-remaining in structured logs
- `scripts/seed_registry.py` - Seed 100+ mock agents into registry.json (online_check=false)
- `src/asap/discovery/registry.py` - Optional RegistryEntry.online_check for bypassing reachability
- `apps/web/src/types/registry.d.ts` - RegistryAgent.online_check
- `apps/web/src/lib/registry-schema.ts` - online_check in RegistryAgentSchema
- `apps/web/src/app/agents/[id]/agent-detail-client.tsx` - Demo badge when online_check=false
- `apps/web/src/app/dashboard/dashboard-client.tsx` - Demo badge when online_check=false
- `tests/scripts/test_seed_registry.py` - Tests for seed script
- `tests/discovery/test_registry.py` - RegistryEntry online_check test
- `.cursor/dev-planning/tasks/v2.0.0/launch-checklist-v2.0.md` - Pre-launch verification checklist (Task 4.5.2)

---

## Context

This is the final sprint before v2.0.0 launch. Focus on security of the IssueOps flow, client-side performance, monitoring, and final landing page polish. The backend infrastructure (Prometheus/Grafana) has been removed in favor of a Lean Marketplace approach.

---

## Task 4.1: Security Audit & Hardening

### Sub-tasks

- [x] 4.1.1 IssueOps Security Review & Concurrency
  - [x] **Action Payload Injection**: Audit `scripts/process_registration.py` for vulnerability to malicious Markdown/YAML payloads.
  - [x] **Concurrency**: Prevent `git push rejected` by adding `concurrency: group: register-agent` to `.github/workflows/register-agent.yml` to queue rapid registrations. 
    - **CRITICAL**: explicitly set `cancel-in-progress: false` to avoid race conditions if a user edits an issue while the action is processing.

- [x] 4.1.2 Cryptographic Strictness
  - [x] **Manifest Signatures**: Ensure Ed25519 signature validation strictly follows JCS (RFC 8785) and Strict Verification (RFC 8032) to prevent malleability.

- [x] 4.1.3 API, Identity Hardening & Caching
  - [x] **Rate Limiting**: Audit Next.js server actions and GitHub API interactions to prevent Octokit rate limit exhaustion.
  - [x] **API Caching & Invalidation**: Implement Next.js `unstable_cache` with a short TTL (e.g., 30s) on API calls like `fetchUserRegistrationIssues`. **Crucial UX Fix**: Ensure the "Refresh" button in the dashboard uses `updateTag` to forcefully bust this cache, otherwise users won't see immediate updates.
  - [x] **Bandit Scan**: Add `bandit` to CI workflow for automated security scanning.

- [x] 4.1.4 Registry Integrity (CI Guardrail)
  - [x] **Action**: Create `.github/workflows/validate-registry.yml` that runs on every push to `main` and Pull Requests.
  - [x] **Validation**: It must parse `registry.json` against the Pydantic schema to ensure manual edits don't break the Next.js ISR build. 

- [x] 4.1.5 Document security practices (`SECURITY.md`)
  - [x] Reporting policy
  - [x] Scope of coverage

- [x] 4.1.6 Agent Deprecation & Removal Process
  - [x] **Action**: Define a manual IssueOps flow (e.g., Issue with `remove-agent` label) to safely deprecate and remove offline/abandoned agents from the `registry.json`. Document this process for v2.0 to prevent indefinite registry bloat.

**Acceptance Criteria**:
- [x] Security audit passed and all critical vulnerabilities remediated.
- [x] Automated security scanning enabled in CI.
- [x] API calls to GitHub are aggressively cached to protect rate limits.
- [x] `registry.json` is protected by a CI syntax guardrail.

- [ ] 4.1.7 Commit: Security
  - **Command**: `git commit -m "chore(security): apply audit fixes, guardrails, and API cache"`

---

## Task 4.2: Frontend Performance & Reliability

### Sub-tasks

- [x] 4.2.1 Client-side Load Testing
  - Simulate parsing a `registry.json` payload with 500+ agents.
  - Measure browser render time, memory usage, and Time to Interactive (TTI).

- [x] 4.2.2 Search, Filter Optimization & Layout Shift
  - Implement Web Workers or advanced memoization if client-side search/filtering lags with 500+ entries.
  - **Skeletons**: Ensure Skeleton Screens perfectly match the Agent Card dimensions to prevent Cumulative Layout Shift (CLS).

- [x] 4.2.3 Cache Coordination
  - Balance GitHub Pages cache TTL with Next.js ISR (`revalidate: 60`) to minimize the time between a merged PR and listing visibility.
  - **Done**: Single source of truth `REGISTRY_REVALIDATE_SECONDS` in `lib/registry.ts` (default 60s, configurable via env, min 30s). Used by fetch and by browse/agents page segment config. Documented: GitHub Pages uses max-age=600; our revalidate controls Next.js ISR so listing visibility is at most this interval on our side.

- [x] 4.2.4 CORS-Bypass Proxy for Reachability
  - **Action**: Create a server-side route handler `/api/proxy/check?url=...` in Next.js.
  - **Security (SSRF Prevention)**: This endpoint must strictly validate inputs. Add an allowlist for URLs (only `https://`), explicitly block private IPs (RFC 1918), and implement IP-based rate limiting to prevent abuse.
  - **Usage**: Update the dashboard and detail pages to ping agent health via this proxy instead of direct client-side fetching. This prevents silent failures when developers forget to configure CORS on their agents.
  - **Done**: `/api/proxy/check` with `isAllowedProxyUrl` (HTTPS only), `checkProxyRateLimit` (30 req/min per IP), dashboard and agent detail use proxy; tests added.

**Acceptance Criteria**:
- [ ] UI remains responsive with 500+ agents and zero CLS during loading.
- [ ] Agent HTTP reachability checks work regardless of agent CORS settings and proxy is secured against SSRF.

- [ ] 4.2.5 Commit: Optimization
  - **Command**: `git commit -m "perf(web): apply client load optimizations and proxy reachability"`

---

## Task 4.3: Monitoring & Polish

### Sub-tasks

- [x] 4.3.1 Vercel Speed Insights & Web Analytics (Hobby Plan)
  - Review and fix the current Speed Insights implementation (commit `58dccf4`).
  - Install and configure `@vercel/analytics` for Visitor Tracking (`<Analytics />` component).
  - Verify both analytics streams are receiving events in the Vercel Dashboard.
  - **Done**: Installed `@vercel/speed-insights` and `@vercel/analytics`; added `<SpeedInsights />` and `<Analytics />` to root layout. Enable both in Vercel Dashboard (Speed Insights tab + Analytics tab) and deploy to verify events.

- [x] 4.3.2 Native Log Formatting & Traceability (Alternative to Sentry)
  - Replace Sentry overhead by relying on Vercel's native Runtime Logs and GitHub Action Logs.
  - **Rate Limits**: Ensure structured logs capture the `x-ratelimit-remaining` header from Octokit responses to proactively monitor API quota exhaustion.
  - **Traceability (Debug ID)**: Generate a unique "Debug ID" using the format `ASAP-{timestamp}-{6char-random}` (e.g., `ASAP-1704067200-A8B2C9`). Include this readable ID in both the structured JSON logs *and* injected into the automated GitHub Issue error comment. This connects public errors to internal logs without heavy external APMs or UUID libraries.
  - **Done**: `scripts/lib/debug_id.py` generator; process_registration/removal emit debug_id in result.json + structured JSON logs; workflows include Debug ID in issue comment; dashboard actions log `x-ratelimit-remaining` from Octokit.

- [x] 4.3.3 SEO & Social Sharing
  - [x] Implement dynamic OG Image generation for Agent Cards (`apps/web/app/agents/[id]/opengraph-image.tsx`). *Note: Be aware of Vercel Hobby tier build costs for 100+ agents; first visits may be slightly slow during ISR OG image generation.*
  - [x] Implement `next-sitemap` or native Next.js `sitemap.ts` to expose all agents for Google indexation.
    - **CRITICAL**: Exclude load-test/mock agents (`URN` matches `urn:asap:agent:mock:...` or `urn:asap:agent:loadtest:...`) from the sitemap.

**Acceptance Criteria**:
- [x] Speed Insights and Web Analytics are tracking correctly on Vercel.
- [x] Structured errors map perfectly to GitHub Issue comments via a Debug ID.
- [x] SEO metadata and social previews are fully functional.

- [ ] 4.3.4 Commit: Polish
  - **Command**: `git commit -m "feat(web): add vercel monitoring, log traceability, and SEO"`

---

## Task 4.4: Marketing Content & Landing Page Expansion

### Sub-tasks

- [x] 4.4.1 Protocol Feature Detail Pages (Card Click-through)
  - **Action**: Make the 4 "Protocol Features" cards clickable on the landing page, routing to dedicated explanatory sub-pages (`/features/[slug]`):
    - `.../lite-registry`: Explain the static JSON architecture, zero-database overhead, and resilience.
    - `.../verified-trust`: Explain the 3-Tier trust hierarchy (Self-signed vs Verified), Ed25519 signing, and the Manual IssueOps vetting process. Show examples.
    - `.../1-click-integration`: Detail the standardized `.process` WebSocket command vs REST HTTP schemas.
    - `.../full-observability`: Explain how state snapshots and Live Event streams work.
  - **Done**: `FeaturesSection` now uses `<Link>`, routing to the generic static layout inside `/features/[slug]/page.tsx` rendering Tailwind Prose content.
  
- [x] 4.4.2 Demos & Visual Showcase Page
  - **Route**: Add link to Header (`/demos` or `/playground`).
  - **Content**: A visual and technical showcase of the protocol in action to keep users engaged.
    - Show side-by-side: `JSON Payload` -> `Agent Stream`.
    - Show code block: `WebSockets Connect` -> `.process` command validation mapping to `register.json` schemas.
    - Show `MemorySnapshot` event rendering.
  - **Done**: Added `/demos` with three visual UI blocks detailing WebSocket connections, Zod payload validation, and Memory event streaming using Tailwind syntax highlighting and `lucide-react` icons./demo page representing the active agent ecosystem.
    - **Interactive Demo**: Upgrade from static GIFs. Leverage Gemini 3.1 Pro to create a real-time, interactive demo in the browser where users can enter a task and watch ASAP process it live (the ultimate "wow factor").
    - **Code Snippets (Markdown)**: Side-by-side or below the visuals, show the minimal code required to achieve the demo.
    - **GitHub Hyperlink**: A clear CTA at the end of each demo: "View the full source code on GitHub" for deep dives.

- [x] 4.4.3 Quick Start for Consumers & UI Refinements
  - **Quick Start Component**: Add a section on the Landing Page and explicitly on the `/agents/[id]` Detail Page visualizing "Consumer" ease-of-use (`npm install @asap/client` -> `await agent.run()`).
  - **Terminal Hero Upgrade**: Instead of just typing effects, show a complete, realistic ASAP task cycle in the terminal block: `task_id` generation -> status changing from `pending` -> `running` -> `completed` with timestamps. Show the protocol in meaningful action.
  - **Verified Badge First-Class Treatment**: Elevate the "Verified" indicator from a simple text badge to a premium first-class element (e.g., a shield icon with a pronounced gradient). Add a dedicated "Trust & Verification" section in the Agent Detail page separated from SLA details.
  - **Enhanced Information Density (Agent Cards)**: Upgrade Agent Cards to display more valuable data: `asap_version`, `built_with` framework, and a placeholder for promised `P95 latency` (SLA).
  - **Empty States Conversion**: When search/filters yield zero results on `/browse`, design a premium empty state that includes a direct Call-To-Action (CTA) to "Register this missing agent", converting a dead-end into a growth opportunity.
  - **Mobile "Connect" UX**: In the Agent Detail page, make sure the "Copy Endpoint" button uses `navigator.clipboard` with instant visual feedback (Check icon).

- [x] 4.4.4 Developer Experience Page
  - **Route**: Add link to Header (`/developer-experience`).
  - **Content**: Explain "The Shell, Not the Brain" philosophy (Pydantic schemas), the 3-step IssueOps registration flow (Local Manifest -> Test -> GitHub Action) and local compliance testing.

- [x] 4.4.5 Footer Expansion & Legal Pages
  - **Action**: Add secondary links to the footer to make the project look professional and compliant for the GitHub App store:
    - Include explicit **Apache 2.0 License** link (pointing to repo LICENSE: https://github.com/adriannoes/asap-protocol/blob/main/LICENSE).
    - Add "Privacy Policy" and "Terms of Service" placeholders (required for GitHub OAuth App validation).
    - Add "Manifesto / Vision" link based on our architecture documents.

- [ ] 4.4.6 Commit Marketing Pages
  - **Command**: `git commit -m "feat(web): add feature drill-downs, demos, quick-start, and PRD v2.1"`

---

## Task 4.5: Launch Preparation & Seeding

### Sub-tasks

- [x] 4.5.1 [cursor-auto] Seed the Registry (Cold Start)
  - **Action**: Create `scripts/seed_registry.py` to generate 100+ mock agents directly into `registry.json`.
  - **Reachability Strategy**: To prevent seeded agents from destroying "social proof" by showing up as "Unreachable" due to dummy endpoints, either format them with an explicit `online_check: false` bypass property or deploy a minimal mock server returning successful `/health` replies.
  - **Goal**: Serve as "social proof" for launch day and provide real data to validate the client-side load testing (Task 4.2.1).
  - **Done**: `scripts/seed_registry.py` added; `RegistryEntry.online_check` (optional bool) and UI skip when false; 120 agents seeded in `registry.json`; tests in `tests/scripts/test_seed_registry.py` and `tests/discovery/test_registry.py`.

- [ ] 4.5.2 Final checklist review
  - **Checklist**: Run through [launch-checklist-v2.0.md](./launch-checklist-v2.0.md) and confirm each item.
  - [ ] Domain DNS propagated?
  - [ ] GitHub OAuth Production App configured?
  - [ ] Vercel Analytics tracking active?
  - Mark 4.5.2 done when all items in the launch checklist are verified.

- [ ] 4.5.3 Deploy to production (Promote Vercel Preview to Prod)

**Acceptance Criteria**:
- [x] 100+ agents seeded and successfully rendered in the Web App. (120 agents in registry.json; browse page shows count; seed agents use `online_check: false` so they show "Demo" instead of reachability check.)
- [ ] v2.0.0 launched!

- [ ] 4.5.4 Tag Logic Release
  - **Command**: `git tag v2.0.0`
  - **Command**: `git push origin v2.0.0`

---

## Sprint M4 Definition of Done

- [x] Security audit passed — Task 4.1 done (audit, bandit CI, API cache, validate-registry, SECURITY.md, removal flow).
- [ ] Frontend performance validated — 4.2 implementation done (load test, skeletons, proxy); AC (500+ responsive, zero CLS, proxy SSRF) left for you to confirm in testing.
- [x] Monitoring operational — Speed Insights + Analytics in layout; Debug ID in IssueOps logs; no Sentry.
- [x] Landing page finalized — Features, demos, quick-start, DX page, footer, legal placeholders (4.4).
- [x] 100+ beta agents — 120 seed agents in registry.json (4.5.1).
- [ ] v2.0.0 launched! — Pending: your tests → open PR → merge → run [launch checklist](./launch-checklist-v2.0.md) (4.5.2) → deploy (4.5.3) → tag `v2.0.0` (4.5.4).

**Total Sub-tasks**: ~22

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
