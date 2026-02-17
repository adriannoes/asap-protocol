# Sprint M3: Developer Experience (IssueOps)

> **Goal**: Low-friction Agent Registration via IssueOps
> **Prerequisites**: Sprint M2 completed (Web App Features)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `.github/ISSUE_TEMPLATE/register_agent.yml` - Registration Form Definition
- `.github/workflows/register-agent.yml` - Registration Action
- `apps/web/app/register/page.tsx` - Web Registration Form
- `apps/web/lib/github-issues.ts` - Issue Submission Logic

---

## Context

This sprint optimizes the **Developer Experience** for registering agents.
Instead of requiring a CLI tool or manual Git PRs, we provide a **Web Form** that generates a pre-filled GitHub Issue.
A **GitHub Action** then processes this Issue to validate the agent and automatically merge it into `registry.json`.

---

## Task 3.1: GitHub Issue Template

### Sub-tasks

- [ ] 3.1.1 Create `register_agent.yml`
  - **Inputs**: Name, Description, Endpoints (HTTP/WS), Manifest URL, Skills
  - **Validation**: Regex for URLs, required fields
  - **Labels**: `registration`, `pending-review`

**Acceptance Criteria**:
- [ ] Users can open a new Issue using the template
- [ ] Template enforces required fields

---

## Task 3.2: Web Registration Form

### Sub-tasks

- [ ] 3.2.1 Create `/register` page
  - **Form Framework**: React Hook Form + Zod
  - **Fields**: Match Issue Template

- [ ] 3.2.2 Client-side Validation (Zod)
  - Schema: `ManifestSchema` (shared)
  - Check: Valid URLs, name length, etc.

- [ ] 3.2.3 "Check Reachability" button
  - **Action**: Fetch Manifest URL from client
  - **Feedback**: "✅ Reachable" or "❌ Fail"

- [ ] 3.2.4 "Submit" Logic
  - **Action**: Construct GitHub Issue URL with query params
    - `https://github.com/asap-protocol/asap-protocol/issues/new?template=register_agent.yml&title=Register:+<name>&body=...`
  - **Redirect**: Open GitHub in new tab

**Acceptance Criteria**:
- [ ] Form validates inputs locally
- [ ] "Submit" opens correct GitHub Issue URL with pre-filled data

---

## Task 3.3: Registration Action (The "Ops")

### Sub-tasks

- [ ] 3.3.1 Create `.github/workflows/register-agent.yml`
  - **Trigger**: `issues: [opened, edited]`
  - **Condition**: Label `registration` present

- [ ] 3.3.2 Parsing Script (`scripts/process_registration.py`)
  - **Input**: Issue Body (Markdown/YAML)
  - **Output**: JSON Agent Object

- [ ] 3.3.3 Validation Steps
  - **Schema**: Validate against `Agent` Pydantic model
  - **Network**: `curl` the Manifest URL
  - **Uniqueness**: Check if `id` or `name` exists in `registry.json`

- [ ] 3.3.4 Auto-Merge Logic
  - **If Valid**:
    - Add to `registry.json`
    - Commit: "feat(registry): register <agent_name>"
    - Close Issue with comment: "✅ Registered successfully!"
  - **If Invalid**:
    - Comment on Issue: "❌ Validation failed: <errors>"
    - Leave Issue open for edits

**Acceptance Criteria**:
- [ ] Valid Issue -> Agent added to `registry.json` -> Issue Closed
- [ ] Invalid Issue -> Error Comment -> Issue Open

---

## Task 3.4: Developer Dashboard Integration

### Sub-tasks

- [ ] 3.4.1 "My Agents" Logic
  - **Filter**: `registry.json` where `maintainers` includes current GitHub User
  - **Status**:
    - "Listed": Present in `registry.json`
    - "Pending": Open Issue with `registration` label (via GitHub API)

- [ ] 3.4.2 Dashboard UI Updates
  - Show "Pending Registration" cards linking to the Issue

**Acceptance Criteria**:
- [ ] Dashboard shows both Listed and Pending agents

---

## Sprint M3 Definition of Done

- [ ] Registration flow (Web -> Issue -> Action) working end-to-end
- [ ] Developers can register agents without manual Git commands
- [ ] Invalid registrations are automatically rejected with feedback

**Total Sub-tasks**: ~12

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
