This directory contains the **Cognitive Context** and **Operating Rules** for the coding AI Agents (i.e., Cursor, Claude Code) working on the ASAP Protocol.

It is the "brain" of the project's development process.

## Structure

### 📂 `[commands/](./commands)`
**Workflows & Automation**.
Prompt templates and workflows for the AI to follow when executing complex tasks.
- *Example*: "Conduct a Security Review", "Create a PRD", "Generate Tasks".

### 📂 `[skills/](./skills)`
**Agent Capabilities**.
Advanced workflows that combine instructions with executable scripts (e.g., automated audits).
- *Example*: `code-quality-review`, `security-review`.

### 📂 `[rules/](./rules)`
**Active Instructions**.
Files ending in `.mdc` that are automatically indexed by Cursor. They define strict coding standards, architectural principles, and behavior rules.
- *Example*: `architecture-principles.mdc`, `python-best-practices.mdc`.

### 📂 `[product-specs/](./product-specs)`
**The "What" and "Why"**.
Contains the immutable truths of the product.
- **PRDs**: Product Requirement Documents.
- **ADRs**: Architectural Decision Records.
- **Vision**: Long-term goals.

### 📂 `[dev-planning/](./dev-planning)`
**The "How" and "When"**.
Contains the execution plans.
- **Tasks**: Detailed checklists broken down by sprint/version.
- **Architecture**: Technical documentation and rationale (e.g., `tech-stack-decisions.md`).
- **Templates**: Standard formats for issues and plans.


---

> **Tip for Humans**: You ideally shouldn't need to touch `rules/` or `commands/` often. Focus on reading `product-specs/` to understand the product and `dev-planning/` to track progress.
>
**Bonus**: Looking for battle-tested Cursor rules? Check out [awesome-vibe-coding/cursor-rules](https://github.com/adriannoes/awesome-vibe-coding/tree/main/cursor-rules).
