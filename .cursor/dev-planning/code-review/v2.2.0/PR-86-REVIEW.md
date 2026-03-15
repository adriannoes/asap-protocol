# Code Review: PR #86

## 1. Executive Summary
| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ⚠️ | PR introduces ECDSA instead of required Ed25519 for generated keys. Added `idb-keyval` dependency without justification. |
| **Architecture** | ⚠️ | Violates §3.1 of Tech Stack Decisions (Strict Ed25519 constraint). |
| **Security** | ⚠️ | Test/Fixture authentication backdoor relies only on `ENABLE_FIXTURE_ROUTES` without checking `NODE_ENV`, creating a risk if deployed to production. |
| **Tests** | ✅ | Excellent E2E test coverage added for auth and dashboard journeys via Playwright. |

> **General Feedback:** Solid addition of E2E coverage and functional requirements for the Marketplace agent registration journey (UX). However, the PR violates a strict architectural mandate regarding cryptography (Ed25519) and introduces a potential security backdoor if the test-login feature leaks to a production deployment. 

## 2. Required Fixes (Must Address Before Merge)

### Cryptography Standard Violation: ECDSA instead of Ed25519
*   **Location:** `apps/web/src/lib/webcrypto.ts:Line 14-17`
*   **Problem:** The `generateAndStoreAgentKeys()` function uses the `ECDSA` algorithm with the `P-256` curve.
*   **Rationale (Expert View):** Section 3.1 of `.cursor/dev-planning/architecture/tech-stack-decisions.md` explicitly mandates the use of **Ed25519** and specifically rejects **ECDSA** ("multiple curves = complexity"). Using ECDSA violates the core signing identity structure (Alignment with MCP, SSH, Signal) and breaks the core protocol compliance standards.
*   **Fix Suggestion:**
    Update the WebCrypto `generateKey` algorithm to use `Ed25519`.
    ```typescript
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: 'Ed25519',
        },
        true,
        ['sign', 'verify']
    );
    ```

### Production Security Risk: Test Provider Backdoor
*   **Location:** `apps/web/src/auth.ts:Line 35` and `apps/web/src/app/dashboard/register/actions.ts:Line 54`
*   **Problem:** The `test-login` NextAuth Credentials provider and the bypass reachability checks in the registration Server Action only check `process.env.ENABLE_FIXTURE_ROUTES === 'true'`. 
*   **Rationale (Expert View):** Environment variables can easily be misconfigured or leaked across environments. Relying solely on a feature flag for deep authentication bypass creates a severe security risk. Next.js server actions are public endpoints, and this creates a severe backdoor if left enabled in production. It must explicitly deny execution in the production environment.
*   **Fix Suggestion:**
    Include a strict environment check (`NODE_ENV !== 'production'`).
    ```typescript
    // In src/auth.ts
    ...(process.env.ENABLE_FIXTURE_ROUTES === 'true' && process.env.NODE_ENV !== 'production'
        ? [
            Credentials({ ... })
        ] : []),
    
    // In src/app/dashboard/register/actions.ts
    if (process.env.ENABLE_FIXTURE_ROUTES === 'true' && process.env.NODE_ENV !== 'production' && username === 'e2e-tester') {
        ...
    }
    ```

## 3. Tech-Specific Bug Hunt (Deep Dive)

*   [x] **Cryptography**: Using ECDSA rather than Ed25519 in `webcrypto.ts`.
*   [x] **Server Actions Security**: The server action `submitAgentRegistration` contains testing backdoors that need stricter environment constraints.

## 4. Improvements & Refactoring (Highly Recommended)

*   [ ] **Optimization**: The `idb-keyval` dependency is a new external library. While it is lightweight, you might consider dropping it if you can use native IndexedDB to strictly follow the "Avoid dependency bloat" directive, or at least document its justification in the PR description.
*   [ ] **Typing**: In `apps/web/src/auth.ts:270`, the type assertion `(user as { username?: string }).username` is a bit cumbersome. You could augment the NextAuth `User` interface in a `types/next-auth.d.ts` declaration file to include `username` as an optional string.

## 5. Verification Steps
> Run Playwright E2E tests ensuring the changes do not break the auth journey or E2E tests:
> `npm run test:e2e` in `apps/web`.
> Manual Test: Clear browser IndexedDB, visit the register page, and verify that the generated keys use Ed25519 algorithm.
