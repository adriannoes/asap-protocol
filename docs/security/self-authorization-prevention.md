# Self-authorization prevention

This document describes the threat of **self-authorization** in ASAP approval flows (PRD §4.5), mitigations shipped in the reference implementation, and how operators should configure them.

## Threat

An **agent that controls the browser** (or an automation layer around it) can drive the user through Device Authorization on the **same** machine: open `verification_uri`, paste or infer `user_code`, and complete consent without a human making a deliberate, separate-device decision. That effectively lets the agent approve its own registration or escalation.

Related risks:

- Long-lived or reused Host JWTs can be replayed to start approval while the human is not present.
- High-risk capabilities approved without **proof-of-presence** can be abused if only a password or passive session is available.

## Mitigations (protocol and product)

| Mitigation | Requirement ID | Implementation notes |
|------------|----------------|------------------------|
| **Fresh authentication on approval paths** | SELF-001 | Host JWT `iat` must fall within `FreshSessionConfig.window_seconds` when `identity_fresh_session_config` is set on the app. Applies to registration that requires approval and to `GET /asap/agent/status` polling while approval is **pending**. |
| **WebAuthn / hardware-backed proof** | SELF-002 | `FreshSessionConfig.require_webauthn_for` lists capability names that require a `webauthn` object in the register JSON body. Verifier is pluggable (`identity_webauthn_verifier`); default wiring uses `PlaceholderWebAuthnVerifier` (always succeeds) until a real WebAuthn stack is integrated. Production SHOULD use `userVerification: "required"` where appropriate. |
| **CIBA preference when the agent controls the browser** | SELF-003 | Clients MAY send `"agent_controls_browser": true` on register. When the host is linked (`user_id`) and CIBA is supported, the server selects **CIBA** so approval can be completed on another channel/device, even if the client hinted `device_authorization`. |
| **Configuration surface** | SELF-005 | `FreshSessionConfig.window_seconds` defaults to **300** seconds (`freshSessionWindow`). |

## Configuration guidance

1. **Enable fresh sessions in production** for any deployment that exposes approval:

   ```python
   from asap.auth.self_auth import FreshSessionConfig
   from asap.transport.server import create_app

   app = create_app(
       manifest,
       identity_fresh_session_config=FreshSessionConfig(window_seconds=300),
   )
   ```

2. **Tighten the window** for high-assurance environments (e.g. 120 seconds) so stale Host JWTs cannot open new approval sessions.

3. **List sensitive capabilities** under `require_webauthn_for` and supply a real `WebAuthnVerifier` implementation. Treat the placeholder verifier as **test-only**.

4. **Prefer CIBA** for browser-embedded agents: set host `user_id`, ensure `identity_host_supports_ciba=True`, and have clients set `agent_controls_browser: true` when accurate.

5. **Operational**: combine with human review, audit of approvals, and least-privilege default capabilities (see capability defaults on `HostIdentity`).

## References

- PRD: `prd-v2.2-protocol-hardening.md` §4.5 (Self-Authorization Prevention)
- Code: `src/asap/auth/self_auth.py`, approval-aware routes in `src/asap/transport/agent_routes.py`
