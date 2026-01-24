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

## Project Structure

-   `src/asap/models`: Core Pydantic models.
-   `src/asap/transport`: HTTP/JSON-RPC layer.
-   `src/asap/state`: State machine logic.
-   `tests/`: Where the magic is verified.

## Need Help?

Check [Discussions](https://github.com/adriannoes/asap-protocol/discussions) or open an [Issue](https://github.com/adriannoes/asap-protocol/issues).

By contributing, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and license your code under Apache 2.0.
