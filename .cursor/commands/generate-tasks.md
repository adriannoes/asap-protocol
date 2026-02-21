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
5.  **Phase 2: Generate Sub-Tasks:** Once the user confirms, break down each parent task into smaller, actionable sub-tasks. **Use the detailed format** (see below) to ensure weaker AI models can execute correctly. For tasks that are part of a flow or have dependencies, add **Trigger/entry point**, **Enables**, and **Depends on** at the task level. Give each parent task its own **acceptance criteria** (verifiable, and specific to that task).
6.  **Identify Relevant Files:** Based on the tasks and PRD, identify potential files that will need to be created or modified. List these under the `Relevant Files` section, including corresponding test files if applicable.
7.  **Make dependencies explicit:** For any task that is part of a larger flow or has dependencies (user journey, pipeline step, API consumer, script that reads another task's output), add **Trigger/entry point**, **Enables**, and **Depends on** (see "Dependencies and integration" below). Ensure acceptance criteria belong to the task that delivers them—no AC from another task.
8.  **Generate Final Output:** Combine the parent tasks, sub-tasks, relevant files, dependency notes, and acceptance criteria into the final Markdown structure.
9.  **Post-generation checklist:** Before saving, verify: (a) tasks with dependencies have Trigger/Enables/Depends on where relevant; (b) each task has its own acceptance criteria and none describe another task's outcome; (c) integration points (where one task's output is another's input) are stated in sub-tasks or task notes.
10. **Save Task List:** Save the generated document in the `/.cursor/dev-planning/tasks/` directory with the filename `tasks-[prd-file-name].md`.

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

### Dependencies and integration (when applicable)

For any task that is part of a larger flow or has dependencies—whether a user journey, a pipeline step, an API consumer, or a script that reads another task's output—make the following explicit at the start of that task (or parent task):

- **Trigger / entry point:** What invokes or reaches this work (e.g. user action, cron job, webhook, call from another service, previous pipeline step).
- **Enables:** What this task unblocks for other tasks, services, or features (e.g. new API for a client, new field in a schema, next step in a workflow).
- **Depends on:** What must already exist before this task (other tasks, schema, endpoints, file format).

Use neutral wording so the same rules apply to backend, frontend, scripts, and infrastructure. When one task's output is another's input, describe the **integration** in the sub-tasks or task description (e.g. API contract, payload shape, file format, URL, or artifact).

Example of an explicit dependency block at the start of a task:

```markdown
## Task 2.3: Verification request form

**Trigger:** User clicks "Apply for Verified" on a listed agent card (Task 2.2).  
**Enables:** Admins to process verification issues; dashboard to show Verified badge (Task 2.4) once schema is updated.  
**Depends on:** Task 2.2 (dashboard with listed agents); Task 2.5 (schema) for persisting verification in registry.
```

### Acceptance criteria

- Each parent task must have **acceptance criteria** that are specific to that task and **verifiable** (command, observable behaviour, or clear done condition).
- No acceptance criterion may describe an outcome that is the responsibility of a different task. Check that AC are assigned to the task that actually delivers them.

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

When the result of this sub-task (or task) is consumed by another task, add an **Integration** line so the link is explicit:

- **Integration** (optional): [How this output is used elsewhere—e.g. "This endpoint is called by the dashboard (Task N) with query param `agent_id`"; "This script writes a file committed by the workflow in Task M"; "Schema consumed by TypeScript types in `apps/web`".]

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