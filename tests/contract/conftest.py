"""Contract test fixtures for cross-version compatibility testing.

This module imports and re-exports rate limiting fixtures from the transport
conftest to ensure proper test isolation without duplicating code.

Following testing-standards.mdc:
- Fixtures are loaded automatically via conftest.py
- Rate limiting patterns from tests/transport/conftest.py are reused
"""

import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from slowapi import Limiter


@pytest.fixture(autouse=True)
def disable_rate_limiting_for_contract_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> "Limiter":
    """Automatically disable rate limiting for all contract tests.

    This fixture runs automatically for every test in the contract package.
    It creates a limiter with no limits and replaces the global limiter
    in both middleware and server modules.

    This follows the pattern from tests/transport/conftest.py but applies
    automatically to all tests in this package.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        The no-limit limiter instance
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    # Create limiter with NO limits
    no_limit_limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=f"memory://contract-tests-{uuid.uuid4().hex}",
        default_limits=[],  # Empty list = no limits
    )

    # Replace globally in both modules
    import asap.transport.middleware as middleware_module
    import asap.transport.server as server_module

    monkeypatch.setattr(middleware_module, "limiter", no_limit_limiter)
    monkeypatch.setattr(server_module, "limiter", no_limit_limiter)

    return no_limit_limiter
