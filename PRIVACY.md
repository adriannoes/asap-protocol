# Privacy — ASAP Protocol (website and adoption telemetry)

This document describes **aggregate adoption and infrastructure metrics** for the ASAP Protocol project, the public website, and **maintainer-only** dashboards. It is **not** legal advice.

## What we collect (high level)

### Public-source aggregates

We derive **non-identifying** statistics from public data sources where possible, for example:

- **npm** — public download count APIs for `@asap-protocol/*` packages.
- **PyPI** — public download statistics for the `asap-protocol` project.
- **GitHub** — public repository metadata (for example stars and forks) and repository traffic endpoints available to maintainers with appropriate access.
- **Lite registry** — counts of entries in the public `registry.json` mirror.

These aggregates **do not** include agent IDs, end-user identity, or message payloads from the protocol.

### Website (Vercel)

The public site uses **Vercel Web Analytics** and related Vercel product defaults as configured in the deployment. Analytics is intended to measure **aggregate** traffic and feature usage (for example which documentation links are used), **not** to build per-person behavioral profiles.

- **No PII in weekly maintainer dashboards** — published snapshots are counts and ratios only.
- **Client-side signals** follow Vercel’s product privacy posture for Web Analytics (cookie-light / privacy-oriented design — see [Vercel’s documentation](https://vercel.com/docs/analytics) for current detail).

### Optional operator-supplied site metrics

Maintainership tooling may merge **manually exported** or **backend-relayed** CTR summaries into weekly snapshots (see `docs/maintainers/telemetry.md`). Those values are **aggregates** and must not include personal data.

## What we do not do (telemetry scope)

We **do not** use:

- Protocol **agent IDs** or tenant identifiers in public telemetry files.
- SDK “phone home” telemetry from embedded agents (out of scope for this repository’s weekly dashboard).

## Do Not Track and preferences

Where technically practical, we honor **Do Not Track** (`DNT`) and similar browser privacy signals for site delivery paths that support them. For product-specific handling, refer to the hosting provider’s current documentation (for example Vercel).

Visitors who prefer not to be included in aggregate analytics should use standard browser controls and provider opt-out paths described in Vercel’s **Web Analytics** documentation.

## Lawful basis (GDPR Art. 6 — summary)

For visitors to the website in jurisdictions where the GDPR applies, maintainer dashboards rely on **legitimate interests (Art. 6(1)(f))**, specifically:

- **Understanding aggregate product adoption** (documentation usage, package installs in aggregate) to prioritize engineering work and documentation.
- **Securing and operating the site** (abuse detection at the infrastructure layer — via the hosting provider’s tooling where applicable).

We apply **data minimization**: we work with **counts and trends**, not with identifiable visitor profiles, in the committed and artifact outputs from this repository’s telemetry scripts.

## Retention

Raw provider-side analytics data is governed by the hosting provider’s retention settings. Weekly snapshots in CI artifacts are intended for **short-to-medium-term planning**; rotate or delete artifacts per your org policy.

## Contact

General inquiries: [info@asap-protocol.com](mailto:info@asap-protocol.com).  
Security issues: see [SECURITY.md](SECURITY.md).
