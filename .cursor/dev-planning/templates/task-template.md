# Task Template for Detailed Sprint Planning

> **Purpose**: Template for creating detailed, AI-friendly task breakdowns
> **Location**: Use this template when expanding sprint roadmaps into detailed task files

---

## Template Structure

When creating a detailed task file (e.g., `sprint-S1-oauth2-foundation.md`), follow this structure:

### Header Section

```markdown
# Tasks: ASAP vX.Y.Z [Feature Name] (Sprint IDs) - Detailed

> **Sprints**: S1-S2 - [Sprint themes]
> **Goal**: [One sentence describing the outcome]
> **Prerequisite**: [What must be done before this]
> **Estimated Duration**: [X-Y days]

---
```

### Relevant Files Section

```markdown
## Relevant Files

### Sprint S1: [Theme]
- `src/asap/module/file.py` - [What this file does]
- `tests/module/test_file.py` - Unit tests for file.py

### Sprint S2: [Theme]
- `src/asap/module/other.py` - [Purpose]
- `tests/module/test_other.py` - Tests
```

### Task Section (Detailed Format)

Each task should include:

```markdown
## Sprint S1: [Theme]

### Task 1.1: [Task Name]

**Goal**: [One sentence - what does success look like?]

**Context**: [Why are we doing this? What problem does it solve? How does it fit in the bigger picture?]

**Prerequisites**: [What must exist before starting this task?]

#### Sub-tasks

- [ ] 1.1.1 [Action verb] [specific item]
  - **File**: `path/to/file.py`
  - **What**: [Detailed description of what to create/modify]
  - **Why**: [Rationale - helps model understand intent]
  - **Reference**: [Link to docs, examples, or existing code to follow]
  - **Verify**: [How to confirm this works - command or manual check]

- [ ] 1.1.2 [Action verb] [specific item]
  - **File**: `path/to/file.py`
  - **What**: [Description]
  - **Pattern**: [If applicable - "Follow pattern from src/asap/auth/oauth2.py"]
  - **Test**: `pytest tests/module/test_file.py -k "test_name"`
  - **Verify**: [Expected output or behavior]

- [ ] 1.1.3 Write tests
  - **File**: `tests/module/test_file.py`
  - **What**: Test [specific functionality]
  - **Coverage**: [List scenarios to test]
  - **Command**: `pytest tests/module/test_file.py -v`

- [ ] 1.1.4 Commit
  - **Command**: `git commit -m "feat(module): add [feature]"`
  - **Scope**: [List files that should be in this commit]

**Acceptance Criteria**:
- [ ] [Specific, verifiable outcome 1]
- [ ] [Specific, verifiable outcome 2]
- [ ] Test coverage >95% for new code

---
```

### Definition of Done Section

```markdown
**Sprint S1-S2 Definition of Done**:
- [ ] [Key deliverable 1]
- [ ] [Key deliverable 2]
- [ ] All tests passing
- [ ] Test coverage >95%
- [ ] Documentation updated

**Total Sub-tasks**: ~XX
```

---

## Key Principles for Detailed Tasks

### 1. Context is King
A weaker model needs to understand WHY, not just WHAT. Always include:
- **Goal**: What success looks like
- **Context**: Why this matters
- **Reference**: Where to look for patterns

### 2. Be Explicit About Files
Don't assume the model knows the codebase. Always specify:
- Exact file paths (not module names)
- Whether to create new or modify existing
- Related files (tests, types, exports)

### 3. Provide Verification Steps
Every sub-task should have a way to verify completion:
- Test commands: `pytest tests/... -k "..."`
- Manual checks: "Endpoint returns 200 with valid token"
- Build checks: `uv run mypy src/`

### 4. Reference Existing Patterns
Point to existing code as examples:
- "Follow pattern from `src/asap/auth/middleware.py`"
- "Use same structure as `OAuth2ClientCredentials`"

### 5. Commit Boundaries
Define clear commit boundaries:
- One commit per logical unit
- Include commit message format
- List files that belong in each commit

---

## Example: Good vs Bad Sub-task

### ❌ Bad (too vague for weak models)

```markdown
- [ ] 1.1.1 Add OAuth2 client
  - Create OAuth2 client class
```

### ✅ Good (explicit and contextual)

```markdown
- [ ] 1.1.1 Create OAuth2 client credentials class
  - **File**: `src/asap/auth/oauth2.py` (create new)
  - **What**: Create `OAuth2ClientCredentials` class with:
    - `__init__(client_id, client_secret, token_url)`
    - `async get_access_token() -> Token`
    - `async refresh_token() -> Token`
  - **Why**: Needed for agent-to-agent auth using client_credentials grant
  - **Pattern**: Use Authlib's AsyncOAuth2Client internally, expose ASAP-specific models (see ADR-12)
  - **Reference**: https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/
  - **Verify**: Unit test can obtain mock token
```

---

## Checklist Before Finalizing Task File

- [ ] Every sub-task has a **File** path
- [ ] Every sub-task has a **What** description
- [ ] Every sub-task has a **Verify** step
- [ ] Context explains WHY, not just WHAT
- [ ] References to existing patterns included
- [ ] Commit messages specified
- [ ] Acceptance criteria are measurable
- [ ] Total sub-task count is accurate
