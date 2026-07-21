# Registry Bot

Lightweight **FastAPI** service for **Lite Registry auto-registration** (`POST /registry/agents`). It is meant to run **next to** the main `asap-protocol` package: install the monorepo root as an editable dependency so future `asap.registry.auto_registration` code is importable without duplicating transport wiring.

## When the handler is missing

Until `asap.registry.auto_registration` ships in `src/asap/`, `POST /registry/agents` returns **503** with a JSON body explaining that the module is not available. `GET /health` always returns **200** for load balancers.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | For PR flow (current impl) | Fine-grained PAT or token with **contents** + **pull requests** write on the registry repo (used for `git clone` / `push` and REST `POST /repos/.../pulls`) |
| `GITHUB_REPOSITORY` | For PR flow | `owner/name` of the registry repo |
| `GITHUB_BASE_BRANCH` | No | Base branch for PRs (default `main`) |
| `GITHUB_APP_ID` | Planned | GitHub App numeric id when the worker exchanges a JWT for an installation token |
| `GITHUB_APP_PRIVATE_KEY` | Planned | PEM for the GitHub App (store as a secret; newline handling varies by host) |
| `GITHUB_INSTALLATION_ID` | Planned | Installation id for the target org/repo |
| `ASAP_AUTH_JWKS_URI` | Yes (prod) | JWKS endpoint for Bearer JWT validation (project standard; see main docs) |
| `ASAP_AUTH_ISSUER` | Optional | OIDC issuer when JWKS URI is discovered |
| `ASAP_AUTH_AUDIENCE` | Optional | Expected JWT audience |
| `ASAP_OAUTH_PUBLIC_KEY` | Alternative | If your deployment prefers a single PEM over JWKS, document the bridge in your worker; the core library validates via JWKS — align with ops or add a thin adapter in the worker |

Optional server binding:

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY_BOT_HOST` | `0.0.0.0` | Bind address |
| `PORT` / `REGISTRY_BOT_PORT` | `8080` | Listen port (`PORT` is common on PaaS) |

**Security**: never commit real keys; use the host’s secret store. Prefer **HTTPS** for all external URLs (manifest fetch, GitHub API, JWKS).

## Run locally (monorepo)

From `apps/registry-bot/`:

```bash
cd apps/registry-bot && uv sync && uv run uvicorn registry_bot.app:app --reload --host 127.0.0.1 --port 8080
```

Purpose: start the API with hot reload for local development.

## Deploy (Railway / Fly / VM)

1. Build context: **repository root** (so `uv` can resolve `asap-protocol` from `[tool.uv.sources]`).
2. Working directory: `apps/registry-bot`.
3. Start command:

```bash
cd apps/registry-bot && uv sync --frozen && uv run uvicorn registry_bot.app:app --host 0.0.0.0 --port ${PORT:-8080}
```

Purpose: production-style bind and use the platform’s `PORT`.

For **Docker**, copy the repo root, `uv sync` from `apps/registry-bot`, then the same `uvicorn` command.

## Vercel / serverless

Auto-registration is a **long-lived** HTTP service (manifest fetch, harness, GitHub API). **Serverless functions** are a poor fit unless you split “accept job → queue → worker”. Prefer Railway, Fly.io, Kubernetes, or a small VM. If you must use Vercel, run the **worker** elsewhere and keep only a thin edge if needed.

## Python worker integration

If you already run a **Celery/RQ/async worker** inside the monorepo:

- Keep **JWT validation** and **Compliance Harness** calls in the shared `asap-protocol` library when modules land.
- Use the GitHub App id + private key only in the worker (or in `registry-bot`) to open PRs; do not embed them in the public web app.
- Point this service’s dependency at the same editable `asap-protocol` path as CI so `import asap.registry.auto_registration` succeeds in lockstep with `main`.

**Import note:** Importing `asap.registry` pulls `asap.transport` (package `__init__` re-exports `create_app`), which builds the default `asap.transport.server:app` once. That is noisy in logs but harmless for a dedicated bot process.
