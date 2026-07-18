# v2.5.4 — Branching strategy

## Integration branch

**All** v2.5.4 feature/sprint branches merge into:

```text
release/2.5.4
```

| Rule | Detail |
|------|--------|
| Base for new work | Branch **from** `release/2.5.4` |
| PR target | Open PRs **into** `release/2.5.4` — never into `main` mid-train |
| Only path to `main` | **One** PR at S5: `release/2.5.4` → `main` (then tag `v2.5.4`) |
| Rebase policy | Rebase each sprint branch on latest `release/2.5.4` before merge |

**Status (2026-07-18):** `release/2.5.4` exists on origin (created at kickoff). Do **not** recreate it.

**Do not** land sprint PRs directly on `main` until the full v2.5.4 release is ready.

## Per-sprint workflow

1. ~~Create `release/2.5.4` from `main`~~ — **done** (on origin).
2. Branch from `release/2.5.4`: `feat/v2.5.4-s0-scope-lock`, `feat/v2.5.4-s1-starter-pack`, `feat/v2.5.4-s2-build-for-agents`, `feat/v2.5.4-s3-homepage-routing`, `feat/v2.5.4-s4-telemetry`, etc.
3. Open PR **into `release/2.5.4`** (not `main`).
4. After S5 checklist passes on `release/2.5.4`, open **one** PR: `release/2.5.4` → `main` (tag `v2.5.4`).

Combined branches are allowed when efficient (for example S0+S1), but each PR still targets `release/2.5.4`. Prefer one functional change theme per PR when possible.

## Merge order

```
S0 → S1 → S2 → S3 → S5 → main
      └── S4 (parallel after S0; SHOULD; must not block S5 if deferred)
```

Every arrow above (except the final `→ main`) is a merge **into `release/2.5.4`**.

S4 may merge any time after S0. Incomplete S4 requires an explicit deferral note on the roadmap before S5 marks DIST-004 N/A/deferred.

## Naming

```text
feat/v2.5.4-s{N}-{slug}   →  PR base: release/2.5.4
release/2.5.4             →  PR base: main   (S5 only)
```
