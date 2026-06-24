# v2.5.0 — Branching strategy

## Integration branch

All v2.5.0 work merges into:

```text
release/2.5.0
```

**Do not** land sprint PRs directly on `main` until the full v2.5.0 release is ready.

## Per-sprint workflow

1. Branch from `release/2.5.0`: `feat/v2.5.0-s0-design-lock`, `feat/v2.5.0-s1-middleware`, etc.
2. Open PR **into `release/2.5.0`** (not `main`).
3. After S5 release checklist passes on `release/2.5.0`, open **one** PR: `release/2.5.0` → `main` (tag `v2.5.0`).

## Merge order

```
S0 → S1 → S2 → S3 → S4 → S5 → main
```

Each sprint PR should rebase on latest `release/2.5.0` before merge.
