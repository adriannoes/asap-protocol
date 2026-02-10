"""Transport layer test fixtures for ASAP protocol.

This module provides reusable pytest fixtures for transport layer tests, including:
- Isolated rate limiter creation (isolated_limiter_factory)
- Aggressive monkeypatch fixtures (replace_global_limiter)
- App creation helpers (create_isolated_app)
- Base test classes (NoRateLimitTestBase)

See docs/testing.md for detailed usage guide and testing strategies.
"""

import collections.abc
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.observability import get_logger
from asap.transport.rate_limit import (
    ASAPRateLimiter,
    create_test_limiter,
    get_remote_address,
)
from asap.transport.server import create_app

# Get logger for test fixtures
logger = get_logger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI

# Test configuration constants
TEST_RATE_LIMIT_DEFAULT = "100000/minute"  # Very high default for testing


@pytest.fixture
def isolated_limiter_factory() -> Callable[[Sequence[str] | None], ASAPRateLimiter]:
    """Factory fixture that creates isolated rate limiters.

    Returns a function that creates new ASAPRateLimiter instances with unique storage.
    Each limiter gets its own UUID-based storage to ensure complete test isolation.

    Args:
        limits: Optional rate limit strings (e.g., ["10/minute"]). Defaults to very high limit.

    Returns:
        New ASAPRateLimiter instance with isolated memory storage.
    """

    def _create(limits: collections.abc.Sequence[str] | None = None) -> ASAPRateLimiter:
        """Create a new isolated limiter."""
        logger.debug(
            "test.fixture.isolated_limiter_factory",
            limits=limits,
            action="creating_limiter",
        )
        return create_test_limiter(limits, key_func=get_remote_address)

    return _create


@pytest.fixture
def replace_global_limiter(
    monkeypatch: pytest.MonkeyPatch,
    isolated_limiter_factory: Callable[[Sequence[str] | None], ASAPRateLimiter],
) -> ASAPRateLimiter:
    """Replace global limiter with isolated instance using monkeypatch.

    Replaces the module-level ``limiter`` in ``asap.transport.middleware``.

    Returns:
        The new isolated limiter instance.
    """
    logger.debug(
        "test.fixture.replace_global_limiter",
        action="creating_isolated_limiter",
    )

    new_limiter = isolated_limiter_factory(None)

    import asap.transport.middleware as middleware_module

    logger.debug(
        "test.fixture.replace_global_limiter",
        action="monkeypatching_modules",
        limiter_id=id(new_limiter),
    )

    monkeypatch.setattr(middleware_module, "limiter", new_limiter)

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
    isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], ASAPRateLimiter]",
) -> "collections.abc.Callable[[Manifest, str | None, int | None, int | None, bool], FastAPI]":
    """Factory fixture for creating isolated FastAPI apps.

    NOTE: This is a utility/building-block fixture. For most tests, prefer creating
    specialized class-level fixtures instead (see test_rate_limiting.py for examples
    like isolated_app_5_per_minute). This pattern provides better readability and
    co-locates fixture configuration with the tests that use them.

    The returned function creates apps with isolated rate limiters to prevent
    interference between tests.

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
            use_monkeypatch: If True, replace global limiter in middleware module

        Returns:
            FastAPI app with isolated limiter configured
        """
        # Create isolated limiter
        limits = [rate_limit] if rate_limit else None
        isolated_limiter = isolated_limiter_factory(limits)

        # If use_monkeypatch, replace global limiter in middleware module
        if use_monkeypatch:
            import asap.transport.middleware as middleware_module

            monkeypatch.setattr(middleware_module, "limiter", isolated_limiter)

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

    The fixture automatically replaces the global limiter in the middleware
    module with a limiter that has very high limits.

    Example:
        class TestMyFeature(NoRateLimitTestBase):
            \"\"\"Tests for my feature without rate limiting interference.\"\"\"

            def test_something(self):
                # This test runs with rate limiting disabled
                app = create_app(manifest)
                # Rate limiting is automatically disabled
    """

    @pytest.fixture(autouse=True)
    def disable_rate_limiting(self, monkeypatch: pytest.MonkeyPatch) -> ASAPRateLimiter:
        """Automatically disable rate limiting for all tests in this class.

        Creates a limiter with very high limits and replaces the global limiter
        in the middleware module.

        Args:
            monkeypatch: Pytest monkeypatch fixture

        Returns:
            The no-limit limiter instance
        """
        no_limit_limiter = create_test_limiter(
            ["999999/minute"],
            key_func=get_remote_address,
        )

        import asap.transport.middleware as middleware_module

        monkeypatch.setattr(middleware_module, "limiter", no_limit_limiter)

        return no_limit_limiter
