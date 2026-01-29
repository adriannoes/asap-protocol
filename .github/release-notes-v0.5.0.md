# v0.5.0 - Security-Hardened Release

Release date: 2026-01-28

This release focuses on security hardening while preserving full backward compatibility with v0.1.0 and v0.3.0. All new security features are **opt-in**; existing agents continue to work without code changes.

---

## Security Hardening Highlights

- **Authentication**: Bearer token authentication with configurable validators and sender verification.
- **Replay attack prevention**: Timestamp validation (5-minute window) and optional nonce validation with configurable TTL.
- **DoS protection**: Rate limiting (100 req/min per sender), request size limits (10MB), bounded thread pool, and client-side circuit breaker.
- **HTTPS enforcement**: Client can require HTTPS in production (`require_https=True`).
- **Secure logging**: Automatic sanitization of tokens, nonces, and URLs in logs (no sensitive data leakage).
- **Input validation**: Stricter validation and empty nonce rejection with clear error messages.

All features are **opt-in**; no breaking changes for existing users.

---

## New Features

| Area | Feature |
|------|---------|
| **Rate limiting** | 100 requests/minute per sender (configurable); per-sender tracking. |
| **HTTPS** | Client-side `require_https` option for production. |
| **Timestamps** | Envelope age validation with `MAX_ENVELOPE_AGE_SECONDS` (5 min). |
| **Nonce TTL** | Configurable via `NONCE_TTL_SECONDS` (2× envelope age). |
| **Retry** | Exponential backoff, jitter, `Retry-After` support, circuit breaker. |
| **Log sanitization** | `sanitize_token`, `sanitize_nonce`, `sanitize_url` in `asap.utils.sanitization`. |

---

## Upgrade Instructions

1. **From v0.1.0 or v0.3.0**  
   Upgrade as usual: `pip install --upgrade asap-protocol`  
   No code changes required; new security features are opt-in.

2. **Enable security (optional)**  
   - Set `manifest.auth` and a token validator for Bearer auth.  
   - Set `require_nonce=True` for replay protection.  
   - Set `require_https=True` on the client for HTTPS-only.

3. **Documentation**  
   See `docs/migration.md` for detailed upgrade paths and `docs/security.md` for security configuration.

---

## Breaking Changes

**None.** This release is fully backward compatible with v0.1.0 and v0.3.0.

---

## Full Changelog

See [CHANGELOG.md](../CHANGELOG.md) for the complete list of changes, fixes, and technical details.

**Issues closed**: #7, #9, #10, #11, #12, #13
