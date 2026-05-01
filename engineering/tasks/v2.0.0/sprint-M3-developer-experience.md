# Sprint M3: Developer Experience (IssueOps)

> **Goal**: Low-friction Agent Registration via IssueOps
> **Prerequisites**: Sprint M2 completed (Web App Features)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `.github/ISSUE_TEMPLATE/register_agent.yml` - Registration issue form (Task 3.1; includes built_with, repository_url, documentation_url, confirm)
- `.github/workflows/register-agent.yml` - Registration Action (Task 3.3; trigger issues opened/edited, label registration)
- `scripts/process_registration.py` - Parse issue body, validate manifest, update registry (Task 3.3)
- `tests/scripts/test_process_registration.py` - Unit tests for parsing and validation (Task 3.3.5)
- `src/asap/discovery/registry.py` - RegistryEntry + generate_registry_entry (optional repository_url, documentation_url, built_with)
- `apps/web/src/types/protocol.d.ts` - Manifest type (optional repository_url, documentation_url, built_with for registry display)
- `apps/web/src/lib/register-schema.ts` - Shared Zod ManifestSchema for form + server action (Task 3.2.3)
- `apps/web/src/app/dashboard/register/page.tsx` - Web Registration Form (Task 3.2)
- `apps/web/src/app/dashboard/register/register-form.tsx` - Form UI using ManifestSchema + zodResolver
- `apps/web/src/app/dashboard/register/__tests__/register-form.test.tsx` - Vitest: Zod validation + Issue URL template (Task 3.2.5)
- `apps/web/src/app/dashboard/register/actions.ts` - Server action: validation + reachability, returns issueUrl (no PR)
- `apps/web/src/lib/github-issues.ts` - Build GitHub Issue URL with template + pre-fill params (Task 3.2.4)
- `apps/web/src/app/dashboard/actions.ts` - fetchUserRegistrationIssues: read-only Octokit issues (label registration) for My Agents (Task 3.4.1)
- `apps/web/src/app/dashboard/dashboard-client.tsx` - My Agents: pending issues, Listed/Pending/Verified logic (Task 3.4)
- `.github/ISSUE_TEMPLATE/request_verification.yml` - Verification request issue form (Task 3.5.1; labels verification-request, pending-review)
- `apps/web/src/app/dashboard/verify/page.tsx` - Verify page: reads agent_id from query, renders VerifyForm or empty-state (Task 3.5.2)
- `apps/web/src/app/dashboard/verify/verify-form.tsx` - Verification form: why_verified, running_since, evidence, contact; submits to GitHub Issue (Task 3.5.2)
- `apps/web/src/app/dashboard/verify/actions.ts` - submitVerificationRequest: auth + buildVerificationRequestIssueUrl (Task 3.5.2)
- `apps/web/src/lib/github-issues.ts` - buildVerificationRequestIssueUrl for request_verification.yml (Task 3.5.2)
- `docs/guides/registry-verification-review.md` - Admin guide: vet verification requests, update registry (Task 3.5.3)
- `apps/web/src/app/dashboard/verify/__tests__/verify-form.test.tsx` - Vitest: Zod validation + GitHub Issue URL (Task 3.5.4)
- `apps/web/src/app/dashboard/verify/__tests__/verify-actions.test.ts` - Vitest: auth + URL building (Task 3.5.4)
- `src/asap/models/entities.py` - VerificationStatus model + verification on Manifest (Task 3.6.1)
- `src/asap/discovery/registry.py` - verification on RegistryEntry (Task 3.6.1)
- `apps/web/src/types/protocol.d.ts` - Regenerated with VerificationStatus (Task 3.6.2)
- `apps/web/src/types/registry.d.ts` - RegistryAgent type with repository_url, documentation_url, built_with (Doc)
- `apps/web/src/lib/registry.ts` - normalizeRegistryAgent for endpoints.http→asap; fetchRegistry returns RegistryAgent[] (Doc)

---

## Context

This sprint optimizes the **Developer Experience** for registering agents by migrating from a PR-based flow to an IssueOps flow.
**Why the change?** The M2 automated PR flow requires the NextAuth GitHub App to request `public_repo` permissions, which gives the web app write access to all of a user's repositories. This creates massive friction and trust issues for developers trying to register.
By providing a **Web Form** that generates a pre-filled GitHub Issue (which the user submits themselves on GitHub.com), we can downgrade the NextAuth scope to just `read:user`.
A **GitHub Action** then processes this Issue to validate the agent and automatically merge it into `registry.json`.

---

## Task 3.1: GitHub Issue Template

### Sub-tasks

- [x] 3.1.1 Create `register_agent.yml`
  - **Inputs**: Must directly map to the `Manifest` / `RegistryEntry` fields:
    - Name (slug-friendly)
    - Description
    - Manifest URL
    - HTTP Endpoint
    - WebSocket Endpoint (Optional)
    - Skills (comma-separated)
    - **Built with** (optional dropdown: CrewAI, OpenClaw, LangChain, AutoGen, Other)
    - **Repository URL** (optional)
    - **Documentation URL** (optional)
    - **Confirmation** checkbox (required): manifest publicly accessible, endpoints match
  - **Validation**: Regex for URLs (in Action 3.3), required fields in template
  - **Labels**: `registration`, `pending-review`

**Acceptance Criteria**:
- [x] Users can open a new Issue using the template
- [x] Template enforces required fields

---

## Task 3.2: Web Registration Form

### Sub-tasks

- [x] 3.2.1 Update NextAuth Scopes (`apps/web/src/auth.ts`)
  - **Action**: Remove `public_repo` or `repo` scopes from the GitHub provider.
  - **Goal**: Only request `read:user` (or `user:email`) to restore developer trust.

- [x] 3.2.2 Refactor `/dashboard/register/page.tsx`
  - **Form Framework**: React Hook Form + Zod (Keep existing layout)
  - **Fields**: Match Issue Template exactly (including optional: built_with, repository_url, documentation_url; and confirmation checkbox).

- [x] 3.2.3 Client-side Validation (Zod) & Reachability (Keep existing)
  - Schema: `ManifestSchema` (shared)
  - **Reachability**: Keep the existing SSR/Server Action reachability check.

- [x] 3.2.4 "Submit" Logic Pivot
  - **Action**: Remove the `octokit.rest.pulls.create` logic from `actions.ts`.
  - **New Action**: Construct GitHub Issue URL with query params matching the YAML template inputs.
    - Example: `https://github.com/adriannoes/asap-protocol/issues/new?template=register_agent.yml&title=Register:+<name>&name=<name>&description=<description>&manifest_url=...`
  - **Redirect**: Open GitHub in a new tab so the user can click "Submit new issue".

- [x] 3.2.5 Unit Tests for Registration Form (Vitest)
  - **Action**: Create `apps/web/src/app/dashboard/register/register-form.test.tsx`.
  - **Tests**: 
    - Verify Zod schema validation (e.g., regex constraints, required fields).
    - Mock GitHub Issue URL generation and ensure it matches the expected template.

**Acceptance Criteria**:
- [x] Form validates inputs locally
- [x] "Submit" opens correct GitHub Issue URL with pre-filled data

---

## Task 3.3: Registration Action (The "Ops")

### Sub-tasks

- [x] 3.3.1 Create `.github/workflows/register-agent.yml`
  - **Trigger**: `issues: [opened, edited]`
  - **Condition**: Label `registration` present

- [x] 3.3.2 Parsing Script (`scripts/process_registration.py`)
  - **Input**: Issue Body (Markdown/YAML)
  - **Parsing**: Use regex to extract data under markdown headers generated by the GitHub Issue Form.
  - **Output**: JSON Agent Object matching `RegistryEntry` (Manifest-derived + optional `repository_url`, `documentation_url`, `built_with`).
  - **Optional fields**: Parse and pass through `repository_url`, `documentation_url`, `built_with` (empty string → omit or null in registry).

- [x] 3.3.3 Validation Steps
  - **Schema**: Validate against the `Manifest` Pydantic model (`src/asap/models/entities.py`).
  - **Network**: Fetch the Manifest URL to ensure it is alive.
  - **Identity**: Ensure `id` matches `urn:asap:agent:<github_username>:<name>`.
  - **Uniqueness**: Check if `id` exists in `registry.json` (prevent duplicate names for the same user).

- [x] 3.3.4 Auto-Merge Logic
  - **Permissions**: The workflow needs `permissions: contents: write` to push to `main` (if branch protections allow).
  - **If Valid**:
    - Build `RegistryEntry` (including optional `repository_url`, `documentation_url`, `built_with` from issue body).
    - Add to `registry.json`.
    - Commit directly to `main`: `feat(registry): register <agent_id>`.
    - Close Issue with comment: "✅ Registered successfully!" via `gh issue close`.
  - **If Invalid**:
    - Comment on Issue: "❌ Validation failed: <errors>" via `gh issue comment`.
    - Leave Issue open for edits.

- [x] 3.3.5 Unit Tests for Parsing Script (pytest)
  - **Action**: Create `tests/scripts/test_process_registration.py`.
  - **Tests**:
    - Parse valid and invalid markdown issue templates.
    - Include cases where the issue body contains the optional fields (`repository_url`, `documentation_url`, `built_with`) and assert they are extracted and passed through to the payload / `RegistryEntry`.
    - Mock network calls for Manifest reachability.
    - Verify strict schema validation logic using the `Manifest` Pydantic model.

**Acceptance Criteria**:
- [x] Valid Issue -> Agent added to `registry.json` -> Issue Closed
- [x] Invalid Issue -> Error Comment -> Issue Open

---

## Task 3.4: Developer Dashboard Integration

### Sub-tasks

- [x] 3.4.1 "My Agents" Logic
  - **Filter**: `registry.json` where `agent.id` is `urn:asap:agent:<github_username>:<name>`. (Manifest has no `maintainers` field!).
  - **Status**:
    - "Listed": Fetch from `registry.json`.
    - "Pending": Use Octokit (read-only) to fetch open issues in `asap-protocol` created by `author:<github_username>` with label `registration`.
    - "Verified": Agent has `verification.status === 'verified'` in `registry.json` (Requires Task 3.6).

- [x] 3.4.2 Dashboard UI Updates
  - Show "Pending Registration" cards
  - Show "Apply for Verified" button on eligible agents (Listed + Unverified)

- [x] 3.4.3 Pending cards: link to issue + feedback copy (MVP Option A)
  - In each "Pending Registration" card, show a **direct link to the GitHub issue** (e.g. "View issue" / "Open in GitHub").
  - Copy for the user: *"If validation failed, the comment on the issue shows the reason. You can fix and re-edit the issue."*
  - Goal: user can see pending agents on the dashboard and open the issue in one click to check success or error without searching GitHub.

- [x] 3.4.4 Status badges on agent cards (Listed / Verified)
  - On each listed agent card, show a **Listed** badge (in registry) alongside the existing Online/Offline badge.
  - When Task 3.6 is done: show **Verified** badge (e.g. shield icon) for agents with `verification.status === 'verified'`.
  - Keeps "in registry" and trust state visible at a glance.

- [x] 3.4.5 Pending count in "My Agents" tab
  - In the tab label, show pending count when > 0, e.g. **My Agents (1 pending)** or **My Agents · 1 pending**.
  - User sees at a glance that something is awaiting validation without opening the tab.

- [x] 3.4.6 Empty state when only pending (no listed yet)
  - When there are pending registration(s) but zero listed agents: do not show generic "No agents found".
  - Copy: *"You have pending registration(s). Open the issue link above to check if it was accepted or if there's feedback to fix."*
  - When there are neither pending nor listed: keep current "No agents found" + "Register your first agent" CTA.

- [x] 3.4.7 Refresh button for My Agents
  - Add a **Refresh** button in the My Agents section that revalidates data (refetch `registry.json` and pending issues).
  - After the user closes an issue on GitHub, they can refresh to see the agent move from Pending to Listed without reloading the page manually.

**Acceptance Criteria**:
- [x] Dashboard shows true status of all agents (Listed / Pending / Verified)
- [x] Pending registrations show a direct link to the issue and short copy about where to see validation result
- [x] Agent cards show Listed (and Verified when 3.6 is done) badges; tab shows pending count when > 0
- [x] Empty state copy differs when user has pending but no listed vs. no agents at all
- [x] Refresh button updates listed and pending data on demand

---

## Task 3.5: Verified Badge Request (IssueOps)

**Entry point**: User clicks **"Apply for Verified"** on a Listed agent card in the Dashboard (Task 3.4.2). That button links to the verification form (3.5.2) with `agent_id` so the issue can be pre-filled.

### Sub-tasks

- [x] 3.5.1 Create `request_verification.yml` Issue Template
  - **Inputs**: Agent ID, Evidence of reliability (links, uptime stats), Contact info
  - **Labels**: `verification-request`, `pending-review`

- [x] 3.5.2 Verification Form (Web)
  - **Route**: `/dashboard/verify?agent_id=...`
  - **Fields**: "Why should this agent be verified?", "How long has it been running?"
  - **Action**: Redirects to pre-filled GitHub Issue

- [x] 3.5.3 Admin Review Process (Manual)
  - **Documentation**: Guide for admins on how to vet agents (uptime check, code review if open source).
  - **Action**: Admin manually edits `registry.json` to add `verification` details.

- [x] 3.5.4 Unit Tests for Verification Form (Vitest)
  - **Action**: Create tests for the verification form logic.
  - **Tests**: Assert correctly parameterized GitHub Issue URL generation.

**Acceptance Criteria**:
- [x] "Apply for Verified" on dashboard (3.4) leads to verification form with correct `agent_id`; form redirects to pre-filled GitHub Issue
- [x] Issue template for verification exists; admins can review and update `registry.json` (manual until 3.6 schema is in place)

---

## Task 3.6: Update Protocol Schema (IssueOps Pre-requisite)

> **Context**: The `verification` field does not exist in `src/asap/models/entities.py`, so adding it to `registry.json` would break Python validation and TypeScript models.

**Enables**: Once 3.6 is done, (a) the **Verified badge** can be shown on dashboard agent cards (3.4.4), (b) admins can persist `verification` in `registry.json` after review (3.5.3) without breaking validation, and (c) browse and agent detail pages can display verified status.

### Sub-tasks

- [x] 3.6.1 Update `src/asap/models/entities.py`
  - Add a `VerificationStatus` model (`status: str`, `verified_at: str`).
  - Add `verification: Optional[VerificationStatus] = None` to the `Manifest` class.

- [x] 3.6.2 Regenerate TypeScript Types
  - Run `python scripts/generate_types.py` so the web app can use `agent.verification`.

**Acceptance Criteria**:
- [x] Python Manifest (and registry schema if needed) accept optional `verification`; validation and registry ingestion do not break
- [x] TypeScript types include `verification`; dashboard (3.4) and browse/detail pages can read and display Verified status

---

## Sprint M3 Definition of Done

- [x] Registration flow (Web -> Issue -> Action) working end-to-end
- [x] Developers can register agents without manual Git commands
- [x] Invalid registrations are automatically rejected with feedback

**Total Sub-tasks**: ~12

## Deferred to v2.1+

- **Category/tags in registry**: Add optional category (e.g. Research, Coding, Productivity) and tags to `RegistryEntry`; filters in browse UI. Not in M3 scope.

## Documentation Updates
- [x] **Required/optional in form**: Schema comment in `register-schema.ts` lists Required vs Optional; form labels show "(required)" or "(optional)" for all fields (Task 3.2 polish).
- [x] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
- [x] **Web app types**: Ensure registry agent type (or Manifest) includes optional `repository_url`, `documentation_url`, `built_with` for display on agent detail and browse (Task 3.2/3.4).
