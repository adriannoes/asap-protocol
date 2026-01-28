# GitHub Configuration

This directory contains GitHub-specific configuration files for the ASAP Protocol repository.

## Structure

```
.github/
├── README.md                    # This file - overview of GitHub configuration
├── dependabot.yml              # Dependency update automation
├── PULL_REQUEST_TEMPLATE.md    # PR template (used automatically by GitHub)
├── ISSUE_TEMPLATE/             # Issue templates
│   ├── bug_report.yml          # Bug report template
│   └── feature_request.yml     # Feature request template
└── workflows/                  # GitHub Actions workflows
    ├── ci.yml                  # Continuous Integration (tests, lint, type check)
    ├── docs.yml                # Documentation deployment (MkDocs)
    └── release.yml             # PyPI release automation (triggered by tags)
```

## Files Overview

### Dependabot Configuration

**File**: `dependabot.yml`

- **Purpose**: Automates dependency updates for security and version management
- **Schedule**: Monthly checks for version updates
- **Security**: Automatic updates for security vulnerabilities (independent of schedule)
- **Documentation**: See [SECURITY.md](../SECURITY.md) and [CONTRIBUTING.md](../CONTRIBUTING.md#reviewing-dependabot-prs)

### Issue Templates

**Location**: `ISSUE_TEMPLATE/`

- **bug_report.yml**: Template for bug reports
  - Collects version, Python version, OS, reproduction steps, logs
- **feature_request.yml**: Template for feature requests
  - Collects problem description, proposed solution, alternatives

These templates are automatically used when creating new issues on GitHub.

### Pull Request Template

**File**: `PULL_REQUEST_TEMPLATE.md`

- **Purpose**: Standardizes PR descriptions
- **Usage**: Automatically included in PR description when creating a new PR
- **Sections**: Description, type of change, testing, checklist

### GitHub Actions Workflows

**Location**: `workflows/`

#### CI Workflow (`ci.yml`)

- **Triggers**: Push to `main`, pull requests
- **Jobs**:
  - Linting (Ruff)
  - Formatting (Ruff format)
  - Type checking (mypy)
  - Testing (pytest with coverage)
  - Security audit (pip-audit)
- **Status**: Required for merging PRs

#### Docs Workflow (`docs.yml`)

- **Triggers**: Push to `main`
- **Job**: Deploys MkDocs documentation to GitHub Pages
- **Output**: https://adriannoes.github.io/asap-protocol

#### Release Workflow (`release.yml`)

- **Triggers**: Push of tags matching `v*` pattern
- **Jobs**:
  1. Builds Python package (wheel and source distribution)
  2. Publishes to PyPI using Trusted Publishing
  3. Creates GitHub Release with notes extracted from CHANGELOG.md
  4. Attaches distribution files to release
- **Usage**: Create and push a tag (e.g., `git tag v0.4.0 && git push origin v0.4.0`)

## References

- **Dependabot**: [SECURITY.md](../SECURITY.md#security-update-policy)
- **PR Review**: [CONTRIBUTING.md](../CONTRIBUTING.md#reviewing-dependabot-prs)
- **Workflows**: See individual workflow files for detailed configuration

## Maintenance

These files are actively maintained and should be updated when:
- Adding new workflows or modifying existing ones
- Updating issue/PR templates to match project needs
- Adjusting Dependabot configuration (schedule, limits, labels)

For questions or suggestions about GitHub configuration, please open an issue or discussion.
