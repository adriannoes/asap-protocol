# Transport module evolution (D4 baseline)

Product constraint **D4** requires every **new transport route or callable surface** to live in a **dedicated module**, not by extending `src/asap/transport/server.py` or `src/asap/transport/client.py` indefinitely.

CI enforces a frozen baseline of **public function and method names** on those two files.

## Enforcement

- **Script**: [`scripts/lint_no_transport_growth.py`](../../scripts/lint_no_transport_growth.py) — parses AST only (no imports from ASAP).
- **Baseline snapshot**: [`scripts/_transport_baseline_v2.3.0.json`](../../scripts/_transport_baseline_v2.3.0.json) — frozen at **v2.3.0**.
- **Workflow**: GitHub Actions job **`lint transport growth (D4)`** in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

Adding any **new public symbol** (names not starting with `_`; excludes nested defs inside functions) to either monolith file **breaks CI**. Removing symbols is allowed.

Repo admins must add this job to **branch protection required checks** next to the other CI gates.

## Escape hatch (rare)

Updating the baseline is intentional governance overhead — only after architectural agreement.

1. **Architectural review** — justify why new surface cannot ship from a new submodule under `src/asap/transport/` (or another boundary consistent with ADRs).
2. **Maintainer sign-off** — explicit approval on the PR (link reviewer handles).
3. **Same PR** — regenerate or edit **`scripts/_transport_baseline_v2.3.0.json`** together with the code change:

   ```bash
   uv run python scripts/lint_no_transport_growth.py --emit-baseline > scripts/_transport_baseline_v2.3.0.json
   ```

   Inspect the diff; commit only intentional additions.

Do **not** widen the baseline to silence unrelated churn — refactor helpers into dedicated modules instead.
