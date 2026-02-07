# AGENTS.md

> Instructions for AI coding agents working on ASAP Protocol.
> Compatible with Cursor, Copilot, Codex, Gemini CLI, Windsurf and other AI tools.

## Project Overview

ASAP (Async Simple Agent Protocol) is a production-ready protocol for agent-to-agent communication and task coordination. Built with Python 3.13+, Pydantic v2 and FastAPI.

- **Core**: Protocol models, state machines, and handlers
- **Transport**: HTTP client/server with compression, rate limiting, observability
- **CLI**: `asap` command for serving, validation,and tooling

## Setup Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/asap --cov-report=term-missing

# Start dev server
uv run asap serve --reload

# Type checking
uv run mypy src/

# Linting and formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Code Style

- **Python**: 3.13+ required (see `pyproject.toml`)
- **Type hints**: Required on all functions (mypy strict mode)
- **Formatting**: Ruff (double quotes, 100 char line length)
- **Async**: Use `async/await` for I/O operations
- **Models**: Pydantic v2 for all data models
- **Imports**: Use absolute imports from `asap.*`

## Project Structure

```
src/asap/
├── models/        # Pydantic models (Envelope, TaskRequest, etc.)
├── transport/     # HTTP client, server, middleware
├── handlers/      # Task processing logic
├── observability/ # Logging, tracing, metrics
└── cli.py         # CLI entry point
tests/             # pytest tests mirroring src/ structure
```

## Architecture & Design Decisions

- **ADR**: `.cursor/product-specs/ADR.md` - All architecture decisions
- **Tech Stack**: `.cursor/dev-planning/architecture/tech-stack-decisions.md` - Rationale for technology choices
- **Vision**: `.cursor/product-specs/vision-agent-marketplace.md` - Future roadmap
- **Roadmap**: `.cursor/product-specs/roadmap-to-marketplace.md` - v1.0 → v2.0 path

## Development Planning

- **Task Templates**: `.cursor/dev-planning/templates/task-template.md`
- **Sprint Tasks**: `.cursor/dev-planning/tasks/` (by version)
- **Code Reviews**: `.cursor/dev-planning/code-review/`

## AI Governance Matrix

We use a layered approach to guide AI Agents:

| Layer | Type | Directory | Purpose |
|-------|------|-----------|---------|
| **1. Law** | **Rules** | `.cursor/rules/` | **Context**. Passive instructions that must ALWAYS be followed (e.g. "Use Pydantic v2"). |
| **2. Actions** | **Commands** | `.cursor/commands/` | **Workflows**. Specific prompts for complex tasks (e.g. "Create PRD"). |
| **3. Tools** | **Skills** | `.cursor/skills/` | **Capabilities**. Agents defined with scripts and resources (e.g. "Security Review"). |

### 1. Rules (Context)
Files ending in `.mdc` indexed by Cursor.
-   `architecture-principles.mdc`: Core patterns.
-   `security-standards.mdc`: Zero Trust & Secrets.
-   `frontend-best-practices.mdc`: Next.js 15 & Tailwind v4.

### 2. Commands (Workflows)
Markdown prompts for standard procedures.
-   `create-prd.md`: Interactive interview to generate specs.
-   `generate-tasks.md`: Create Jira-like markdown tasks.

### 3. Skills (Capabilities)
Directories containing `SKILL.md` and `scripts/`.
-   `code-quality-review`: Conducts deep code analysis.
-   `security-review`: Conducts security audit.
-   `skill-creator`: Generates new Skills with standard structure.

## Testing

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/transport/

# With verbose output
uv run pytest -v

# Parallel (faster)
uv run pytest -n auto
```

**Test patterns**:
- Use `pytest-asyncio` for async tests
- Mock external services (never hit real APIs in tests)
- Rate limiters need isolation (see `testing-rate-limiting.mdc`)

## Important Patterns

1. **State Machine**: Tasks follow `PENDING → RUNNING → COMPLETED/FAILED`
2. **Envelope Protocol**: All messages wrapped in `Envelope[T]`
3. **Handler Registration**: `@server.handler("task_type")` decorator
4. **Circuit Breaker**: Client has retry + circuit breaker logic

## Security Notes

- Never commit secrets or API keys
- Use environment variables for configuration
- Rate limiting enabled by default
- mTLS optional (planned for v1.2.0)

## PR Guidelines

- Follow commit format in `.cursor/rules/git-commits.mdc`
- Review the [PR Template](.github/PULL_REQUEST_TEMPLATE.md) for self-review checklist
- All tests must pass
- Type checking clean (`mypy src/`)
- Coverage should not decrease
