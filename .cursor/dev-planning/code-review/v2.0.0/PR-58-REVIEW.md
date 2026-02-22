# Code Review: PR #58

> **PR**: feat(v2.0): Sprint M3 — Developer experience (registry, IssueOps, verify flow)
> **Branch**: `feat/sprint-m3-developer-experience` → `main`
> **Commits**: 10
> **Files Changed**: 48 (+2,605 / −516)
> **Reviewer**: Senior Staff Engineer (Automated Deep Review)
> **Date**: 2026-02-21

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ⚠️ | `VerificationStatus` uses `str` instead of `Enum`/`datetime`; native HTML select/checkbox instead of Shadcn; `protocol.d.ts` has duplicate type aliases |
| **Architecture** | ⚠️ | CI workflow pushes directly to `main` (bypasses branch protection); no concurrency group creates race conditions; verify action missing Zod validation |
| **Security** | ⚠️ | SSRF in `process_registration.py` (no URL scheme validation); error messages leak fetched content to issue comments; weak key derivation in `auth.ts` |
| **Tests** | ⚠️ | Good coverage overall but gaps: `buildVerificationRequestIssueUrl` untested; dashboard happy path missing; script edge cases (malformed JSON, missing file) uncovered |

> **General Feedback:** The Sprint M3 deliverables are comprehensive and well-structured — the IssueOps pivot from PR-based registration is architecturally sound and the register flow (`actions.ts`) is an excellent security model. However, the `process_registration.py` script (which runs in CI with write access to `main`) has **critical SSRF and error-leakage vulnerabilities** that must be fixed before merge. The verify flow needs parity with the register flow (Zod validation, rate limiting). The `VerificationStatus` model should use proper Enum/datetime types consistent with the rest of the codebase.

---

## 2. Required Fixes (Must Address Before Merge)

### RF-1: SSRF in `fetch_manifest` — No URL Validation in CI Script

- **Location:** `scripts/process_registration.py:70-74`
- **Severity:** CRITICAL (CWE-918)
- **Problem:** The `manifest_url` comes directly from GitHub Issue body (untrusted user input). The script fetches it with `httpx.Client` without any URL scheme or hostname validation. An attacker can create an issue with `manifest_url: http://169.254.169.254/latest/meta-data/iam/security-credentials/` to hit cloud metadata endpoints on the GitHub Actions runner.
- **Rationale (Expert View):** This is the highest-risk finding. The web app has `isAllowedExternalUrl()` SSRF protection, but the CI script completely bypasses that. Combined with RF-2, fetched content can be exfiltrated via issue comments.
- **Fix Suggestion:**

```python
import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    "metadata.google.internal", "metadata.aws.internal",
    "169.254.169.254",
}

def _is_safe_url(url: str) -> bool:
    """Block private IPs, loopback, and cloud metadata endpoints."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTS:
        return False
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return False
    except ValueError:
        pass
    return True

def fetch_manifest(url: str, timeout: float = 15.0) -> Manifest:
    """Fetch and validate an agent manifest from a URL."""
    if not _is_safe_url(url):
        raise ValueError(f"Blocked URL (private/metadata): {url}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return Manifest.model_validate_json(resp.text)
```

---

### RF-2: Error Messages Leak Internal Data to Issue Comments

- **Location:** `scripts/process_registration.py:134-141`, `.github/workflows/register-agent.yml:74-75`
- **Severity:** HIGH (CWE-209)
- **Problem:** Pydantic `ValidationError` and `httpx.HTTPError` messages may include fetched content. These are written to `result.json`, then posted as public GitHub issue comments. Combined with RF-1, this enables SSRF data exfiltration.
- **Rationale (Expert View):** Even without SSRF, leaking Pydantic validation details reveals the exact schema structure to attackers — useful for crafting bypass payloads.
- **Fix Suggestion:**

```python
except httpx.HTTPError:
    errors.append(f"Manifest URL unreachable: {manifest_url}")
    Path(output_path).write_text(json.dumps({"valid": False, "errors": "; ".join(errors)}))
    return
except ValidationError as e:
    error_count = e.error_count()
    errors.append(
        f"Manifest failed schema validation ({error_count} error(s)). "
        "Ensure it follows the ASAP Manifest format."
    )
    Path(output_path).write_text(json.dumps({"valid": False, "errors": "; ".join(errors)}))
    return
```

---

### RF-3: Race Condition — No Concurrency Group in Registration Workflow

- **Location:** `.github/workflows/register-agent.yml` (top level)
- **Severity:** CRITICAL
- **Problem:** Two issues opened simultaneously both read `registry.json`, both pass uniqueness checks, and one overwrites the other on `git push`. GitHub Actions runs concurrent jobs by default.
- **Rationale (Expert View):** Data loss in the production registry. An agent registration silently disappears with no error or audit trail.
- **Fix Suggestion:**

```yaml
concurrency:
  group: registry-update
  cancel-in-progress: false
```

---

### RF-4: Verify Server Action Missing Zod Validation + Rate Limiting

- **Location:** `apps/web/src/app/dashboard/verify/actions.ts:6-24`
- **Severity:** CRITICAL (CWE-20)
- **Problem:** Unlike `submitAgentRegistration` (which uses `ManifestSchema.safeParse` + `checkRateLimit`), the verify action accepts `VerificationFormValues` TypeScript type — erased at runtime. Any payload passes. No rate limiting either.
- **Rationale (Expert View):** Server Actions are public HTTP endpoints. TypeScript types provide zero runtime protection. This is inconsistent with the excellent security pattern in the register flow.
- **Fix Suggestion:**

```typescript
// lib/verification-schema.ts (shared)
import { z } from 'zod';
export const VerificationSchema = z.object({
    agent_id: z.string().min(1).max(200),
    why_verified: z.string().min(1).max(2000),
    running_since: z.string().min(1).max(100),
    evidence: z.string().max(2000).optional(),
    contact: z.string().max(200).optional(),
});
export type VerificationFormValues = z.infer<typeof VerificationSchema>;

// verify/actions.ts
export async function submitVerificationRequest(
    values: unknown
): Promise<{ success: boolean; issueUrl?: string; error?: string }> {
    const session = await auth();
    if (!session?.user) return { success: false, error: 'Unauthorized' };

    const userId = (session.user as { id?: string }).id ?? 'anonymous';
    if (!checkRateLimit(userId, 5, 60_000)) {
        return { success: false, error: 'Too many requests. Try again in a minute.' };
    }

    const parsed = VerificationSchema.safeParse(values);
    if (!parsed.success) return { success: false, error: 'Invalid form data.' };
    const data = parsed.data;
    // ... build URL with data ...
}
```

---

### RF-5: `sys.exit(0)` on Unexpected Exception Masks CI Failures

- **Location:** `scripts/process_registration.py:219-223`
- **Severity:** CRITICAL
- **Problem:** The broad `except Exception` handler exits with code 0 (success) and has no logging. If the script crashes (e.g., `PermissionError`, `MemoryError`), CI reports success. If `result.json` also fails to write, the exception is silently swallowed.
- **Rationale (Expert View):** Silent CI failures are the worst kind — they build false confidence that the registration system is working when it may be broken.
- **Fix Suggestion:**

```python
import logging

logger = logging.getLogger(__name__)

# In main():
except Exception:
    logger.exception("Unexpected error processing registration")
    try:
        Path(args.output).write_text(
            json.dumps({"valid": False, "errors": "Internal processing error"})
        )
    except OSError:
        logger.exception("Failed to write error output")
    sys.exit(1)  # Exit with error code
```

---

### RF-6: Weak Cryptographic Key Derivation

- **Location:** `apps/web/src/auth.ts:13`
- **Severity:** HIGH (CWE-326)
- **Problem:** `authSecret.padEnd(32, '0').slice(0, 32)` — if `AUTH_SECRET` is 8 chars, 24 bytes are predictable `'0'`. This drastically reduces entropy of the AES key used to encrypt OAuth access tokens in sessions.
- **Rationale (Expert View):** The encrypted access token grants read access to users' GitHub issues. A weak encryption key makes the token recoverable.
- **Fix Suggestion:**

```typescript
import { createHash } from 'crypto';

if (!authSecret || authSecret.length < 32) {
    throw new Error(
        'AUTH_SECRET must be at least 32 characters. Generate one with: npx auth secret'
    );
}
const secretKey = createHash('sha256').update(authSecret).digest();
```

---

### RF-7: Direct Push to `main` Bypasses Branch Protection

- **Location:** `.github/workflows/register-agent.yml:52-59`
- **Severity:** HIGH
- **Problem:** The workflow pushes directly to `main` with `contents: write`. If `process_registration.py` has a bug (or a supply-chain compromise in a dependency), arbitrary changes could be committed. This also fails silently if branch protection requires PRs.
- **Rationale (Expert View):** The IssueOps pattern should create a PR (auto-merged after CI passes) rather than pushing directly. This preserves auditability and allows rollback.
- **Fix Suggestion:**

```yaml
- name: Create PR for registry update
  if: steps.result.outputs.valid == 'true'
  run: |
    BRANCH="registry/issue-${{ github.event.issue.number }}"
    git checkout -b "$BRANCH"
    git add registry.json
    git commit -m "feat(registry): register agent from issue #${{ github.event.issue.number }}"
    git push origin "$BRANCH"
    gh pr create --title "feat(registry): register agent #${{ github.event.issue.number }}" \
      --body "Auto-generated from issue #${{ github.event.issue.number }}" \
      --base main --head "$BRANCH"
    gh pr merge "$BRANCH" --auto --squash
```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### Next.js 15 / React 19

- [x] **Server Action without Zod (RF-4):** `verify/actions.ts` accepts typed input without runtime validation — **CRITICAL** (see Required Fix RF-4)
- [ ] **Client Component Abuse:** `dashboard-client.tsx` and `verify-form.tsx` correctly use `"use client"` since they manage state/forms — **PASS**
- [ ] **Unnecessary `useEffect`:** `AgentStatusBadge` fetches health status client-side for every agent in the dashboard. Consider proxying via API route to avoid exposing user IPs to arbitrary agent endpoints — **MAJOR** (see Section 4, IMP-6)
- [x] **HTML Native instead of Shadcn:** `register-form.tsx:212-221` uses native `<select>` and `<input type="checkbox">` instead of Shadcn `<Select>` and `<Checkbox>` — **MAJOR**
- [x] **Tailwind Typo:** `agent-detail-client.tsx:150` has `test-sm` instead of `text-sm` — **MAJOR** (visual bug)
- [ ] **Missing `next-auth.d.ts`:** Multiple files use `session.user.username` and `session.encryptedAccessToken` via unsafe type assertions (`as { id?: string }`) — **MAJOR** (type safety)

### FastAPI / Pydantic v2

- [x] **`VerificationStatus.status` is plain `str`:** Project convention uses `Enum` for state fields (`TaskStatus`, `MessageRole`). Should be `VerificationState(str, Enum)` — **MAJOR**
- [x] **`VerificationStatus.verified_at` is `str`:** Should be `datetime` with ISO 8601 validation, consistent with `LiteRegistry.updated_at` — **MAJOR**
- [x] **`verified_at` required when status is "pending":** Should be `datetime | None = None` — **MINOR**

### Asyncio / Scripts

- [x] **Non-atomic file write:** `save_registry()` uses `Path.write_text()` — interrupted write corrupts `registry.json` — **MAJOR** (see Section 4, IMP-1)
- [x] **Zero logging:** 228-line CI script with no `logging` calls — **MAJOR**
- [x] **Dead code:** `issue_number` parameter passed to `run()` but never used — **MAJOR**
- [x] **4 public functions without docstrings:** `fetch_manifest`, `save_registry`, `run`, `main` — **MAJOR** (PEP 257 violation)

### Schema / Types

- [x] **`manifest.schema.json`:** `VerificationStatus.status` has no enum constraint; `verified_at` has no `format: "date-time"` — **MAJOR**
- [x] **`protocol.d.ts` duplicate types:** Auto-generated file has massive type alias duplications (e.g., `TaskId` declared 14+ times) — **MAJOR** (generator bug)

---

## 4. Improvements & Refactoring (Highly Recommended)

### IMP-1: Atomic Write for `registry.json`

- **Location:** `scripts/process_registration.py:90-91`
- **Suggestion:** Use `tempfile.mkstemp` + atomic rename to prevent corruption on interrupted writes:

```python
import tempfile, os

def save_registry(path: str, agents: list[dict[str, Any]]) -> None:
    """Write agents list to registry JSON file atomically."""
    target = Path(path)
    content = json.dumps(agents, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

---

### IMP-2: DRY — Extract Error Writer Helper

- **Location:** `scripts/process_registration.py` (6 repeated instances of error-writing pattern)
- **Suggestion:**

```python
def _write_validation_result(
    output_path: str, *, valid: bool = False, errors: str = ""
) -> None:
    """Write validation result JSON to output path."""
    Path(output_path).write_text(json.dumps({"valid": valid, "errors": errors}))
```

---

### IMP-3: Unsafe `e as Error` Cast

- **Location:** `apps/web/src/app/dashboard/register/actions.ts:64-66`
- **Suggestion:**

```typescript
} catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return { success: false, error: `Could not reach Manifest URL: ${message}` };
}
```

---

### IMP-4: Registry Fetch Without Runtime Validation

- **Location:** `apps/web/src/lib/registry.ts:29-31`
- **Suggestion:** The `as RegistryAgent[]` type assertion bypasses runtime validation. Create a Zod schema for `RegistryAgent` and validate the external JSON response.

---

### IMP-5: `NEXT_PUBLIC_REGISTRY_URL` Exposed Unnecessarily

- **Location:** `apps/web/src/lib/registry.ts:12-14`
- **Suggestion:** `fetchRegistry()` runs server-side only. Rename to `REGISTRY_URL` (remove `NEXT_PUBLIC_` prefix) to avoid leaking in client bundle.

---

### IMP-6: Client-side Health Fetch Exposes User IPs

- **Location:** `apps/web/src/app/dashboard/dashboard-client.tsx:33-60`
- **Suggestion:** The browser fetches arbitrary agent endpoints for health checks. A malicious agent could register a tracking endpoint. Proxy health checks through a server-side API route.

---

### IMP-7: XSS via `javascript:` URI in OAuth2 URL

- **Location:** `apps/web/src/app/agents/[id]/agent-detail-client.tsx:195`
- **Suggestion:** Validate URL protocol before rendering as `href`:

```typescript
const safeUrl = (() => {
    if (typeof agent.auth.oauth2.authorization_url !== 'string') return '#';
    try {
        const u = new URL(agent.auth.oauth2.authorization_url);
        return ['https:', 'http:'].includes(u.protocol) ? u.href : '#';
    } catch { return '#'; }
})();
```

---

### IMP-8: Test Fixture Uses Private `_registry_cache`

- **Location:** `tests/discovery/test_registry.py:45-48`
- **Suggestion:** Use `reset_registry_cache()` instead of `_registry_cache.clear()` — the public API also clears `_registry_locks`, preventing leak between tests.

---

### IMP-9: Missing Test Coverage

| Missing Test | File | Priority |
| :--- | :--- | :--- |
| `buildVerificationRequestIssueUrl` | `github-issues.test.ts` | High |
| Dashboard happy path (Octokit mock with issues) | `dashboard-actions.test.ts` | High |
| WebSocket URL SSRF validation branch | `register-actions.test.ts` | Medium |
| `load_registry` with malformed JSON | `test_process_registration.py` | Medium |
| `load_registry` with LiteRegistry wrapper format | `test_process_registration.py` | Medium |
| `save_registry` dedicated test | `test_process_registration.py` | Low |
| `main()` unexpected exception handler | `test_process_registration.py` | Low |

---

### IMP-10: `handleRefresh` Without `useCallback`

- **Location:** `apps/web/src/app/dashboard/dashboard-client.tsx:102-107`
- **Suggestion:** Wrap in `useCallback` for referential stability since it's used as an `onClick` handler.

---

### IMP-11: Workflow `fetch-depth: 0` Unnecessary

- **Location:** `.github/workflows/register-agent.yml:23-24`
- **Suggestion:** Use `fetch-depth: 1` (shallow clone) for faster checkout. Full history is not needed.

---

### IMP-12: CI Path Filter Missing `scripts/**`

- **Location:** `.github/workflows/ci.yml:8-16`
- **Suggestion:** Changes to `scripts/process_registration.py` don't trigger CI. Add `'scripts/**'` to the paths filter.

---

## 5. Verification Steps

After applying fixes, verify with:

```bash
# Python quality
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
PYTHONPATH=src uv run pytest tests/ --cov=src --cov-report=term-missing -v

# Script-specific tests
PYTHONPATH=src uv run pytest tests/scripts/test_process_registration.py -v

# Web quality
cd apps/web
npm run lint
npx tsc --noEmit
npx vitest run

# Specific test files for verify flow
npx vitest run src/app/dashboard/verify/__tests__/
npx vitest run src/lib/github-issues.test.ts

# Security
uv run pip-audit
cd apps/web && npm audit
```

---

## 6. Positive Highlights

| Area | Detail |
| :--- | :--- |
| **Register Action** | `register/actions.ts` is an excellent security template: auth check → rate limit → Zod parse → SSRF check → reachability → GitHub Issue URL |
| **Shared Schema** | `register-schema.ts` shared between client and server is the correct DRY pattern |
| **ISR Strategy** | `registry.ts` with `revalidate: 60` is the right approach for semi-static registry data |
| **Token Encryption** | JWE A256GCM in `auth.ts` protects access tokens in session — above-average security |
| **Page as RSC** | `register/page.tsx` and `verify/page.tsx` are properly Server Components with auth guards |
| **SSRF Protection (Web)** | `url-validator.ts` with IP blocklist is thorough |
| **Test Structure** | Good separation of unit tests, clear naming, appropriate mocking patterns |

---

## 7. Issue Tracker

| # | Type | Severity | Title | Effort |
| :--- | :--- | :--- | :--- | :--- |
| RF-1 | Security | **CRITICAL** | SSRF in `fetch_manifest` | 30 min |
| RF-2 | Security | **HIGH** | Error message data leakage | 15 min |
| RF-3 | Reliability | **CRITICAL** | Race condition — no concurrency group | 5 min |
| RF-4 | Security | **CRITICAL** | Verify action missing Zod + rate limit | 30 min |
| RF-5 | Reliability | **CRITICAL** | `sys.exit(0)` masks failures | 15 min |
| RF-6 | Security | **HIGH** | Weak key derivation (`padEnd`) | 10 min |
| RF-7 | Architecture | **HIGH** | Direct push to `main` | 30 min |
| IMP-1 | Reliability | MAJOR | Atomic write for registry | 15 min |
| IMP-2 | Code Quality | MINOR | DRY error writer | 10 min |
| IMP-3 | Type Safety | MINOR | Unsafe `e as Error` | 5 min |
| IMP-4 | Validation | MAJOR | Registry fetch without Zod | 30 min |
| IMP-5 | Security | MINOR | `NEXT_PUBLIC_` exposure | 5 min |
| IMP-6 | Privacy | MAJOR | Client-side health fetch leaks IPs | 45 min |
| IMP-7 | Security | MAJOR | XSS via `javascript:` URI | 10 min |
| IMP-8 | Testing | MINOR | Private `_registry_cache` in fixture | 5 min |
| IMP-9 | Testing | MAJOR | Missing test coverage (7 gaps) | 2 hrs |
| IMP-10 | Performance | MINOR | `handleRefresh` without `useCallback` | 5 min |
| IMP-11 | CI | MINOR | Unnecessary `fetch-depth: 0` | 2 min |
| IMP-12 | CI | MINOR | Missing `scripts/**` in CI paths | 5 min |

**Total estimated effort for Required Fixes:** ~2.5 hours
**Total estimated effort for Improvements:** ~3.5 hours

---

## 8. Post-Fix Verification (2026-02-21)

All Required Fixes (RF-1 through RF-7) and key Improvements have been verified as addressed.

### Required Fixes — Verification Matrix

| # | Fix | Status | Evidence |
| :--- | :--- | :--- | :--- |
| RF-1 | SSRF in `fetch_manifest` | **RESOLVED** | `_is_safe_url()` added with `_BLOCKED_HOSTS` frozenset, private IP check, scheme validation. Tests: `TestFetchManifestSSRF` (3 cases) + `test_blocks_ssrf_manifest_url` in integration |
| RF-2 | Error message data leakage | **RESOLVED** | `ValidationError` messages sanitized to generic `"Manifest failed schema validation (N error(s))"`. `httpx.HTTPError` messages show only URL, not response body |
| RF-3 | Race condition (concurrency) | **RESOLVED** | `concurrency: { group: registry-update, cancel-in-progress: false }` added to workflow |
| RF-4 | Verify action Zod + rate limit | **RESOLVED** | `VerificationSchema.safeParse(values)` + `checkRateLimit(userId, 5, 60_000)` in `verify/actions.ts`. Schema shared from `@/lib/github-issues` with `.max()` constraints |
| RF-5 | `sys.exit(0)` masks failures | **RESOLVED** | Changed to `sys.exit(1)` + `logger.exception()` with fallback `OSError` handling |
| RF-6 | Weak key derivation | **RESOLVED** | `createHash('sha256').update(authSecret).digest()` with min-length guard (`authSecret.length < 32` throws) |
| RF-7 | Direct push to `main` | **RESOLVED** | Workflow now creates branch `registry/issue-N`, opens PR via `gh pr create`, uses `gh pr merge --auto --squash` |

### Improvements — Verification Matrix

| # | Fix | Status | Evidence |
| :--- | :--- | :--- | :--- |
| IMP-1 | Atomic write for registry | **RESOLVED** | `tempfile.mkstemp` + `Path.replace` pattern in `save_registry()` |
| IMP-2 | DRY error writer | **RESOLVED** | `_write_validation_result()` helper extracted |
| IMP-3 | Unsafe `e as Error` cast | **RESOLVED** | Uses `e instanceof Error ? e.message : String(e)` |
| IMP-4 | Registry fetch without Zod | **RESOLVED** | `RegistryResponseSchema` + `RegistryAgentSchema` created in `registry-schema.ts`, validated in `fetchRegistry()` |
| IMP-5 | `NEXT_PUBLIC_` exposure | **RESOLVED** | Renamed to `REGISTRY_URL` (no `NEXT_PUBLIC_` prefix) |
| IMP-6 | Client-side health fetch | **RESOLVED** | Proxied via `/api/health-check?url=` server-side route |
| IMP-7 | XSS via `javascript:` URI | **RESOLVED** | URL protocol validated against `['https:', 'http:']` before rendering as `href` |
| IMP-8 | Private `_registry_cache` | **RESOLVED** | Uses `reset_registry_cache()` public API |
| IMP-9 | Missing test coverage | **RESOLVED** | `buildVerificationRequestIssueUrl` tested; `TestLoadRegistry` (4 cases); `TestSaveRegistry` (1 case); SSRF integration test added |
| IMP-10 | `handleRefresh` without `useCallback` | **RESOLVED** | Wrapped with `useCallback([mutate, router])` |
| IMP-11 | `fetch-depth: 0` | **RESOLVED** | Changed to `fetch-depth: 1` |
| Model: `VerificationStatus` | **RESOLVED** | `status` uses `VerificationState` enum; `verified_at` is `datetime \| None` |
| Shadcn components | **RESOLVED** | Native `<select>` replaced with Shadcn `<Select>`; native checkbox replaced with Shadcn `<Checkbox>` |
| Tailwind typo `test-sm` | **RESOLVED** | Fixed to `text-sm` |
| Docstrings | **RESOLVED** | `fetch_manifest`, `save_registry`, `load_registry` have Google-style docstrings |
| `VerificationSchema` shared | **RESOLVED** | Defined in `@/lib/github-issues.ts`, imported by both `verify-form.tsx` and `verify/actions.ts` |

### CI Verification Results

| Check | Result |
| :--- | :--- |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **289 files already formatted** |
| `uv run mypy src/` | **Success: no issues found in 106 source files** |
| `npx tsc --noEmit` | **No errors** |
| `uv run pytest tests/` | **2365 passed, 5 skipped** (113s) |
| `npx vitest run` | **61 passed** (9 test files, 2.6s) |

### Verdict

**APPROVED for merge.** All Required Fixes resolved. All key Improvements addressed. Full CI suite green.
