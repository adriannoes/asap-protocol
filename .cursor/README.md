This directory contains the **Cognitive Context** and **Operating Rules** for the coding AI Agents (i.e., Cursor, Claude Code) working on the ASAP Protocol.

It is the "brain" of the project's development process.

## Structure

### 📂 [commands/](.cursor/commands)
- **[Commands](./commands)**: Workflow prompts (`create-prd`, `generate-tasks`)
- **[Skills](./skills)**: Agent capabilities (`code-review`, `security-review`)
- **[Rules](./rules)**: Context (`architecture-principles`, `security-standards`)
- **[Product Specs](./product-specs)**: The "What" and "Why"
- **[Dev Planning](./dev-planning)**: The "How" and "When"

### 📂 [product-specs/](.cursor/product-specs)
**The "What" and "Why"**.
Contains the immutable truths of the product.
- **Vision**: `product-specs/strategy/vision-agent-marketplace.md`
- **Roadmap**: `product-specs/strategy/roadmap-to-marketplace.md`
- **Codebase Strategy**: `product-specs/strategy/repository-strategy.md`

### 📂 [dev-planning/](.cursor/dev-planning)
**The "How" and "When"**.
Contains the execution plans.
- **Tasks**: Detailed checklists broken down by sprint/version.
- **Architecture**: Technical documentation and rationale (e.g., `tech-stack-decisions.md`).
- **Templates**: Standard formats for issues and plans.


---

> **Tip for Humans**: You ideally shouldn't need to touch `rules/` or `commands/` often. Focus on reading `product-specs/` to understand the product and `dev-planning/` to track progress.
>
**Bonus**: Looking for battle-tested Cursor rules? Check out [awesome-vibe-coding/cursor-rules](https://github.com/adriannoes/awesome-vibe-coding/tree/main/cursor-rules).
