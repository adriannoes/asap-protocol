---
trigger: model_decision
description: Architecture principles and code quality standards including SOLID principles, DRY, and clean code practices for designing and refactoring code
---

# Architecture & Principles (SOLID/DRY)

## Code Quality Standards

1. **SOLID Principles**:
   - **Single Responsibility**: Each class/module should have one reason to change.
   - **Open/Closed**: Software entities should be open for extension, but closed for modification.
   - **Liskov Substitution**: Objects of a superclass should be replaceable with objects of its subclasses.
   - **Interface Segregation**: Prefer many client-specific interfaces over one general-purpose interface.
   - **Dependency Inversion**: Depend on abstractions, not concretions.

2. **DRY (Don't Repeat Yourself)**:
   - Minimize code duplication through proper abstraction and semantic naming.
   - If a logic is used more than twice, consider refactoring it into a reusable component or utility.

3. **Clean Code**:
   - **Semantic Naming**: Use clear, descriptive names for variables, functions, and classes.
   - **Small Functions**: Functions should do one thing and be relatively short.
   - **Avoid Deep Nesting**: Use early returns (guard clauses) to reduce indentation.

## Product Architecture (v2.0.0+)

The ASAP Protocol uses a **Lean Marketplace** polyglot architecture:
1. **Core Protocol (`src/asap/`)**: Strict Python. Uses Pydantic for validation and `uv` for dependency management. No backend APIs.
2. **Web App (`apps/web/`)**: Next.js 15 (React 19) + TypeScript + Tailwind v4. It acts as a static consumer (SSG/ISR) of the Lite Registry.
3. **Lite Registry**: A single `registry.json` hosted on GitHub Pages acts as the database. Registration and updates happen via GitHub PRs (IssueOps), *not* via a write API.

## Response Format

When providing code modifications:
- Include a `# file: path/to/file.py` (or appropriate language comment) before the code block.
- Provide sufficient context (lines before/after) to make the change clear.
- Stick to the current architecture choices located in `pyproject.toml` unless changes are explicitly discussed.