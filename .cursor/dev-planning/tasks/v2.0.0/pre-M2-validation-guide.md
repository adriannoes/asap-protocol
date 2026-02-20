# Pre-M2 Validation Guide

> **Goal**: Validate that all critical commands and integrations work *before* building Sprint M2 features.
> **Why**: Avoid building the full frontend, deploying to Vercel, and discovering that registration/registry flows fail in production.

---

## Summary of Findings (Pre-Validation)

| Item | Status | Notes |
|------|--------|-------|
| `registry.json` | ✅ **Added** | Created at repo root; push to GitHub for fetch to work; update URL if using separate registry repo |
| `asap-protocol/registry` repo | ⚠️ **Missing** | Sprint M2 assumes this repo exists for Fork → PR flow |
| OAuth scope `public_repo` | ✅ OK | Already configured in `auth.ts` |
| Access token in session | ⚠️ **Unverified** | NextAuth must expose `access_token` for Octokit (server-side only) |
| `lib/registry.ts` fetch | ⚠️ **Returns []** | Falls back to empty array on 404; browse will show no agents |

---

## Prerequisites to Fix Before M2

### 1. Registry Data Source

**Decision needed**: Where does `registry.json` live?

| Option | Repo | URL | Pros | Cons |
|--------|------|-----|------|------|
| A | `asap-protocol/asap-protocol` (main) | `.../main/registry.json` | Single repo, simple | Mixes protocol code with registry data |
| B | `asap-protocol/registry` (new) | `.../registry/main/registry.json` | Clean separation, GitHub Pages | Repo must be created |
| C | `adriannoes/asap-protocol` (fork) | Current `lib/registry.ts` default | Works for dev | Not canonical for production |

**Recommendation**: Create `asap-protocol/registry` with a minimal `registry.json` (empty array `[]` or sample entry) and enable GitHub Pages. Update `lib/registry.ts` and `NEXT_PUBLIC_REGISTRY_URL` to point to it.

**Minimal `registry.json`**:
```json
[]
```

---

### 2. Access Token for GitHub API

The registration flow needs the user's GitHub token to create a fork and PR. NextAuth v5 does not include it by default.

**Add to `auth.ts`** (JWT callback):
```typescript
jwt({ token, user, account, profile }) {
  if (account?.access_token) {
    token.accessToken = account.access_token;
  }
  // ... existing logic
}
```

**Session callback** (optional, for type safety):
```typescript
session({ session, token }) {
  if (token.accessToken && session.user) {
    (session as any).accessToken = token.accessToken; // Server-side only
  }
  // ... existing logic
}
```

**Usage**: In Server Actions / API routes, use `auth()` or `getToken()` to get the token and pass to Octokit.

---

## Validation Scripts

### Script 1: Registry Fetch (Smoke Test)

Run from `apps/web`:

```bash
cd apps/web && node -e "
const url = process.env.NEXT_PUBLIC_REGISTRY_URL || 'https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json';
fetch(url).then(r => {
  console.log('Status:', r.status);
  return r.json();
}).then(d => console.log('Agents:', Array.isArray(d) ? d.length : 'not array')).catch(e => console.error(e));
"
```

**Expected**: `Status: 200`, `Agents: N` (or 0). If 404, fix registry source first.

---

### Script 2: GitHub API Flow (Manual / Dry Run)

**Prerequisites**:
- Personal Access Token (PAT) with `repo` scope
- Target repo exists (e.g. `asap-protocol/registry` or `asap-protocol/asap-protocol`)

**Steps**:
1. Script exists: `apps/web/scripts/validate-github-pr-flow.mjs`
2. Run: `GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs`
3. To test against your fork (if `asap-protocol/registry` doesn't exist):  
   `GITHUB_REGISTRY_OWNER=adriannoes GITHUB_REGISTRY_REPO=asap-protocol GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs`
4. Dry-run (repo check only): `DRY_RUN=1 ... GITHUB_TOKEN=<pat> node ...`

**Script** (`validate-github-pr-flow.mjs`):

```javascript
#!/usr/bin/env node
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

**Note**: Install Octokit first: `cd apps/web && npm install octokit`

---

### Script 3: OAuth Token Flow (Post Auth Fix)

After adding `accessToken` to the JWT:

1. Log in via the app (local or Vercel preview)
2. Add a temporary API route `/api/debug/token` that returns `!!token` (boolean) — never the actual token
3. Verify it returns `true` when logged in

---

## Checklist Before Starting Sprint M2

- [ ] **Registry source defined**: `registry.json` exists and is fetchable (200)
- [ ] **GitHub repo exists**: `asap-protocol/registry` (or chosen repo) is created
- [ ] **Access token in session**: NextAuth exposes token for server-side Octokit
- [ ] **Script 1 passes**: Registry fetch returns 200
- [ ] **Script 2 passes**: Fork → Branch → File → PR flow works with PAT
- [ ] **OAuth scopes**: `read:user public_repo` confirmed (already in `auth.ts`)

---

## Recommended Order

1. **Create registry repo** (if using Option B) and add minimal `registry.json`
2. **Run Script 1** to confirm fetch works
3. **Run Script 2** with your PAT to validate full GitHub flow
4. **Add access token to NextAuth** and verify with Script 3
5. **Start Sprint M2** with confidence

---

## References

- [ADR-18](.cursor/product-specs/decision-records/05-product-strategy.md) — GitHub OAuth + automated PR
- [Sprint M2](./sprint-M2-webapp-features.md) — Task 2.4 Register Agent Flow
- [Octokit createPullRequest plugin](https://www.npmjs.com/package/octokit-plugin-create-pull-request) — Alternative: single call for fork+PR
