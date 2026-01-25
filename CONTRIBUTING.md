# Contributing to ASAP Protocol

Thanks for helping out! Here's how to get started quickly.

## Quick Start

1.  **Setup**: You need `uv` installed.
    ```bash
    git clone https://github.com/adriannoes/asap-protocol.git
    cd asap-protocol
    uv sync --all-extras
    ```

2.  **Verify**:
    ```bash
    uv run pytest
    ```

## Development Workflow

-   **Linting & Formatting**: `uv run ruff check .` and `uv run ruff format .`
-   **Type Checking**: `uv run mypy src/`
-   **Testing**: `uv run pytest` (or `uv run pytest --cov=src` for coverage)

## Pull Requests

1.  **Branch**: Create a feature branch (`git checkout -b feature/my-cool-feature`).
2.  **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: add awesome feature`, `fix: resolve crash`).
3.  **Test**: Ensure `uv run pytest` passes.
4.  **Push**: Open a PR on GitHub.

## Guidelines

-   **Code Style**: Follow PEP 8 (handled by Ruff).
-   **Tests**: New features need tests. Bug fixes need regression tests.
-   **Docs**: Update docstrings and README if you change behavior.

## Reviewing Dependabot PRs

Dependabot automatically creates pull requests for dependency updates. Here's how to review and handle them:

### Types of Updates

1. **Security Updates**: Automatically created when vulnerabilities are detected
   - These are **high priority** and should be reviewed promptly
   - See [Security Update Policy](../SECURITY.md#security-update-policy) for response time SLAs

2. **Version Updates**: Created monthly for non-security dependency updates
   - These can be reviewed during regular maintenance windows
   - Focus on patch and minor updates first

### Review Workflow

1. **Check CI Status**: Ensure all CI checks pass (tests, linting, type checking)
2. **Review Changelog**: Check the dependency's changelog for breaking changes
3. **Test Locally** (if needed):
   ```bash
   git checkout <dependabot-branch>
   uv sync --all-extras
   uv run pytest
   ```
4. **Verify Compatibility**: Ensure the update doesn't break existing functionality
5. **Merge**: If everything looks good, merge the PR

### SLA Timelines

- **Critical Security**: Review within 24 hours
- **High Security**: Review within 3 days
- **Medium/Low Security**: Review within 7 days
- **Version Updates**: Review within 14 days (monthly batch)

### When to Defer

- If the update introduces breaking changes that require code modifications
- If CI tests fail and the failure is not related to the dependency update
- If the update conflicts with other ongoing work (coordinate with maintainers)

### Auto-merge

Currently, auto-merge is disabled. All Dependabot PRs require manual review to ensure compatibility and maintain code quality.

## Project Structure

-   `src/asap/models`: Core Pydantic models.
-   `src/asap/transport`: HTTP/JSON-RPC layer.
-   `src/asap/state`: State machine logic.
-   `tests/`: Where the magic is verified.

## Need Help?

Check [Discussions](https://github.com/adriannoes/asap-protocol/discussions) or open an [Issue](https://github.com/adriannoes/asap-protocol/issues).

By contributing, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and license your code under Apache 2.0.
