# Generating a Task List from a PRD

## Goal

To guide an AI assistant in creating a detailed, step-by-step task list in Markdown format based on an existing Product Requirements Document (PRD). The task list should guide a developer (or weaker AI model) through implementation.

## Output

- **Format:** Markdown (`.md`)
- **Location:** `/.cursor/dev-planning/tasks/`
- **Filename:** `tasks-[prd-file-name].md` (e.g., `tasks-prd-user-profile-editing.md`)
- **Template:** See [task-template.md](../dev-planning/templates/task-template.md) for detailed format

## Process

1.  **Receive PRD Reference:** The user points the AI to a specific PRD file.
2.  **Analyze PRD:** The AI reads and analyzes the functional requirements, user stories, and other sections of the specified PRD.
3.  **Phase 1: Generate Parent Tasks:** Based on the PRD analysis, create the file and generate the main, high-level tasks required to implement the feature. Use your judgement on how many high-level tasks to use. It's likely to be about 5. Present these tasks to the user in the specified format (without sub-tasks yet). Inform the user: "I have generated the high-level tasks based on the PRD. Ready to generate the sub-tasks? Respond with 'Go' to proceed."
4.  **Wait for Confirmation:** Pause and wait for the user to respond with "Go".
5.  **Phase 2: Generate Sub-Tasks:** Once the user confirms, break down each parent task into smaller, actionable sub-tasks. **Use the detailed format** (see below) to ensure weaker AI models can execute correctly.
6.  **Identify Relevant Files:** Based on the tasks and PRD, identify potential files that will need to be created or modified. List these under the `Relevant Files` section, including corresponding test files if applicable.
7.  **Generate Final Output:** Combine the parent tasks, sub-tasks, relevant files, and notes into the final Markdown structure.
8.  **Save Task List:** Save the generated document in the `/.cursor/dev-planning/tasks/` directory with the filename `tasks-[prd-file-name].md`.

## Output Format

The generated task list _must_ follow this structure:

```markdown
## Relevant Files

- `path/to/potential/file1.py` - Brief description of why this file is relevant.
- `tests/path/to/test_file1.py` - Unit tests for `file1.py`.

### Notes

- Unit tests should typically be placed in `tests/` mirroring the `src/` structure.
- Use `pytest tests/[path] -v` to run tests.

## Tasks

- [ ] 1.0 Parent Task Title
  - [ ] 1.1 [Sub-task description 1.1]
  - [ ] 1.2 [Sub-task description 1.2]
- [ ] 2.0 Parent Task Title
  - [ ] 2.1 [Sub-task description 2.1]
```

## Detailed Sub-task Format (for weaker AI models)

When generating tasks that will be executed by less capable AI models, use this **detailed format** for each sub-task:

```markdown
- [ ] X.Y.Z [Action verb] [specific item]
  - **File**: `path/to/file.py` (create new | modify existing)
  - **What**: [Detailed description of what to create or modify]
  - **Why**: [Context - why this is needed, how it fits the bigger picture]
  - **Pattern**: [Reference to existing code to follow, e.g., "Follow src/asap/auth/oauth2.py"]
  - **Verify**: [How to confirm it works - test command or expected behavior]
```

### Example: Good vs Bad Sub-task

❌ **Bad** (too vague):
```markdown
- [ ] 1.1 Add OAuth2 client
```

✅ **Good** (explicit and contextual):
```markdown
- [ ] 1.1 Create OAuth2 client credentials class
  - **File**: `src/asap/auth/oauth2.py` (create new)
  - **What**: Create `OAuth2ClientCredentials` class with `get_access_token()` and `refresh_token()` methods
  - **Why**: Enables agent-to-agent authentication using client_credentials grant
  - **Pattern**: Use Authlib's AsyncOAuth2Client internally, expose ASAP-specific models (see ADR-12)
  - **Verify**: `pytest tests/auth/test_oauth2.py -k "test_get_token"` passes
```

## Interaction Model

The process explicitly requires a pause after generating parent tasks to get user confirmation ("Go") before proceeding to generate the detailed sub-tasks. This ensures the high-level plan aligns with user expectations before diving into details.

## Target Audience

Assume the primary reader of the task list is:
1. A **junior developer** who will implement the feature
2. A **weaker AI model** that needs explicit context and verification steps

Both require clear, unambiguous instructions with sufficient context to understand not just WHAT to do, but WHY.

## Related Templates

- **Task Template**: [task-template.md](../dev-planning/templates/task-template.md) - Full template with examples
- **PRD Template**: [create-prd.md](./create-prd.md) - How to create PRDs