# Code Review: PR #57

> **Sprint M2 — Web App Features & Registry Browser**
> **Branch**: `feature/v2.0.0-sprint-M2-merge` → `main`
> **Reviewer**: Staff Engineer (AI)
> **Date**: 2026-02-20
> **Diff Stats**: 41 files changed, +5844 / -763 lines

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Aligned with tech-stack-decisions.md — Next.js 15, TypeScript, Tailwind, Shadcn, Zod, SWR. |
| **Architecture** | ⚠️ | Registration flow creates branches on main repo instead of forking (will fail for non-collaborators). |
| **Security** | ⚠️ | Hardcoded fallback encryption key in `auth.ts`; incomplete SSRF blocklist; token exposed in error messages. |
| **Tests** | ⚠️ | Good unit tests for UI components but no tests for server actions (the most critical security surface). |

> **General Feedback:** The PR delivers a solid and well-structured Sprint M2 with clean UI components, proper ISR configuration, and thoughtful Zod validation. The main areas requiring attention before merge are: (1) the hardcoded cryptographic fallback key, (2) the registration flow not using the fork-based pattern established in the pre-M2 validation script, and (3) server action test coverage.

---

## 2. Required Fixes (Must Address Before Merge)

### 2.1 CRITICAL: Hardcoded Fallback Encryption Key

*   **Location:** `apps/web/src/auth.ts:7`
*   **Severity:** Critical
*   **Problem:** The encryption key for JWE tokens falls back to a hardcoded, predictable string (`"default_secret_32_bytes_long_min"`) when `AUTH_SECRET` is not set. Any attacker reading the open-source code can decrypt user access tokens in environments where this variable is missing. This violates the project's Security Standards (§1 — No Hardcoded Secrets).
*   **Fix Suggestion:**

    ```typescript
    const authSecret = process.env.AUTH_SECRET;
    if (!authSecret) {
        throw new Error(
            "AUTH_SECRET environment variable is required. " +
            "Generate one with: npx auth secret"
        );
    }
    const secretKey = new TextEncoder().encode(authSecret.padEnd(32, '0').slice(0, 32));
    ```

*   **Verification:** Remove `AUTH_SECRET` from `.env.local` and confirm the app throws on startup instead of silently using the default.

---

### 2.2 Registration Flow Uses Branch-on-Main Instead of Fork

*   **Location:** `apps/web/src/app/dashboard/register/actions.ts:85-96`
*   **Severity:** High
*   **Problem:** The production registration code calls `octokit.rest.git.createRef()` directly on the upstream repo (`adriannoes/asap-protocol`). Regular GitHub users (non-collaborators) will receive a `403 Forbidden` error because they lack write access. The pre-M2 validation script (`validate-github-pr-flow.mjs`) correctly uses a fork-first pattern, but the production code does not replicate this.
*   **Fix Suggestion:** Mirror the validation script's fork-based flow:

    ```typescript
    // A. Fork the repository (idempotent — returns existing fork if already forked)
    const { data: fork } = await octokit.rest.repos.createFork({ owner, repo });

    // Wait briefly for fork to be ready (GitHub recommendation)
    await new Promise(resolve => setTimeout(resolve, 3000));

    // B. Get the SHA of the default branch from the fork
    const { data: refData } = await octokit.rest.git.getRef({
        owner: fork.owner.login,
        repo: fork.name,
        ref: `heads/${fork.default_branch}`,
    });
    const baseSha = refData.object.sha;

    // C. Create branch on the fork (not the upstream!)
    await octokit.rest.git.createRef({
        owner: fork.owner.login,
        repo: fork.name,
        ref: `refs/heads/${targetBranch}`,
        sha: baseSha,
    });

    // D-E. Update file and create PR using fork owner
    // ...use fork.owner.login and fork.name for file operations...

    // F. Create PR from fork to upstream
    const { data: prData } = await octokit.rest.pulls.create({
        owner,
        repo,
        title: `Register Agent: ${agentId}`,
        head: `${fork.owner.login}:${targetBranch}`,
        base: 'main',
        body: `...`,
    });
    ```

*   **Verification:** Log out, log in with a non-collaborator GitHub account, and attempt agent registration. Confirm a PR is created from a fork.

---

### 2.3 Incomplete SSRF Mitigation

*   **Location:** `apps/web/src/app/dashboard/register/actions.ts:57-67`
*   **Severity:** High
*   **Problem:** The private IP blocklist is incomplete. Missing checks for:
    -   `0.0.0.0` (binds to all interfaces)
    -   IPv6 loopback variations (`[::1]`, `[::ffff:127.0.0.1]`)
    -   Cloud metadata endpoints (`metadata.google.internal`, `metadata.aws.internal`)
    -   Hostname `[0]`, `[0x7f000001]` (hex/octal encoding)
    -   DNS rebinding attacks (hostname resolves to public IP initially, then private IP on fetch)

*   **Fix Suggestion:**

    ```typescript
    const BLOCKED_HOSTNAMES = new Set([
        'localhost', '127.0.0.1', '::1', '0.0.0.0',
        'metadata.google.internal', 'metadata.aws.internal',
        '169.254.169.254',
    ]);

    const isBlockedHostname = (hostname: string): boolean => {
        const lower = hostname.toLowerCase();
        if (BLOCKED_HOSTNAMES.has(lower)) return true;

        // Private IPv4 ranges
        if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.)/.test(lower)) return true;

        // IPv6-mapped IPv4
        if (/^::ffff:/.test(lower)) return true;

        return false;
    };

    if (isBlockedHostname(hostname)) {
        return { success: false, error: 'Internal/Private network addresses are not allowed.' };
    }
    ```

*   **Verification:** Unit test with inputs: `http://0.0.0.0:8080`, `http://[::ffff:127.0.0.1]/manifest`, `http://metadata.google.internal/computeMetadata/v1/`.

---

### 2.4 Debug Endpoint Should Not Exist in Codebase

*   **Location:** `apps/web/src/app/api/debug/token/route.ts`
*   **Severity:** Medium
*   **Problem:** This endpoint exposes information about whether a user has an access token and their username. While it has production guards, the route is deployed to Vercel preview environments (non-production, non-development) where `NODE_ENV` may not be `'production'` and `VERCEL_ENV` could be `'preview'`. The `DEBUG_TOKEN` env var may not be set in preview, leaving the endpoint completely open.
*   **Fix Suggestion:** Either:
    -   (A) Delete this file entirely — it was a pre-M2 validation tool. Or:
    -   (B) Add a third guard: `if (!debugToken) return NextResponse.json({ error: 'Not found' }, { status: 404 });`

    ```typescript
    // Fail-closed: if no DEBUG_TOKEN is configured, the endpoint is disabled
    if (!debugToken) {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }
    ```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### 3.1 `as any` Type Safety Bypass in Production Code

*   **Location:** `apps/web/src/app/dashboard/register/actions.ts:82,88`
*   **Severity:** Medium
*   **Problem:** Two `as any` casts in the `newAgent` construction:
    ```typescript
    version: "1.0.0" as any,
    skills: skillsList as any
    ```
    The `Manifest` type expects `Version` (which is `string`) for `version`, so the cast is unnecessary. For `skills`, the generated `Skill` interface expects `{ id: string; description: string; input_schema?: ...; output_schema?: ... }`, which the `skillsList` already satisfies. Using `Partial<Manifest>` and then pushing `as Manifest` further erodes type safety.
*   **Fix Suggestion:** Define a proper `RegistryEntry` type (a subset of `Manifest`) or use `Omit`/`Pick` to construct only the needed fields without `any`:

    ```typescript
    import type { Manifest, Skill } from '@/types/protocol';

    const skillsList: Skill[] = skills.split(',')
        .map(s => s.trim()).filter(Boolean)
        .map(s => ({ id: s, description: `Capability: ${s}` }));

    const newAgent: Omit<Manifest, 'ttl_seconds'> = {
        id: agentId,
        name: agentId.split(':').pop() ?? name,
        description,
        version: "1.0.0",
        endpoints: {
            asap: endpoint_http,
            ...(endpoint_ws ? { events: endpoint_ws } : {}),
        },
        capabilities: {
            asap_version: "0.1",
            skills: skillsList,
        },
    };
    ```

---

### 3.2 Redundant `as string` Assertions Throughout Components

*   **Location:** `apps/web/src/app/browse/browse-content.tsx` (lines with `agent.id as string`), `dashboard-client.tsx`
*   **Severity:** Low
*   **Problem:** The `Manifest.id` type is already `Id = string`, so `agent.id as string` is redundant. This pattern appears ~15 times across browse-content, dashboard-client, and agent-detail-client. It indicates lack of confidence in the generated types.
*   **Fix Suggestion:** Remove all `as string` casts on `Manifest` fields. If the issue is that the field could be `undefined` at runtime (despite the type), use optional chaining or nullish coalescing:
    ```typescript
    agent.id ?? ''
    ```

---

### 3.3 SWR Polling GitHub API at 10-Second Interval

*   **Location:** `apps/web/src/app/dashboard/dashboard-client.tsx:74`
*   **Severity:** Medium
*   **Problem:** The SWR hook polls `fetchUserPullRequests()` every 10 seconds. Each call hits the GitHub REST API via a server action. GitHub's rate limit for authenticated users is 5,000 requests/hour. With the dashboard open, a single user consumes 360 requests/hour. With multiple users or tabs, this could exhaust the rate limit quickly.
*   **Fix Suggestion:** Increase the interval to 60 seconds (sufficient for PR status which changes infrequently) and add an `onErrorRetry` handler that backs off on 429s:

    ```typescript
    const { data: prData } = useSWR('userPrs', async () => {
        const res = await fetchUserPullRequests();
        if (res.success && res.data) return res.data;
        return [];
    }, {
        refreshInterval: 60_000,
        onErrorRetry: (error, _key, _config, revalidate, { retryCount }) => {
            if (retryCount >= 3) return;
            setTimeout(() => revalidate({ retryCount }), 5000 * (retryCount + 1));
        },
    });
    ```

---

### 3.4 No Rate Limiting on Server Actions

*   **Location:** `apps/web/src/app/dashboard/register/actions.ts`, `apps/web/src/app/dashboard/actions.ts`
*   **Severity:** Medium
*   **Problem:** Server actions `submitAgentRegistration` and `fetchUserPullRequests` have no rate limiting. A malicious authenticated user could rapidly call `submitAgentRegistration` to:
    -   Create hundreds of branches/PRs on the registry repo
    -   Exhaust GitHub API tokens
    -   Flood the registry with duplicate entries
*   **Fix Suggestion:** Add basic rate limiting using a simple in-memory counter per user (acceptable for Vercel serverless since each cold start resets). For a more robust solution, consider using `next-rate-limit` or Vercel's Edge Config:

    ```typescript
    import { headers } from 'next/headers';

    const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

    function checkRateLimit(userId: string, maxRequests = 5, windowMs = 60_000): boolean {
        const now = Date.now();
        const entry = rateLimitMap.get(userId);
        if (!entry || now > entry.resetAt) {
            rateLimitMap.set(userId, { count: 1, resetAt: now + windowMs });
            return true;
        }
        if (entry.count >= maxRequests) return false;
        entry.count++;
        return true;
    }
    ```

---

## 4. Improvements & Refactoring (Highly Recommended)

### 4.1 Server Action Test Coverage

*   **Priority:** High
*   **Problem:** The most critical code paths — `register/actions.ts` (SSRF check, GitHub automation, token decryption) and `dashboard/actions.ts` (PR fetching with auth) — have zero test coverage. The existing tests only cover UI rendering and form validation.
*   **Recommendation:** Create `__tests__/actions.test.ts` for both server action files:
    -   Mock `Octokit` and `auth()` to test the happy path and error scenarios.
    -   Test SSRF blocklist with known bypass patterns.
    -   Test behavior when `encryptedAccessToken` is missing.
    -   Test behavior when GitHub API returns 403 (no write access).

---

### 4.2 Extract SSRF Validation to Shared Utility

*   **Priority:** Medium
*   **Problem:** The SSRF validation logic is inline in `register/actions.ts`. If another endpoint needs URL validation, the logic would be duplicated.
*   **Recommendation:** Extract to `src/lib/url-validator.ts`:
    ```typescript
    export function isAllowedExternalUrl(url: string): { valid: boolean; error?: string } {
        // Centralized SSRF validation
    }
    ```

---

### 4.3 Agent Ownership Model is Fragile

*   **Priority:** Medium
*   **Location:** `apps/web/src/app/dashboard/page.tsx:23`
*   **Problem:** Agent "ownership" is determined by checking if the agent ID contains the user's GitHub username:
    ```typescript
    const myAgents = username
        ? allAgents.filter(a => (a.id as string).toLowerCase().includes(username.toLowerCase()))
        : [];
    ```
    This has false positives: an agent with ID `urn:asap:agent:john:admin-tool` would match a user named `admin`. It also breaks if a user changes their GitHub username.
*   **Recommendation:** Use strict prefix matching on the expected URN format:
    ```typescript
    const prefix = `urn:asap:agent:${username.toLowerCase()}:`;
    const myAgents = allAgents.filter(a => a.id.toLowerCase().startsWith(prefix));
    ```

---

### 4.4 Missing Error Boundary for Client Components

*   **Priority:** Low
*   **Problem:** `BrowseContent`, `DashboardClient`, and `AgentDetailClient` lack React Error Boundaries. If any rendering error occurs (e.g., malformed registry data), the entire page crashes without a user-friendly message.
*   **Recommendation:** Add an `error.tsx` file in `app/browse/`, `app/dashboard/`, and `app/agents/[id]/` to leverage Next.js's built-in error boundary pattern:
    ```typescript
    'use client';
    export default function Error({ error, reset }: { error: Error; reset: () => void }) {
        return (
            <div className="text-center py-10">
                <h2>Something went wrong.</h2>
                <button onClick={() => reset()}>Try again</button>
            </div>
        );
    }
    ```

---

### 4.5 ADR & Documentation Quality

*   **Priority:** Low
*   **Observation:** The ADR-19 addition (npm overrides strategy) is well-reasoned and follows the existing ADR format. The roadmap progress updates are accurate. Minor nit: the `vercel-deploy-guide.md` addition is useful for onboarding.

---

## 5. Pre-Flight Check Summary

| Check | Status | Notes |
| :--- | :--- | :--- |
| Sync I/O in Async | ✅ N/A | PR is TypeScript/Next.js (frontend). No Python async paths affected. |
| `python-jose` usage | ✅ Pass | Not present. Uses `jose` (JS library) for JWE — correct for frontend. |
| Pydantic v1 syntax | ✅ N/A | No Python model changes. |
| JSON-RPC for actions | ✅ N/A | Web App uses REST/API Routes — JSON-RPC applies only to agent-to-agent transport per §1.3 note. |
| Well-known paths | ✅ N/A | No discovery endpoints modified. |
| Hardcoded secrets | ❌ Fail | Fallback key in `auth.ts:7`. See §2.1. |
| Zod validation | ✅ Pass | Both client and server schemas use Zod. |

---

## 6. Verification Steps

After applying fixes, the developer should verify with:

```bash
# 1. TypeScript strict checks
cd apps/web && npx tsc --noEmit

# 2. ESLint
cd apps/web && npm run lint

# 3. Unit tests (Vitest)
cd apps/web && npx vitest run

# 4. Build verification
cd apps/web && npm run build

# 5. Manual test: Registration flow with non-collaborator GitHub account
# (After fork-based fix is applied)

# 6. Manual test: Remove AUTH_SECRET and confirm app fails to start
# (After hardcoded key fix is applied)

# 7. Python CI (unchanged backend — sanity check)
uv run ruff check . && uv run mypy src/
```

---

## 7. Files Reviewed

| File | Verdict | Notes |
| :--- | :--- | :--- |
| `auth.ts` | ⚠️ Fix Required | Hardcoded fallback key (§2.1) |
| `register/actions.ts` | ⚠️ Fix Required | Fork flow (§2.2), SSRF (§2.3), `as any` (§3.1), no rate limit (§3.4) |
| `dashboard/actions.ts` | ✅ Acceptable | Minor: no tests, but logic is straightforward |
| `api/debug/token/route.ts` | ⚠️ Fix Required | Preview env exposure (§2.4) |
| `browse/page.tsx` | ✅ Good | Clean ISR usage |
| `browse/browse-content.tsx` | ✅ Good | Well-structured filtering logic |
| `agents/[id]/page.tsx` | ✅ Good | Proper ISR + generateStaticParams |
| `agents/[id]/agent-detail-client.tsx` | ✅ Good | Clean component, no issues |
| `dashboard/page.tsx` | ⚠️ Minor | Ownership matching is fragile (§4.3) |
| `dashboard/dashboard-client.tsx` | ⚠️ Minor | SWR interval too aggressive (§3.3) |
| `dashboard/register/register-form.tsx` | ✅ Good | Clean form with proper Zod integration |
| `browse-content.test.tsx` | ✅ Good | Comprehensive filter tests |
| `register-form.test.tsx` | ✅ Good | Tests validation, submission, errors |
| `browse.spec.ts` (Playwright) | ✅ Acceptable | Basic E2E coverage |
| UI components (`alert`, `form`, `label`, `tabs`, `textarea`) | ✅ Good | Standard Shadcn components |
| `pyproject.toml` | ✅ Good | Mypy exclude for compliance harness is correct |
| ADR updates | ✅ Good | ADR-19 is well-reasoned |

---

**Review Conclusion:** 3 Required Fixes (§2.1, §2.2, §2.3) and 1 Recommended Fix (§2.4) must be addressed before merge. The remaining items are improvements that can be tracked as follow-up tasks.
