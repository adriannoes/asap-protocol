# Engineering (`engineering/`)

Execution planning for the ASAP Protocol: **tasks** (by release/sprint), **code-review** notes, **architecture** deep dives, and references. Documentation review milestones live in [`product/checkpoints.md`](../product/checkpoints.md).

## Layout

| Path | Purpose |
|------|---------|
| **`tasks/`** | Sprint and roadmap markdown (versioned folders, roadmaps, checklists). |
| **`code-review/`** | Historical PR review notes. |
| **`architecture/`** | Supporting docs (e.g. rate limiting, tech-stack rationale lives partly here and in `product/decision-records/`). |
| **`references/`** | External spec excerpts when helpful (e.g. MCP). |
| **`manual-release-testing.md`** | Human verification companion to release sprints. |

Ignored paths (see `.gitignore`): **`private/`**, **`tasks/private/`**, **`tasks/v2.3.[1-9]*/`** — keep tactical drafts locally only.

For **what** and **why**, start in [`../product/`](../product/README.md).
