# Pre-M2 Validation Guide

> **Goal**: Validate that all critical commands and integrations work *before* building Sprint M2 features.
> **Why**: Avoid building the full frontend, deploying to Vercel, and discovering that registration/registry flows fail in production.

---

## Summary of Findings (Pre-Validation)

| Item | Status | Notes |
|------|--------|-------|
| `registry.json` | ✅ **Live** | At repo root, pushed to `main`; public and fetchable |
| Registry location | ✅ **Option A** | Lives in `asap-protocol/asap-protocol` (main repo) |
| OAuth scope `public_repo` | ✅ OK | Already configured in `auth.ts` |
| Access token in JWT | ✅ **Done** | Stored in `auth.ts` JWT callback; verified via `/api/debug/token` |
| `lib/registry.ts` fetch | ✅ **Ready** | URL points to `adriannoes/asap-protocol/main/registry.json` |

---

## Prerequisites to Fix Before M2

### 1. Registry Data Source

**Decision**: `registry.json` lives at repo root (Option A). Public and safe — contains only agent metadata (endpoints, skills, description), no secrets. See [ADR-15 Update (2026-02-19)](../../product-specs/decision-records/05-product-strategy.md#question-15-lite-registry-for-v11-discovery-gap).

| Option | Repo | URL | Status |
|--------|------|-----|--------|
| A | `adriannoes/asap-protocol` | `.../main/registry.json` | ✅ **Active** |
| B | `asap-protocol/registry` (separate) | `.../registry/main/registry.json` | Deferred; can migrate later |

**Current `registry.json`**: Array `[]` at repo root. Add entries via PR (Sprint M2 registration flow).

---

### 2. Access Token for GitHub API ✅ Done

Implemented in `auth.ts`: JWT callback stores `account.access_token` in `token.accessToken`. Use `getToken()` in Server Actions / API routes to retrieve it for Octokit. Debug route: `/api/debug/token` (returns `hasToken` boolean — remove before production).

---

## Validation Scripts

### Script 1: Registry Fetch (Smoke Test)

```bash
node apps/web/scripts/validate-registry-fetch.mjs
```

**Expected**: `Status: 200`, `Agents: 0` (or N). If 404, check registry URL and branch.

---

### Script 2: GitHub API Flow (Manual / Dry Run)

**Prerequisites**:
- Personal Access Token (PAT) with `repo` scope
- Target repo exists (e.g. `asap-protocol/registry` or `asap-protocol/asap-protocol`)

**Steps**:
1. Run with current repo (registry in main):  
   `GITHUB_REGISTRY_OWNER=adriannoes GITHUB_REGISTRY_REPO=asap-protocol GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs`
2. Dry-run (repo check only):  
   `DRY_RUN=1 GITHUB_REGISTRY_OWNER=adriannoes GITHUB_REGISTRY_REPO=asap-protocol GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs`

**Implementation note**: Script fetches `sha` of existing `registry.json` before `createOrUpdateFileContents` (GitHub API requires it when updating). See `apps/web/scripts/validate-github-pr-flow.mjs`. Octokit installed. PAT must have `repo` scope.

```javascript
// (abbreviated - see apps/web/scripts/validate-github-pr-flow.mjs)
/**
 * Pre-M2 validation: Test GitHub API flow for agent registration.
 * Run: GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs
 * Requires: repo scope on PAT.
 */
import { Octokit } from 'octokit';

const token = process.env.GITHUB_TOKEN;
if (!token) {
  console.error('Set GITHUB_TOKEN');
  process.exit(1);
}

const OWNER = 'asap-protocol';
const REPO = 'registry'; // or 'asap-protocol' if registry lives in main repo
const octokit = new Octokit({ auth: token });

async function main() {
  try {
    // 1. Check repo exists
    const { data: repo } = await octokit.rest.repos.get({ owner: OWNER, repo: REPO });
    console.log('✓ Repo exists:', repo.full_name);

    // 2. Get default branch
    const defaultBranch = repo.default_branch || 'main';
    console.log('✓ Default branch:', defaultBranch);

    // 3. Get current registry.json (if exists)
    let currentContent = '[]';
    try {
      const { data } = await octokit.rest.repos.getContent({
        owner: OWNER,
        repo: REPO,
        path: 'registry.json',
      });
      if ('content' in data && data.content) {
        currentContent = Buffer.from(data.content, 'base64').toString();
      }
    } catch (e) {
      if (e.status === 404) console.log('⚠ registry.json not found (will create)');
      else throw e;
    }

    // 4. Fork (uses authenticated user)
    const { data: fork } = await octokit.rest.repos.createFork({ owner: OWNER, repo: REPO });
    console.log('✓ Fork created:', fork.full_name);

    // 5. Create branch on fork
    const branchName = 'register/test-agent-' + Date.now();
    const { data: ref } = await octokit.rest.git.getRef({
      owner: fork.owner.login,
      repo: fork.name,
      ref: 'heads/' + defaultBranch,
    });
    await octokit.rest.git.createRef({
      owner: fork.owner.login,
      repo: fork.name,
      ref: 'refs/heads/' + branchName,
      sha: ref.object.sha,
    });
    console.log('✓ Branch created:', branchName);

    // 6. Add/update registry.json
    const newEntry = {
      id: 'urn:asap:test-agent-' + Date.now(),
      name: 'test-agent',
      description: 'Pre-M2 validation test',
      endpoints: { http: 'https://example.com/asap' },
      skills: ['test'],
    };
    const registry = JSON.parse(currentContent);
    if (!Array.isArray(registry)) throw new Error('registry.json must be array');
    registry.push(newEntry);
    const newContent = JSON.stringify(registry, null, 2);

    await octokit.rest.repos.createOrUpdateFileContents({
      owner: fork.owner.login,
      repo: fork.name,
      path: 'registry.json',
      message: 'chore: pre-M2 validation test',
      content: Buffer.from(newContent).toString('base64'),
      branch: branchName,
    });
    console.log('✓ File updated');

    // 7. Create PR
    const { data: pr } = await octokit.rest.pulls.create({
      owner: OWNER,
      repo: REPO,
      title: 'Register Agent: test-agent (Pre-M2 validation)',
      head: fork.owner.login + ':' + branchName,
      base: defaultBranch,
      body: 'Automated registration via Marketplace. **Pre-M2 validation test** — safe to close.',
    });
    console.log('✓ PR created:', pr.html_url);
    console.log('\n✅ All steps passed. GitHub flow is ready for M2.');
  } catch (err) {
    console.error('❌ Error:', err.message);
    if (err.response) console.error('   Status:', err.response.status, err.response.data);
    process.exit(1);
  }
}

main();
```

---

### Script 3: OAuth Token Flow (Verify)

1. **Log out** (if already logged in) — the token is stored only on sign-in
2. **Log in** via the app (local or Vercel preview)
3. **GET** `http://localhost:3000/api/debug/token` in the **browser** (curl won't send session cookie)
4. **Expected**: `{ "hasToken": true, "username": "..." }`

---

## Checklist Before Starting Sprint M2

- [x] **Registry source defined**: `registry.json` at repo root, fetchable (200)
- [x] **Registry public**: Safe — metadata only, no secrets
- [x] **Script 1 passes**: Registry fetch returns 200 ✅
- [x] **Script 2 passes**: Fork → Branch → File → PR flow ✅
- [x] **Access token in JWT**: NextAuth stores `access_token` for server-side Octokit
- [x] **OAuth scopes**: `read:user public_repo` confirmed (already in `auth.ts`)

---

## Validation History (2026-02-19)

| Step | Action | Result |
|------|--------|--------|
| 1 | Created `registry.json` at repo root, pushed to `main` | ✅ Fetch returns 200 |
| 2 | Added ADR-15 update (Registry Location) to decision records | ✅ Documented |
| 3 | Script 1: `validate-registry-fetch.mjs` | ✅ Pass |
| 4 | Script 2: `validate-github-pr-flow.mjs` — fixed `sha` required for `createOrUpdateFileContents` | ✅ Pass (PR #55) |
| 5 | Added `access_token` to JWT in `auth.ts` | ✅ Done |
| 6 | Created `/api/debug/token` for verification | ✅ Pass (`hasToken: true`) |
| 7 | All pre-M2 checks complete | ✅ **Ready for Sprint M2** |

---

## Test Results (Latest Run)

| Script | Result | Notes |
|--------|--------|-------|
| Script 1 (Registry fetch) | ✅ Pass | Status 200, Agents: 0 |
| Script 2 (GitHub PR flow) | ✅ Pass | Fork → Branch → File → PR (sha fix applied) |
| Script 3 (OAuth token) | ✅ Pass | `hasToken: true`, `username: adriannoes` |

---

## Before Production

- `/api/debug/token` — protected:
  - Returns 404 when `NODE_ENV === 'production'` or `VERCEL_ENV === 'production'`
  - If `DEBUG_TOKEN` env var is set, requires `X-Debug-Token` header to match (defense in depth)
  - Available in dev/preview only

---

## References

- [ADR-18](.cursor/product-specs/decision-records/05-product-strategy.md) — GitHub OAuth + automated PR
- [Sprint M2](./sprint-M2-webapp-features.md) — Task 2.4 Register Agent Flow
- [Octokit createPullRequest plugin](https://www.npmjs.com/package/octokit-plugin-create-pull-request) — Alternative: single call for fork+PR
