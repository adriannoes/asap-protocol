# Security Policy

## Supported Versions

The following versions of the ASAP Protocol specification and reference implementation are currently supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| >= 2.0.0| :white_check_mark: |
| 1.x.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

## Scope of Coverage

This security policy applies to the **ASAP Protocol** ecosystem. Vulnerabilities in the following components are considered **in-scope**:

- **ASAP Protocol Reference Implementations** (`src/asap/` Python package)
- **Marketplace & Registry API** (`apps/web/` Next.js frontend and IssueOps workflow)
- **Cryptographic implementations** (Ed25519 signatures, RFC 8032/8785 handling)
- **Agent Server/Client Tooling** (FastAPI routers, WebSocket handlers)

**Out of Scope**:
- Vulnerabilities within external agents listed in the `registry.json`. Each agent is maintained by its respective owner and must be reported directly to them.
- Third-party dependencies (unless the vulnerability requires a change in how ASAP interacts with the dependency).

## Reporting a Vulnerability

We take the security of ASAP Protocol seriously. If you have found a security vulnerability, please do NOT report it publicly.

### How to Report

We use GitHub's **Private Vulnerability Reporting**. If you have found a security vulnerability, please report it privately using the "Report a vulnerability" button in the **Security** tab of this repository.

Direct link: [Report a vulnerability](https://github.com/adriannoes/asap-protocol/security/advisories/new)

If for some reason you cannot use the GitHub reporting tool, please open an issue asking for a private communication channel without disclosing the vulnerability details.

### Information to Include

Please include as much information as possible to help us reproduce and validate the issue:

-   **Description**: A clear description of the vulnerability.
-   **Reproduction Steps**: Detailed steps to reproduce the vulnerability (a Proof of Concept script is highly appreciated).
-   **Environment**:
    -   Library version (e.g., 0.1.0)
    -   Python version (e.g., 3.13)
    -   Operating system
-   **Impact**: How this vulnerability could be exploited and what the potential impact is.
-   **Logs/Output**: Any relevant error messages or logs.

### What Happens Next

1.  **Acknowledgement**: We will acknowledge your report within 48 hours via the GitHub advisory discussion.
2.  **Investigation**: We will investigate the issue and collaborate with you in the private advisory to confirm the vulnerability.
3.  **Resolution**: We will work on a fix. GitHub allows us to create a private fork to develop the fix and collaborate securely.
4.  **Release**: Once the fix is ready and verified, we will merge it, release a new version of the package, and publish a Security Advisory (CVE) crediting you for the discovery (unless you prefer to remain anonymous).

Thank you for helping keep the ASAP Protocol secure!

## Security Update Policy

We use [Dependabot](https://docs.github.com/en/code-security/dependabot) to automatically monitor dependencies for security vulnerabilities and create pull requests with fixes.

### Automatic Security Updates

Dependabot automatically creates pull requests for security updates when vulnerabilities are detected in our dependencies. These updates are independent of our monthly version update schedule and are created immediately upon detection.

### Response Times by Severity

We aim to review and merge security updates according to the following target times. These are goals, not strict commitments, as we are a solo-maintained project:

| Severity | Target Review Time | Action |
|----------|-------------------|--------|
| **Critical** | 3-5 business days | Priority review and merge if CI passes |
| **High** | 1-2 weeks | Priority review, merge after validation |
| **Medium** | 2-3 weeks | Review during next maintenance window |
| **Low** | 1 month | Review with regular version updates |

### Security Advisories

- **GitHub Security Advisories**: [View all advisories](https://github.com/adriannoes/asap-protocol/security/advisories)
- **Dependabot Alerts**: [View dependency alerts](https://github.com/adriannoes/asap-protocol/security/dependabot)
- **Dependency Graph**: [View dependency insights](https://github.com/adriannoes/asap-protocol/network/dependencies)

### Monitoring

We continuously monitor dependencies using:
- **Dependabot**: Automated security updates and alerts
- **pip-audit**: Integrated into CI pipeline for vulnerability scanning
- **GitHub Security Advisories**: Public database of known vulnerabilities

CI runs `pip-audit` after a sync that **excludes** the optional extras `crewai` and `llamaindex`, because those graphs currently pull transitive packages (`diskcache`, `nltk`) that OSV still lists with no fixed release on PyPI. To match the security job locally:

`uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex` then `uv run pip-audit --ignore-vuln CVE-2026-4539` (matches CI).

**CVE-2026-4539 (Pygments)**: OSV lists this advisory while the latest release on PyPI remains `2.19.2`. CI uses `--ignore-vuln CVE-2026-4539` until a patched `pygments` release is published; remove the flag when upgrading resolves the advisory.

If you install `[crewai]` or `[llamaindex]`, run `pip-audit` separately on that environment and expect possible advisories until upstream publishes patched releases. Integration tests for those extras still run in CI with the full dependency tree.

### Version Update Schedule

- **Security Updates**: Automatic and immediate (no schedule)
- **Version Updates**: Monthly checks for non-security updates. This project relies on [Dependabot](.github/dependabot.yml) to monitor and bump dependency versions.

For more information on reviewing Dependabot PRs, see [CONTRIBUTING.md](../CONTRIBUTING.md#reviewing-dependabot-prs).
