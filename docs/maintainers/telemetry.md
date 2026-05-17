# Telemetry runbook (weekly adoption snapshot)

Maintainers use `scripts/telemetry/` to build an **aggregate JSON snapshot** plus a **markdown dashboard** for adoption signals (npm/PyPI/GitHub/registry, optional site CTR, and **adapter-request** issue counts). Outputs default to **`private/telemetry/`** (gitignored — see repo `.gitignore`).

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** per `pyproject.toml`
- **Network** access to npm, PyPI Stats (`pypistats` extra), GitHub API, and the registry mirror URL

Sync dependencies (includes the `telemetry` extra):

```bash
uv sync --frozen --all-extras --dev
```

The above command installs Python deps from the lockfile and enables the PyPI collector (`pypistats`).

## Tokens and secrets

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_TOKEN` | For GitHub traffic + issues | Classic PAT with **`repo`** scope (traffic endpoints require push-equivalent access to the target repository), **or** a fine-grained token with **Contents: Read** and **Issues: Read** plus traffic access as allowed by GitHub for that token type. **Never commit this token.** |
| `TELEMETRY_TOKEN` | For `/api/telemetry` only | Shared bearer for the Next.js route `apps/web/src/app/api/telemetry/route.ts`. Set in Vercel/hosting env; use the same value when calling the route locally or from `aggregate.py`. |
| `TELEMETRY_SITE_ENDPOINT` | Optional | Full URL to the deployed telemetry route, e.g. `https://example.com/api/telemetry`. Passed to `aggregate.py` or set in CI **repository variables**. |

### Site metrics without a public analytics API

Vercel Web Analytics **does not** expose aggregate event/CTR APIs for arbitrary server-side pulls (see Vercel docs and community threads). The web route therefore supports:

- Optional env **`TELEMETRY_SITE_METRICS_JSON`** on the **Next.js server** — non-secret JSON merged into `ctr_per_cta` (for example values pasted from a dashboard export or a drain pipeline).

CI can omit `TELEMETRY_SITE_ENDPOINT`; the snapshot will still include an empty `site.ctr_per_cta` with a note.

## Running collectors individually

**npm** (public API):

```bash
uv run python scripts/telemetry/collect_npm.py --period last-week -o /tmp/npm.json
```

**PyPI** (`pypistats`):

```bash
uv run python scripts/telemetry/collect_pypi.py -o /tmp/pypi.json
```

**GitHub** (summary, traffic, referrers, **open `adapter-request` issues**):

```bash
export GITHUB_TOKEN=…
uv run python scripts/telemetry/collect_github.py -o /tmp/github.json
```

**Registry** (agent count + optional `--previous`):

```bash
uv run python scripts/telemetry/collect_registry.py -o /tmp/registry.json
```

## Weekly aggregate (snapshot + dashboard)

```bash
export GITHUB_TOKEN=…
export TELEMETRY_TOKEN=…   # optional if fetching site
export TELEMETRY_SITE_ENDPOINT=https://YOUR_HOST/api/telemetry   # optional
uv run python scripts/telemetry/aggregate.py --output-dir private/telemetry
```

The script:

- Validates the snapshot against an embedded **JSON Schema** (`jsonschema`).
- Writes `snapshot-YYYY-MM-DD.json`, `dashboard.md`, and attempts `snapshot-latest.json` → symlink (may fail on Windows without symlink rights — optional).

## Adapter-request issues

Ensure the GitHub label **`adapter-request`** exists on the repository (Settings → Labels) so the issue template and automation apply it correctly.

Issues labeled **`adapter-request`** are grouped by **framework name** parsed from the issue body:

1. GitHub Issue Form heading: `### Framework name` (or `### Framework`) followed by the value on the next line.
2. Free-form line: `Framework: My Framework Name` (case-insensitive).

The aggregator stores **slugified** keys (e.g. `OpenAI Agents SDK` → `openai-agents-sdk`). Issues that cannot be parsed increment **`_unparsed`** in the snapshot and dashboard.

## CI artifacts

Workflow **`.github/workflows/telemetry-weekly.yml`** runs on a weekly schedule and **`workflow_dispatch`**. It **does not push to `main`**; it uploads **`snapshot-*.json`** and **`dashboard.md`** as a **workflow artifact**.

Optional: download the artifact and copy files to a **private branch** if you want historical copies in git (not required for promotion-gate review).

## Revoking access

- **Rotate `GITHUB_TOKEN`** at the source (GitHub developer settings) and update Secrets/ENV wherever it was stored.
- **Rotate `TELEMETRY_TOKEN`** in the hosting provider, then update any automation (`TELEMETRY_TOKEN` / `TELEMETRY_SITE_ENDPOINT`) that calls `/api/telemetry`.

## Relevant code

- `scripts/telemetry/aggregate.py` — join + validate + `dashboard.md`
- `scripts/telemetry/collect_github.py` — `adapter_requests` breakdown
- `apps/web/src/app/api/telemetry/route.ts` — bearer-protected site metrics hook
