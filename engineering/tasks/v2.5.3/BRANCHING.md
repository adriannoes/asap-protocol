# v2.5.3 — Branching strategy

## Integration branch

All v2.5.3 work merges into:

```text
release/2.5.3
```

**Do not** land sprint PRs directly on `main` until the full v2.5.3 release is ready.

## Per-sprint workflow

1. Create `release/2.5.3` from `main` at S0 kickoff.
2. Branch from `release/2.5.3`: `feat/v2.5.3-s0-candidate-lock`, `feat/v2.5.3-s1-workflow`, `feat/v2.5.3-s3-docs-review`, etc.
3. Open PR **into `release/2.5.3`** (not `main`).
4. After S4 checklist passes on `release/2.5.3`, open **one** PR: `release/2.5.3` → `main` (tag `v2.5.3`).

## Merge order

```
S0 → S1 → (S1b optional) → (S1c optional, default go) → S2 → S3 → S4 → main
```

S1b / S1c may merge in parallel with S2 after S0; they must not block S4 if incomplete (document as research-only or defer).

Each sprint PR should rebase on latest `release/2.5.3` before merge.
