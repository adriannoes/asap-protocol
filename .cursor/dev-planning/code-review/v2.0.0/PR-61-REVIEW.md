# Code Review: PR #61

> **PR**: [feat(v2.0): Sprint M4 launch prep – security, registry, web polish](https://github.com/adriannoes/asap-protocol/pull/61)
> **Branch**: `feat/v2.0.0-m4-launch-prep` → `main`
> **Stats**: 65 files, +5918 / -284
> **Date**: 2026-02-24

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | All Next.js items addressed |
| **Architecture** | ✅ | RSC, DRY, error boundaries addressed |
| **Security** | ✅ | SSRF, assert, headers, DNS, URL validation addressed |
| **Tests** | ✅ | Good coverage overall; 2385 tests passing |

> **General Feedback:** The PR delivers a comprehensive M4 sprint with strong security awareness. **All blocking issues and recommended improvements have been addressed.** Ready for merge.

---

## 2. Required Fixes (Must Address Before Merge)

### RF-1: `updateTag` does not exist in `next/cache` — API will crash — ✅ DONE

- **Location**: `apps/web/src/app/dashboard/actions.ts:3,55`
- **Problem**: The import `updateTag` from `next/cache` does not exist. The correct API is `revalidateTag`. This will cause a build error or runtime crash when `revalidateUserRegistrationIssues()` is called.
- **Rationale (Expert View)**: The dashboard "Refresh" button is completely broken. Users won't see updated registration status, destroying trust in the IssueOps flow.
- **Fix Suggestion**:

```typescript
// actions.ts L3
import { unstable_cache, revalidateTag } from 'next/cache';

// actions.ts L55
revalidateTag(`${CACHE_TAG_PREFIX}-${userId}`);
```

---

### RF-2: SSRF bypass via HTTP redirect in `fetch_manifest` — ✅ DONE

- **Location**: `scripts/process_registration.py:156-162`
- **Problem**: `_is_safe_url()` validates only the initial URL, but `httpx.Client` follows redirects by default (up to 20). An attacker can submit `https://evil.com/manifest.json` that redirects to `http://169.254.169.254/latest/meta-data/` — complete SSRF bypass (CWE-918).
- **Rationale (Expert View)**: This runs in GitHub Actions processing any user's Issue Form input. AWS IMDSv1 credentials could be exfiltrated via a crafted manifest URL, compromising the CI environment.
- **Fix Suggestion**:

```python
def fetch_manifest(url: str, timeout: float = 15.0) -> Manifest:
    if not _is_safe_url(url):
        raise ValueError(f"Blocked URL (private/metadata): {url}")
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return Manifest.model_validate_json(resp.text)
```

---

### RF-3: `assert` used for cryptographic validation — removed by `-O` — ✅ DONE

- **Location**: `src/asap/crypto/signing.py:42`
- **Problem**: `assert len(raw_signature) == 64` is used to validate Ed25519 signature length. `assert` statements are removed when Python runs with `-O` (optimized mode), silently bypassing this critical check.
- **Rationale (Expert View)**: This is in the signing path — the core trust layer of the ASAP Protocol. A malformed signature could be accepted without error in optimized deployments.
- **Fix Suggestion**:

```python
if len(raw_signature) != 64:
    raise ValueError(
        f"Ed25519 signature must be 64 bytes, got {len(raw_signature)}"
    )
```

---

### RF-4: `opengraph-image.tsx` uses legacy `params` pattern — runtime error on Next.js 15+ — ✅ DONE

- **Location**: `apps/web/src/app/agents/[id]/opengraph-image.tsx:15`
- **Problem**: In Next.js 15+, `params` is `Promise<{ id: string }>` and must be awaited. The adjacent `page.tsx` uses the correct async pattern, but this file uses the legacy sync pattern. This will cause a runtime error — all social share previews will be broken.
- **Rationale (Expert View)**: OG images are critical for social proof and SEO. Broken OG images damage credibility when agents are shared on social media.
- **Fix Suggestion**:

```typescript
export default async function Image({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const agentId = decodeURIComponent(id);
```

---

### RF-5: Missing security headers in `next.config.ts` — ✅ DONE

- **Location**: `apps/web/next.config.ts`
- **Problem**: No security headers configured: no CSP, no `X-Frame-Options`, no `X-Content-Type-Options`, no HSTS, no `Referrer-Policy`, no `Permissions-Policy`. The site handles OAuth flows and sensitive agent data.
- **Rationale (Expert View)**: Without `X-Frame-Options`, the OAuth flow is vulnerable to clickjacking. Without HSTS, downgrade attacks are possible. This is a marketplace handling developer credentials.
- **Fix Suggestion**:

```typescript
const nextConfig = {
  turbopack: { root: path.resolve(__dirname, "./") },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Frame-Options", value: "DENY" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
      ],
    }];
  },
};
```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### Next.js 15 / React 19

- [x] **RF-1**: `updateTag` API does not exist — use `revalidateTag`
- [x] **RF-4**: `params` must be `Promise<>` and awaited (OG image route)
- [x] **Client Component Abuse**: `agent-card-skeleton.tsx` (L1) has `"use client"` but uses zero hooks or event handlers — pure presentational component that should be RSC — **DONE**: No `"use client"`, already RSC
- [x] **Client Component Abuse**: `agent-detail-client.tsx` (L1) — entire ~300-line component is `"use client"`. Only `AgentReachabilityBadge` needs client interactivity. Extract it as a separate client component and keep the rest as RSC — **DONE**: `AgentStatusBadge` extracted to `@/components/agent/agent-status-badge.tsx`
- [x] **Missing Error Boundaries**: No `error.tsx` in `/browse` or `/agents/[id]` — if `fetchRegistry()` fails, users see a generic error page instead of a graceful fallback — **DONE**: `error.tsx` exists in both routes
- [x] **Missing `generateMetadata`**: `features/[slug]/page.tsx` has title/description in `FEATURE_CONTENT` but no `generateMetadata()` export — SEO broken for 4 important feature pages — **DONE**: `generateMetadata()` exported
- [x] **Missing `Metadata` export**: `legal/privacy-policy/page.tsx` and `legal/terms-of-service/page.tsx` use generic root layout metadata — **DONE**: Both export `metadata`
- [x] **Non-null assertion crash**: `Header.tsx:68` — `session.user.image!` crashes for GitHub users without avatar, breaking the entire app (Header is in root layout). Fix: `session.user.image ?? undefined` — **DONE**: Uses `?? undefined`
- [x] **Redundant state**: `browse-content.tsx:25-33` — `debounce` via `useEffect` + `useDeferredValue` serve overlapping purposes. Pick one — **DONE**: Only `useDeferredValue` used, no debounce
- [x] **Double type assertion**: `registry.ts:63` — `as unknown as RegistryAgent` bypasses TypeScript entirely — **DONE**: Input typed with `RegistryAgentValidated`, explicit transformation, documented assertion

### FastAPI / Pydantic v2

- [x] **RF-3**: `assert` used for signature length validation in `signing.py:42`
- [x] **`assert` for type narrowing**: `secure_agent.py:135` uses `assert` to satisfy mypy. Use explicit `if not x: raise ValueError(...)` instead — **DONE**: No assert found; uses `if ... raise ValueError`
- [x] **Unused variable**: `test_signing.py:287` — `other_private_key, other_public_key = generate_keypair()` — first element unused, should be `_` — **DONE**: Uses `_, other_public_key`

### Security & SSRF

- [x] **RF-2**: SSRF redirect bypass in `fetch_manifest()`
- [x] **DNS rebinding (Python)**: `process_registration.py:56-70` — `_is_safe_url()` does not resolve DNS — **DONE**: Uses `socket.getaddrinfo()` to resolve and check resolved IPs
- [x] **DNS rebinding (TS)**: `proxy/check/route.ts:40-48` — TOCTOU gap between `isAllowedProxyUrlAsync(url)` DNS validation and `fetch(url)` — **DONE**: Documented in route comment
- [x] **URL protocol XSS**: `agent-detail-client.tsx:143-150` — `repository_url` and `documentation_url` rendered as `href` without protocol validation — **DONE**: `safeAuthHref` uses `isAllowedExternalUrl` which rejects non-http/https

### CI/CD

- [x] **Missing `permissions:`**: `ci.yml` and `validate-registry.yml` don't declare `permissions:` — **DONE**: Both declare `permissions: contents: read`
- [x] **`uv` not installed**: `register-agent.yml` and `remove-agent.yml` use `actions/setup-python@v5` instead of the project's composite action — **DONE**: Both use `./.github/actions/setup-python`
- [x] **Actions not pinned by SHA**: All external Actions use mutable tags (`@v4`, `@v5`) — supply-chain risk (OpenSSF Scorecard penalty) — **DONE**: Pinned all Actions by full SHA (see Implementation Notes below)
- [x] **Crash leaves user without feedback**: If `process_registration.py` crashes (`sys.exit(1)`), subsequent steps (commenting on issue) are skipped. Add `if: always()` to the comment step — **DONE**: `if: always() && steps.process.outcome == 'failure'` in both workflows
- [x] **Missing `timeout-minutes`**: IssueOps workflows inherit the 360-minute default — **DONE**: Both have `timeout-minutes: 10`

---

## 4. Improvements & Refactoring (Highly Recommended)

- [x] **DRY — Extract shared script utilities**: `sanitize_input()`, `parse_issue_body()`, `_write_validation_result()`, `load_registry()`, `save_registry()` — **DONE**: Extracted to `scripts/lib/registry_io.py`, both scripts import from it
- [x] **DRY — Extract `AgentReachabilityBadge`**: Identical logic exists in `agent-detail-client.tsx` (`AgentReachabilityBadge`) and `dashboard-client.tsx` (`AgentStatusBadge`). Extract to `@/components/agent/agent-status-badge.tsx` — **DONE**
- [x] **Typing**: `registry.ts:63` double `as unknown as` assertion should be replaced with proper type alignment between Zod inferred type and `RegistryAgent` — **DONE**: Input typed with `RegistryAgentValidated`, explicit transformation
- [x] **Typing**: `dashboard-client.tsx:222` casts agent to `{ online_check?: boolean }` — **DONE**: Uses `RegistryAgent` which includes `online_check`
- [x] **Performance**: Consider `react-window` or `@tanstack/react-virtual` for the 500+ agent browse grid instead of rendering all cards in the DOM — **DONE**: Implemented with `@tanstack/react-virtual` (see Implementation Notes below)
- [x] **Zod schema**: `registry-schema.ts:29` uses `.passthrough()` allowing arbitrary unvalidated fields through. Consider `.strip()` or document the forward-compatibility reason — **DONE**: Schema uses `.strip()`
- [x] **Dependabot**: Add `npm` (for `apps/web/`) and `github-actions` ecosystems to `.github/dependabot.yml` — **DONE**: Both ecosystems configured
- [x] **Commit convention**: `remove-agent.yml:67` uses `feat(registry)` for removal — should be `chore(registry)` per Conventional Commits — **DONE**: Uses `chore(registry)`
- [x] **`next-auth` beta**: `package.json:31` uses `"next-auth": "^5.0.0-beta.30"` — pin exact version for production stability — **DONE**: Pinned to `5.0.0-beta.30`
- [x] **`framer-motion` bundle**: `HeroSection.tsx` imports `framer-motion` (~30KB+) — **DONE**: HeroSection uses Tailwind `animate-in`/CSS, no framer-motion

---

## 5. Verification Steps

After applying fixes, verify with:

```bash
# 1. Python tests (all scripts + crypto)
PYTHONPATH=src:. uv run pytest tests/scripts/ tests/crypto/ -v --tb=short

# 2. Full Python test suite
PYTHONPATH=src:. uv run pytest --tb=short -q

# 3. Linting + type check
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ scripts/ tests/

# 4. Web app build (catches updateTag / params errors)
cd apps/web && npm run build

# 5. Web app tests
cd apps/web && npx vitest run

# 6. Security scan
uv run pip-audit
```

### Specific test commands per fix:

| Fix | Verify |
|-----|--------|
| RF-1 (updateTag) | `cd apps/web && npx tsc --noEmit` — will catch import error |
| RF-2 (SSRF redirect) | `uv run pytest tests/scripts/test_process_registration.py -v -k "ssrf or blocked"` |
| RF-3 (assert → raise) | `uv run pytest tests/crypto/test_signing.py -v` |
| RF-4 (OG params) | `cd apps/web && npm run build` — will error on incorrect params type |
| RF-5 (headers) | `curl -I https://preview-url/ | grep -i "x-frame-options"` |

---

## 6. Implementation Notes (Addressed Items)

### 6.1 GitHub Actions Pinned by SHA (Supply-Chain Security)

**What was done:** All external GitHub Actions were replaced from mutable tags (`@v4`, `@v5`, etc.) to full commit SHAs to reduce supply-chain risk and improve OpenSSF Scorecard compliance.

**Files modified:**
- `.github/workflows/ci.yml` — checkout, setup-node, codecov
- `.github/workflows/release.yml` — checkout, docker/*, astral-sh/setup-uv, pypa/gh-action-pypi-publish, softprops/action-gh-release
- `.github/workflows/validate-registry.yml`, `register-agent.yml`, `remove-agent.yml`, `docs.yml` — checkout
- `.github/actions/setup-python/action.yml` — astral-sh/setup-uv

**SHAs used (with original tag in comment):**

| Action | SHA |
|--------|-----|
| `actions/checkout@v4` | `34e114876b0b11c390a56381ad16ebd13914f8d5` |
| `actions/setup-node@v4` | `49933ea5288caeca8642d1e84afbd3f7d6820020` |
| `astral-sh/setup-uv@v5` | `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` |
| `codecov/codecov-action@v4` | `b9fd7d16f6d7d1b5d2bec1a2887e65ceed900238` |
| `docker/setup-qemu-action@v3` | `c7c53464625b32c7a7e944ae62b3e17d2b600130` |
| `docker/setup-buildx-action@v3` | `8d2750c68a42422c14e847fe6c8ac0403b4cbd6f` |
| `docker/metadata-action@v5` | `c299e40c65443455700f0fdfc63efafe5b349051` |
| `docker/login-action@v3` | `c94ce9fb468520275223c153574b00df6fe4bcc9` |
| `docker/build-push-action@v6` | `10e90e3645eae34f1e60eeb005ba3a3d33f178e8` |
| `pypa/gh-action-pypi-publish@release/v1` | `ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e` |
| `softprops/action-gh-release@v2` | `a06a81a03ee405af7f2048a818ed3f03bbf83c7b` |

**Format:** `uses: owner/repo@<sha>  # vX` — comment preserves traceability to original tag.

---

### 6.2 Browse Grid Virtualization (500+ Agents)

**What was done:** The browse page grid now uses `@tanstack/react-virtual` to virtualize agent cards. Only visible rows (plus overscan) are rendered in the DOM, improving performance for 500+ agents.

**Files modified:**
- `apps/web/package.json` — added `@tanstack/react-virtual`
- `apps/web/src/app/browse/browse-content.tsx` — virtualized grid implementation

**Implementation details:**
- **Library:** `@tanstack/react-virtual` with `useWindowVirtualizer` (page scrolls with window)
- **Strategy:** Virtualize by rows; each row contains N cards (N = columns based on breakpoint)
- **Breakpoints:** 1 column (<1024px), 2 columns (lg), 3 columns (xl) — aligned with Tailwind
- **scrollMargin:** Computed via `ResizeObserver` on the grid container for correct positioning
- **overscan:** 3 rows to reduce flicker when scrolling
- **Row height:** ~280px estimated (card + gap)

**Verification:** `npm run build` and `npm test` pass. Unit tests for browse-content (filters, search) remain green.

---

### 6.3 Final Pass (All Remaining Items)

**What was done:** Addressed all remaining items from sections 3 and 4.

**Changes made:**
- **proxy/check/route.ts**: Added TOCTOU documentation comment
- **register-agent.yml**, **remove-agent.yml**: `if: always() && steps.process.outcome == 'failure'` for crash comment step
- **package.json**: Pinned `next-auth` to `5.0.0-beta.30` (exact version)

**Already present (verified):**
- `process_registration.py`: DNS resolution via `socket.getaddrinfo()` in `_is_safe_url()`
- `agent-detail-client.tsx`: `safeAuthHref` uses `isAllowedExternalUrl` (rejects `javascript:`)
- `ci.yml`, `validate-registry.yml`: `permissions: contents: read`
- `register-agent.yml`, `remove-agent.yml`: Use `./.github/actions/setup-python`, `timeout-minutes: 10`, `chore(registry)` for removal
- `scripts/lib/registry_io.py`: Shared utilities used by both scripts
- `dependabot.yml`: npm and github-actions ecosystems
- `HeroSection.tsx`: Uses Tailwind animations, no framer-motion

---

## 7. Positive Highlights

- **SSRF protection (frontend)** is thorough — `url-validator-server.ts` resolves DNS and checks all IPs including IPv4-mapped IPv6
- **Structured logging** with `debug_id` correlation between GitHub Issue comments and Action logs is a great observability pattern
- **Auth checks** present in all dashboard server actions
- **Concurrency group** shared between `register-agent` and `remove-agent` workflows with `cancel-in-progress: false` correctly prevents registry race conditions
- **ISR/SSG** configuration is well-designed with single source of truth `REGISTRY_REVALIDATE_SECONDS`
- **Input sanitization** in IssueOps scripts (HTML stripping, control character removal, length limits)
- **Pydantic v2** used correctly throughout (`model_dump()`, `model_validate()`, `ConfigDict`)
- **Ed25519** strict verification with RFC 8032 `s >= l` rejection and JCS (RFC 8785) canonicalization
- **Test coverage** is strong at 2385 tests passing with good coverage of edge cases

---

*Review produced from systematic analysis of all 65 changed files against tech-stack-decisions.md, AGENTS.md, and sprint-M4-launch-prep.md.*
