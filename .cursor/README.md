This directory contains the **Cognitive Context** and **Operating Rules** for the coding AI Agents (i.e., Cursor, Claude Code) working on the ASAP Protocol.

It is the "brain" of the project's development process.

## Structure

### Tooling (this folder)

- **[Commands](./commands)**: Workflow prompts (`create-prd`, `generate-tasks`)
- **[Skills](./skills)**: Agent capabilities (`code-review`, `security-review`)
- **[Rules](./rules)**: Context (`architecture-principles`, `security-standards`)

### Product & engineering (repository root)

Planning artifacts live **outside** `.cursor/` so the repo separates editor tooling from product truth:

- **`product/`** ([folder](../product)): PRDs, ADRs, design guides — the "what" and "why".
  - **`product/strategy/`**: narrative vision and roadmap (**ignored by Git** on the remote; maintain local copies for internal planning).
  - **`product/prd/private/`**: tactical PRDs (**ignored** when marked private in `.gitignore`).
- **`engineering/`** ([folder](../engineering)): Tasks, checkpoints, architecture notes — the "how" and "when".

---

> **Tip for Humans**: You ideally shouldn't need to touch `rules/` or `commands/` often. Read `product/` for scope and `engineering/` for execution plans.

**Bonus**: Looking for battle-tested Cursor rules? Check out [awesome-vibe-coding/cursor-rules](https://github.com/adriannoes/awesome-vibe-coding/tree/main/cursor-rules).
