# Contributing to ASAP Protocol

Thank you for your interest in contributing to ASAP! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Development Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/adriannoes/asap-protocol.git
   cd asap-protocol
   ```

3. **Install dependencies**:
   ```bash
   uv sync --all-extras
   ```

4. **Verify installation**:
   ```bash
   uv run pytest
   uv run ruff check .
   uv run mypy src/
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/models/test_entities.py

# Run in watch mode (requires pytest-watch)
uv run ptw
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy src/

# Run all checks
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

## How to Contribute

### Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)

### Suggesting Features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml) and include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation (if applicable)

### Pull Requests

1. **Fork and create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the code style (enforced by ruff)
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit your changes** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat: add new feature"
   git commit -m "fix: resolve bug in state machine"
   git commit -m "docs: update API documentation"
   ```

   **Commit types**:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `test`: Adding or updating tests
   - `refactor`: Code refactoring
   - `perf`: Performance improvements
   - `chore`: Maintenance tasks

4. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a pull request on GitHub.

### PR Guidelines

- Fill out the PR template completely
- Ensure all CI checks pass
- Keep PRs focused on a single concern
- Add tests for new functionality
- Update documentation if needed
- Respond to review feedback promptly

## Development Guidelines

### Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all functions
- Write docstrings for public APIs (Google style)
- Keep functions small and focused
- Use meaningful variable names

### Testing

- Write tests before fixing bugs (TDD)
- Aim for >80% code coverage
- Test edge cases and error conditions
- Use descriptive test names
- Keep tests independent

### Documentation

- Update docstrings when changing APIs
- Add examples for complex features
- Keep README.md up to date
- Document breaking changes in CHANGELOG.md

## Project Structure

```
asap-protocol/
├── src/              # Source code
│   ├── models/       # Pydantic models
│   ├── state/        # State management
│   └── transport/    # HTTP transport
├── tests/            # Test files
├── schemas/          # JSON Schemas
├── src/asap/examples/ # Usage examples
└── docs/             # Documentation
```

## Release Process

Releases are automated via GitHub Actions:

1. Update version in `src/__init__.py`
2. Update `CHANGELOG.md`
3. Create and push a tag:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```
4. GitHub Actions will build and publish to PyPI

## Getting Help

- 💬 [GitHub Discussions](https://github.com/adriannoes/asap-protocol/discussions)
- 🐛 [Issue Tracker](https://github.com/adriannoes/asap-protocol/issues)
- 📖 [Documentation](https://adriannoes.github.io/asap-protocol)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
