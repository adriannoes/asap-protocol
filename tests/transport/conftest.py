"""Transport layer test fixtures for ASAP protocol.

This module provides reusable pytest fixtures for transport layer tests, including:
- Isolated rate limiter creation (isolated_limiter_factory)
- Aggressive monkeypatch fixtures (replace_global_limiter)
- App creation helpers (create_isolated_app)
- Base test classes (NoRateLimitTestBase)

See docs/testing.md for detailed usage guide and testing strategies.
"""

import collections.abc
import uuid
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.observability import get_logger
from asap.transport.server import create_app

# Get logger for test fixtures
logger = get_logger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from slowapi import Limiter

# Test configuration constants
TEST_RATE_LIMIT_DEFAULT = "100000/minute"  # Very high default for testing


def create_test_limiter(limits: collections.abc.Sequence[str] | None = None) -> "Limiter":
    """Helper function to create a new isolated limiter instance for testing.

    Args:
        limits: Optional list of rate limit strings. Defaults to very high limits.

    Returns:
        New Limiter instance with isolated storage
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    if limits is None:
        limits = [TEST_RATE_LIMIT_DEFAULT]

    # Use unique storage URI to ensure complete isolation
    unique_storage_id = str(uuid.uuid4())
    return Limiter(
        key_func=get_remote_address,
        default_limits=list(limits),
        storage_uri=f"memory://{unique_storage_id}",
    )


@pytest.fixture
def isolated_limiter_factory() -> Callable[[Sequence[str] | None], "Limiter"]:
    """Factory fixture that creates isolated rate limiters.

    Returns a function that creates new Limiter instances with unique storage.
    Each limiter gets its own UUID-based storage to ensure complete test isolation.

    Args:
        limits: Optional rate limit strings (e.g., ["10/minute"]). Defaults to very high limit.

    Returns:
        New Limiter instance with isolated memory storage
    """

    def _create(limits: collections.abc.Sequence[str] | None = None) -> "Limiter":
        """Create a new isolated limiter."""
        # Log fixture execution for debugging
        logger.debug(
            "test.fixture.isolated_limiter_factory",
            limits=limits,
            action="creating_limiter",
        )
        return create_test_limiter(limits)

    return _create


@pytest.fixture
def replace_global_limiter(
    monkeypatch: pytest.MonkeyPatch,
    isolated_limiter_factory: Callable[[Sequence[str] | None], "Limiter"],
) -> "Limiter":
    """Replace global limiter with isolated instance using aggressive monkeypatch.

    This fixture performs "aggressive monkeypatch" by replacing the module-level
    limiter in BOTH asap.transport.middleware and asap.transport.server.

    Why "aggressive"? The slowapi.Limiter maintains global state that persists
    across tests. Simply replacing app.state.limiter is not sufficient because
    code may reference the module-level limiter directly.

    Returns:
        The new isolated limiter instance
    """
    # Log fixture execution
    logger.debug(
        "test.fixture.replace_global_limiter",
        action="creating_isolated_limiter",
    )

    # Create completely isolated limiter
    new_limiter = isolated_limiter_factory(None)

    # Replace in both modules
    import asap.transport.middleware as middleware_module
    import asap.transport.server as server_module

    logger.debug(
        "test.fixture.replace_global_limiter",
        action="monkeypatching_modules",
        limiter_id=id(new_limiter),
    )

    monkeypatch.setattr(middleware_module, "limiter", new_limiter)
    monkeypatch.setattr(server_module, "limiter", new_limiter)

    logger.debug(
        "test.fixture.replace_global_limiter",
        action="complete",
        limiter_id=id(new_limiter),
    )

    return new_limiter


@pytest.fixture
def no_auth_manifest() -> Manifest:
    """Create a manifest without authentication for simple tests.

    Returns:
        A Manifest instance with no auth configuration
    """
    return Manifest(
        id="urn:asap:agent:test-transport",
        name="Test Transport Agent",
        version="1.0.0",
        description="Test agent for transport layer tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="echo",
                    description="Echo input as output",
                )
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def create_isolated_app(
    monkeypatch: pytest.MonkeyPatch,
    isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], Limiter]",
) -> "collections.abc.Callable[[Manifest, str | None, int | None, int | None, bool], FastAPI]":
    """Factory fixture for creating isolated FastAPI apps.

    NOTE: This is a utility/building-block fixture. For most tests, prefer creating
    specialized class-level fixtures instead (see test_rate_limiting.py for examples
    like isolated_app_5_per_minute). This pattern provides better readability and
    co-locates fixture configuration with the tests that use them.

    The returned function creates apps with isolated rate limiters to prevent
    interference between tests. Supports both direct limiter assignment and
    aggressive monkeypatch strategies.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        isolated_limiter_factory: Factory function to create isolated limiters

    Returns:
        Function that creates FastAPI apps with isolated limiters

    Example:
        >>> def test_something(create_isolated_app, no_auth_manifest):
        ...     app = create_isolated_app(
        ...         manifest=no_auth_manifest,
        ...         rate_limit="100/minute",
        ...         max_request_size=1024 * 1024,
        ...         max_threads=4,
        ...         use_monkeypatch=True
        ...     )
    """

    def _create_app(
        manifest: Manifest,
        rate_limit: str | None = None,
        max_request_size: int | None = None,
        max_threads: int | None = None,
        use_monkeypatch: bool = False,
    ) -> "FastAPI":
        """Create a FastAPI app with isolated rate limiter.

        Args:
            manifest: Agent manifest
            rate_limit: Optional rate limit string (e.g., "100/minute")
            max_request_size: Optional maximum request size in bytes
            max_threads: Optional maximum number of threads
            use_monkeypatch: If True, replace global limiter in modules (aggressive isolation)

        Returns:
            FastAPI app with isolated limiter configured
        """
        # Create isolated limiter
        limits = [rate_limit] if rate_limit else None
        isolated_limiter = isolated_limiter_factory(limits)

        # If use_monkeypatch, replace global limiters in modules
        if use_monkeypatch:
            import asap.transport.middleware as middleware_module
            import asap.transport.server as server_module

            monkeypatch.setattr(middleware_module, "limiter", isolated_limiter)
            monkeypatch.setattr(server_module, "limiter", isolated_limiter)

        # Create app
        app = create_app(
            manifest=manifest,
            registry=None,
            token_validator=None,
            rate_limit=rate_limit or "100000/minute",
            max_request_size=max_request_size,
            max_threads=max_threads,
        )

        # Always replace app.state.limiter with isolated instance
        app.state.limiter = isolated_limiter

        return app  # type: ignore[no-any-return]

    return _create_app


class NoRateLimitTestBase:
    """Base class for tests that should not use rate limiting.

    Tests inheriting from this class will have rate limiting completely
    disabled to avoid interference from rate limiting tests.

    The fixture automatically replaces the global limiter in both middleware
    and server modules with a limiter that has no limits (empty limits list).

    Example:
        class TestMyFeature(NoRateLimitTestBase):
            \"\"\"Tests for my feature without rate limiting interference.\"\"\"

            def test_something(self):
                # This test runs with rate limiting disabled
                app = create_app(manifest)
                # Rate limiting is automatically disabled
    """

    @pytest.fixture(autouse=True)
    def disable_rate_limiting(self, monkeypatch: pytest.MonkeyPatch) -> "Limiter":
        """Automatically disable rate limiting for all tests in this class.

        This fixture runs automatically for every test method in classes
        that inherit from NoRateLimitTestBase. It creates a limiter with
        no limits and replaces the global limiter in both middleware and
        server modules.

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
            storage_uri=f"memory://no-limits-{uuid.uuid4().hex}",
            default_limits=[],  # Empty list = no limits
        )

        # Replace globally in both modules
        import asap.transport.middleware as middleware_module
        import asap.transport.server as server_module

        monkeypatch.setattr(middleware_module, "limiter", no_limit_limiter)
        monkeypatch.setattr(server_module, "limiter", no_limit_limiter)

        return no_limit_limiter
