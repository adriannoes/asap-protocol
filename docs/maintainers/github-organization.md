# GitHub organization cutover (`asap-protocol`)

Canonical repository after transfer: **`asap-protocol/asap-protocol`**.

GitHub redirects `adriannoes/asap-protocol` URLs for a long time, but **Trusted Publishing**, **Pages**, **secrets**, and **third-party apps** must be updated explicitly.

## Already handled in-repo

- Package metadata (`pyproject.toml`, TypeScript `package.json` repository URLs)
- Default IssueOps / registry owner (`GITHUB_REGISTRY_OWNER` → `asap-protocol`)
- Default revocation / registry raw URLs under `asap-protocol/asap-protocol`
- Telemetry collector default owner
- Docs, MkDocs `site_url` / `repo_url`, SECURITY advisory links, Helm/k8s/GHCR examples

## Do not change without a migration plan

JWT identity claim default remains:

`https://github.com/adriannoes/asap-protocol/agent_id`

That string is a **claim name**, not a fetch URL. Renaming it breaks IdPs that already emit the old claim. Future canonical claim: `https://asap-protocol.com/agent_id` (see security docs).

## Maintainer checklist (consoles)

### 1. PyPI Trusted Publishing

For projects **`asap-protocol`** and **`asap-compliance`** on [pypi.org](https://pypi.org/):

1. Publishing → Trusted publishers
2. Edit or add GitHub Actions publisher
3. Set **Owner** / **Repository** to `asap-protocol` / `asap-protocol`
4. Workflow: `.github/workflows/release.yml` (same as before)

### 2. npm Trusted Publishers

For `@asap-protocol/client`, `@asap-protocol/mastra`, `@asap-protocol/openai-agents`:

1. Package → Settings → Trusted Publisher
2. Repository: `asap-protocol/asap-protocol`
3. Workflows: `publish-typescript.yml`, `hotfix-release.yml` (see [npm-publishing.md](./npm-publishing.md))

### 3. Repository / org Actions secrets

Confirm on the **org repo** (Settings → Secrets and variables → Actions):

| Secret | Used by |
|--------|---------|
| `CODECOV_TOKEN` | `.github/workflows/ci.yml` (optional for green CI; `fail_ci_if_error: false`) |
| `TELEMETRY_GITHUB_TOKEN` | `.github/workflows/telemetry-weekly.yml` |
| `TELEMETRY_TOKEN` | Telemetry weekly + web `/api/telemetry` |
| `NPM_TOKEN` / emergency tokens | Break-glass only; prefer OIDC |

Re-install the **Codecov** GitHub App for the `asap-protocol` organization if uploads stop.

### 4. GitHub Pages (MkDocs)

1. Repo → Settings → Pages
2. Source: branch **`gh-pages`**, folder `/ (root)`
3. Canonical URL: `https://asap-protocol.github.io/asap-protocol/`
4. Push to `main` triggers `.github/workflows/docs.yml`

### 5. GHCR

Release pushes `ghcr.io/asap-protocol/asap-protocol`. Ensure the org allows Actions to write packages. Old `ghcr.io/adriannoes/asap-protocol` tags remain under the previous namespace.

### 6. Vercel + OAuth

1. Reconnect the Vercel Git integration to `asap-protocol/asap-protocol`
2. Set `GITHUB_REGISTRY_OWNER=asap-protocol` (optional if relying on code defaults)
3. Update GitHub OAuth App callback URLs if they were personal-account scoped

### 7. Local clones

```bash
git remote set-url origin https://github.com/asap-protocol/asap-protocol.git
```

This points the local remote at the organization repository.

## Smoke after cutover

1. CI green on a PR under the org
2. Tag dry-run / next release: PyPI + npm OIDC succeed
3. Pages deploy reachable at `asap-protocol.github.io`
4. `docker pull ghcr.io/asap-protocol/asap-protocol:latest` (after next release image)
5. Web IssueOps “Register agent” opens issues on `asap-protocol/asap-protocol`
