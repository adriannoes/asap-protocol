# Analysis: Transforming pipefy-mcp-server into a Pipefy CLI

> **Repository**: https://github.com/gbrlcustodio/pipefy-mcp-server
> **Branch analyzed**: `pipe-full-toolset`
> **Date**: 2026-04-03

## 1. Executive Summary

The `pipefy-mcp-server` project has an **excellent architecture for CLI extraction**. The codebase follows a clean Facade pattern where the MCP layer (`tools/`) is a thin wrapper over a fully independent service layer (`services/pipefy/`). Transforming it into a CLI is **technically feasible with moderate effort**, and the service layer can be reused almost entirely without modification.

**Difficulty rating: MODERATE** — The core business logic is already decoupled from MCP transport. The main work is building a CLI interface layer (using `click` or `typer`) that replaces the MCP tool registration with CLI commands.

---

## 2. Architecture Analysis

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────┐
│  MCP Transport (stdio)                      │  ← Would be REPLACED by CLI
│  server.py → FastMCP.run()                  │
├─────────────────────────────────────────────┤
│  Tool Registration Layer                    │  ← Would be REPLACED by CLI commands
│  tools/*.py → @mcp.tool decorators          │
│  tools/registry.py                          │
├─────────────────────────────────────────────┤
│  Facade Client                              │  ← REUSABLE as-is
│  services/pipefy/client.py → PipefyClient   │
├─────────────────────────────────────────────┤
│  Domain Services                            │  ← REUSABLE as-is
│  services/pipefy/*_service.py               │
├─────────────────────────────────────────────┤
│  GraphQL Infrastructure                     │  ← REUSABLE as-is
│  services/pipefy/base_client.py             │
│  services/pipefy/internal_api_client.py     │
├─────────────────────────────────────────────┤
│  Configuration                              │  ← REUSABLE as-is
│  settings.py → pydantic-settings + .env     │
├─────────────────────────────────────────────┤
│  Models                                     │  ← REUSABLE as-is
│  models/*.py → Pydantic v2                  │
└─────────────────────────────────────────────┘
```

### 2.2 What CAN be reused (no changes)

| Component | Files | Lines (approx.) | Notes |
|-----------|-------|-----------------|-------|
| `PipefyClient` (Facade) | `client.py` | ~1125 | Pure delegation, no MCP dependency |
| Domain Services | 12 `*_service.py` files | ~2000+ | Zero MCP imports |
| GraphQL Base | `base_client.py` | ~78 | Transport layer to Pipefy API |
| Internal API Client | `internal_api_client.py` | ~72 | AI Automation endpoint |
| Settings | `settings.py` | ~54 | pydantic-settings, env vars |
| Models | `models/*.py` | ~200+ | Pydantic v2, no MCP deps |
| Queries | `queries/*.py` | ~500+ | Pure GraphQL documents |
| DI Container | `core/container.py` | ~55 | Service wiring |

### 2.3 What MUST be replaced

| Component | Current | CLI Replacement |
|-----------|---------|-----------------|
| `server.py` | `FastMCP` app + lifespan | CLI entrypoint (`typer.Typer()` or `click.Group()`) |
| `tools/*.py` (13 files) | `@mcp.tool` decorators | `@app.command()` decorators |
| `tools/registry.py` | Tool registration | Not needed (CLI auto-discovers commands) |
| `main.py` | `run_server()` | CLI `app()` invocation |
| MCP-specific features | `ctx.elicit()`, `ctx.debug()` | `typer.prompt()`, `rich.console` |

### 2.4 Coupling points to MCP

The tools layer has these MCP-specific dependencies:

1. **`mcp.server.fastmcp.FastMCP`** — Used in `server.py` and all `tools/*.py` for `@mcp.tool`
2. **`mcp.server.fastmcp.Context`** — Used in `pipe_tools.py`, some others for `ctx.elicit()` and `ctx.debug()`
3. **`mcp.types.ToolAnnotations`** — Metadata hints (`readOnlyHint`, `destructiveHint`)
4. **`mcp.server.session.ServerSession`** — Session type for elicitation capability check

**Key finding**: These imports are **confined exclusively to `tools/*.py` and `server.py`**. The service layer (`services/`, `models/`, `settings.py`, `core/`) has **zero MCP imports**.

---

## 3. CLI Transformation Strategy

### 3.1 Recommended approach: Dual-mode (MCP + CLI in same package)

Instead of forking, add a CLI module alongside the existing MCP server:

```
src/pipefy_mcp/
├── cli/                    # NEW: CLI layer
│   ├── __init__.py
│   ├── app.py              # typer.Typer() root
│   ├── pipes.py            # pipe commands
│   ├── cards.py            # card commands
│   ├── tables.py           # table commands
│   ├── reports.py          # report commands
│   ├── automations.py      # automation commands
│   ├── members.py          # member commands
│   ├── formatters.py       # rich output formatting
│   └── common.py           # shared CLI utilities
├── server.py               # EXISTING: MCP server (unchanged)
├── tools/                  # EXISTING: MCP tools (unchanged)
├── services/               # SHARED: used by both CLI and MCP
├── models/                 # SHARED
├── settings.py             # SHARED
└── core/                   # SHARED
```

### 3.2 CLI Example (using Typer + Rich)

```python
# cli/app.py
import typer
from pipefy_mcp.cli.pipes import pipes_app
from pipefy_mcp.cli.cards import cards_app

app = typer.Typer(name="pipefy", help="Pipefy CLI")
app.add_typer(pipes_app, name="pipes")
app.add_typer(cards_app, name="cards")

# cli/pipes.py
import asyncio
import typer
from rich.console import Console
from rich.table import Table
from pipefy_mcp.core.container import ServicesContainer
from pipefy_mcp.settings import settings

pipes_app = typer.Typer(help="Manage Pipefy pipes")
console = Console()

@pipes_app.command("list")
def list_pipes(name: str = typer.Option(None, help="Filter by pipe name")):
    """Search for pipes across all organizations."""
    container = ServicesContainer.get_instance()
    container.initialize_services(settings)
    result = asyncio.run(container.pipefy_client.search_pipes(name))
    # ... format with Rich tables
```

### 3.3 Pyproject.toml changes

```toml
[project.scripts]
pipefy-mcp-server = "pipefy_mcp.main:main"       # existing
pipefy = "pipefy_mcp.cli.app:app"                 # new CLI

[project.optional-dependencies]
cli = ["typer>=0.12", "rich>=13.0"]
```

---

## 4. Effort Breakdown

### 4.1 Components to build

| Task | Complexity | Description |
|------|-----------|-------------|
| CLI framework setup | Low | Add `typer` + `rich`, create `cli/app.py` |
| Pipe commands (~8) | Low | Thin wrappers over `PipefyClient` |
| Card commands (~12) | Medium | Includes interactive field input (replaces `ctx.elicit`) |
| Table commands (~12) | Low | Direct delegation |
| Report commands (~10) | Low | Direct delegation + output formatting |
| Automation commands (~8) | Low | Direct delegation |
| Member/webhook commands (~6) | Low | Direct delegation |
| Introspection commands (~4) | Low | Direct delegation |
| AI agent/automation commands (~8) | Low | Direct delegation |
| Output formatters | Medium | Rich tables, JSON output, CSV export |
| Async wrapper | Low | `asyncio.run()` bridge for sync CLI |
| Error handling | Low | Map exceptions to CLI-friendly messages |
| Tests | Medium | Mirror existing test patterns with CLI runner |

### 4.2 Key Challenges

1. **Async → Sync bridge**: All services are `async`. CLI needs `asyncio.run()` wrapper or use `anyio`. Straightforward but touches every command.

2. **Interactive elicitation**: `create_card` and `fill_card_phase_fields` use MCP's `ctx.elicit()` for dynamic form generation. CLI equivalent would use `typer.prompt()` or `questionary` for each field — requires reimplementing the dynamic form logic.

3. **108 tools → CLI commands**: Not all 108 tools need CLI equivalents. A reasonable first pass would cover the top 30-40 most used operations. The rest can be added incrementally.

4. **Output formatting**: MCP returns raw dicts. CLI needs human-readable output (Rich tables, colored JSON, etc.). This is new code but well-understood.

5. **Destructive operation guards**: The `destructive_tool_guard.py` pattern (preview → confirm) translates naturally to `typer.confirm()`.

---

## 5. Dependencies Impact

### Current dependencies (runtime)
- `gql[httpx]` — GraphQL client ✅ Keep
- `httpx-auth` — OAuth2 ✅ Keep
- `mcp[cli]` — MCP server ⚠️ Optional for CLI-only
- `pydantic` + `pydantic-settings` — ✅ Keep
- `openpyxl` — XLSX handling ✅ Keep
- `rapidfuzz` — Fuzzy matching ✅ Keep

### New dependencies for CLI
- `typer` — CLI framework (~modern Click wrapper)
- `rich` — Terminal formatting (already a typer dependency)
- `questionary` (optional) — Interactive prompts for dynamic forms

### Dependency strategy
Make `mcp[cli]` optional so the package can be installed in CLI-only mode:

```toml
[project.optional-dependencies]
mcp = ["mcp[cli]>=1.25.0"]
cli = ["typer>=0.12"]
```

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing MCP server | High | Dual-mode approach keeps MCP untouched |
| Async complexity in CLI | Low | Well-known pattern with `asyncio.run()` |
| 108 commands is overwhelming UX | Medium | Group into subcommands, implement top 30 first |
| OAuth token caching in CLI | Low | `httpx-auth` handles this transparently |
| Dynamic forms in CLI | Medium | Use `questionary` or simplify to JSON input |

---

## 7. Recommendation

**Go for it.** The architecture is already CLI-ready by design. The service layer (`PipefyClient` + domain services) is completely decoupled from MCP and can be wrapped by any interface layer.

### Suggested approach:
1. **Phase 1**: Add `cli/` module with core pipe/card/table commands (~30 commands)
2. **Phase 2**: Add report, automation, and observability commands
3. **Phase 3**: Add interactive features (dynamic forms, Rich dashboards)

### Alternative approach (if you prefer a separate project):
Extract `services/`, `models/`, `settings.py`, and `core/` into a `pipefy-sdk` package, then have both `pipefy-mcp-server` and `pipefy-cli` depend on it. This is cleaner long-term but more organizational overhead upfront.
