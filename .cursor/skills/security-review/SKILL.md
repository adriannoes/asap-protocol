---
name: Security Review
description: Conduct a thorough security audit focused on OWASP Top 10, secrets detection, and input validation.
disable-model-invocation: false
---

# Security Review

You are an expert security auditor.

## Pre-requisites

Strictly enforce:

- `.cursor/rules/security-standards.mdc` (always-on policy)
- `.cursor/README.md` (agent index and precedence)

## When to use this skill vs a local PR command

| Goal | Use |
|------|-----|
| General security audit of changes or a module | This skill |
| PR review focused on high-confidence exploitable vulns only | Optional local slash command under `.cursor/commands/` (gitignored; not committed) |

A local PR command (when present) **excludes** DoS, rate limiting, secrets-on-disk, and theoretical findings. This skill follows `security-standards.mdc` without those exclusions.

## Review checklist

### 1. Secrets and credentials

- [ ] Scan for `sk-`, `ghp_`, `eyJ` patterns.
- [ ] Check for hardcoded passwords/tokens.
- [ ] Verify environment variables are used, not raw strings.

### 2. Input validation (zero trust)

- [ ] **Frontend:** Zod schemas for forms and URL params.
- [ ] **Backend:** Pydantic v2 models for all API inputs (`extra="forbid"` where appropriate).
- [ ] **Sanitization:** No `dangerouslySetInnerHTML` without DOMPurify.

### 3. Authentication and authorization

- [ ] JWT signatures verified on every protected request.
- [ ] Least-privilege OAuth scopes for agents.
- [ ] No sensitive session data in `localStorage`.

### 4. Dependencies

- [ ] `uv.lock` / `package-lock.json` changes are intentional.
- [ ] Flag known vulnerable packages (`pip-audit`, `npm audit`).

## Output format

- **Vulnerability:** Name or CWE
- **Severity:** Critical / High / Medium / Low
- **Fix:** Secure code example
