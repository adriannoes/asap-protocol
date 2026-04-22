# CI: Compliance Harness gate

This page shows how to run `asap compliance-check` in continuous integration so that a **failing Compliance Harness v2** can block a job (for example before deployment or on every PR).

Prerequisites:

- A reachable ASAP agent **base URL** (staging, preview, or a service started in the same workflow).
- The `asap-protocol` package installed in the job (`pip` or `uv`).

## Exit codes

- Use **`--exit-on-fail`**: the CLI exits **1** if the harness score is below `1.0`, which fails the step unless you allow failure explicitly.
- Connection/timeouts exit **2** — treat as infrastructure errors (retry or alert).

See [CLI reference: `compliance-check`](cli.md#asap-compliance-check) for all flags.

## GitHub Actions example

The following workflow installs the CLI and runs the harness against an agent URL from a **repository secret** (recommended). Replace secret names and triggers to match your repo.

```yaml
# .github/workflows/compliance.yml
name: Compliance Harness

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install asap-protocol CLI
        run: |
          python -m pip install --upgrade pip
          pip install "asap-protocol"

      - name: Run Compliance Harness v2 (gate on failure)
        env:
          AGENT_BASE_URL: ${{ secrets.ASAP_COMPLIANCE_AGENT_URL }}
        run: |
          asap compliance-check \
            --url "$AGENT_BASE_URL" \
            --output json \
            --exit-on-fail \
            --timeout 120
```

Configure `ASAP_COMPLIANCE_AGENT_URL` in the repository **Settings → Secrets and variables → Actions** to your agent’s HTTPS base URL (no path suffix; the harness calls the agent’s HTTP API). **Do not** commit real URLs or tokens in the workflow file.

### Optional: JSON report as an artifact

```yaml
      - name: Write report to file
        env:
          AGENT_BASE_URL: ${{ secrets.ASAP_COMPLIANCE_AGENT_URL }}
        run: |
          asap compliance-check \
            --url "$AGENT_BASE_URL" \
            --output json \
            --exit-on-fail \
            > compliance-report.json

      - name: Upload compliance report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: compliance-report.json
```

### Authenticated agents

If your agent requires auth, prefer **network-level** protection in CI (private network, OIDC to a test tenant) or inject headers via your **deployment** tooling rather than pasting secrets into logs. The harness runs over HTTP(S); ensure TLS and least-privilege credentials for the compliance environment.

## Related

- [CLI: `compliance-check`](cli.md#asap-compliance-check)
- [Compliance testing guide](guides/compliance-testing.md)
