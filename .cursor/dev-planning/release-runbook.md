# Release Runbook (v1.2.0+)

## One-command release

```bash
git tag v1.2.0 && git push origin v1.2.0
```

Triggers `.github/workflows/release.yml` which:
- Validates CHANGELOG has the version section
- Builds and publishes **asap-protocol** and **asap-compliance** to PyPI
- Builds and pushes Docker image to ghcr.io
- Creates GitHub Release with artifacts

## PyPI Trusted Publishing (one-time setup) ✅

Both packages use Trusted Publishing (OIDC). Configure **each** project on PyPI:

1. **asap-protocol**: PyPI → Project → Publishing → Add trusted publisher ✅
   - Owner: `adriannoes` (or your org)
   - Repository: `asap-protocol`
   - Workflow: `release.yml`
   - Environment: (leave empty)

2. **asap-compliance**: Same steps for the `asap-compliance` project ✅
   - Must be configured separately; same repo and workflow

If asap-compliance publish fails with "project not found", create the project on PyPI first (pypi.org → Add project → `asap-compliance`), then add Trusted Publishing.
