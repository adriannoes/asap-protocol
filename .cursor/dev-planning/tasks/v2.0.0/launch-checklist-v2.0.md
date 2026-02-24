# v2.0.0 Launch Checklist (Task 4.5.2)

Use this checklist before promoting to production (Task 4.5.3) and tagging v2.0.0.

---

## 1. Domain DNS propagated?

- [ ] Production domain (e.g. `marketplace.asap-protocol.org` or Vercel default) resolves correctly.
- [ ] `nslookup` / `dig` or browser confirms the domain points to the expected host (e.g. Vercel).
- [ ] HTTPS works; no certificate warnings.

**How to verify:** Open the production URL in a browser; optionally run `dig <your-domain>` or use [DNS checker](https://dnschecker.org).

---

## 2. GitHub OAuth Production App configured?

- [ ] GitHub OAuth App is in **Production** mode (not Development).
- [ ] **Authorization callback URL** matches production (e.g. `https://<your-domain>/api/auth/callback/github`).
- [ ] **Homepage URL** points to production.
- [ ] Client ID and Client Secret are set in Vercel (or host) env vars: `AUTH_GITHUB_ID`, `AUTH_SECRET`, and optionally `AUTH_GITHUB_SECRET` if used by the stack.

**How to verify:** Log out, then sign in again on the production site and confirm GitHub OAuth redirect and session work.

---

## 3. Vercel Analytics tracking active?

- [ ] **Speed Insights** and **Web Analytics** are enabled in the Vercel project (Dashboard → Project → Speed Insights / Analytics).
- [ ] At least one deploy has been done after enabling; events appear in the Vercel Dashboard (e.g. Analytics tab, Speed Insights tab).

**How to verify:** Visit the production site, navigate a few pages; check Vercel Dashboard for new events (may take a few minutes).

---

## Sign-off

- [ ] All items above verified.
- **Date:** _______________
- **Verified by:** _______________

When all boxes are checked, proceed to **Task 4.5.3** (Deploy to production) and **4.5.4** (Tag v2.0.0).
