"""Transport-specific pytest fixtures.

This module provides fixtures specifically for transport layer tests,
including isolated rate limiters, test manifests, and app factories
that ensure complete test isolation.

The fixtures in this module implement an "aggressive monkeypatch" strategy
to completely replace module-level rate limiters, ensuring no interference
between tests even when slowapi.Limiter maintains global state.
"""

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Callable

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.server import create_app

if TYPE_CHECKING:
    from fastapi import FastAPI
    from slowapi import Limiter


@pytest.fixture
def isolated_limiter_factory() -> Callable[[Sequence[str] | None], "Limiter"]:
    """Factory fixture that returns a function to create isolated rate limiters.

    Each call to the returned function creates a new Limiter instance with
    a unique storage URI, ensuring complete isolation between test instances.

    Args:
        limits: Optional list of rate limit strings (e.g., ["100/minute"]).
            If None, defaults to very high limits for testing.

    Returns:
        A function that creates a new isolated Limiter instance

    Example:
        >>> def test_something(isolated_limiter_factory):
        ...     limiter = isolated_limiter_factory(["5/minute"])
        ...     app.state.limiter = limiter
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    def _create(limits: Sequence[str] | None = None) -> "Limiter":
        """Create a new isolated limiter instance.

        Args:
            limits: Optional list of rate limit strings. Defaults to very high limits.

        Returns:
            New Limiter instance with isolated storage
        """
        if limits is None:
            limits = ["100000/minute"]  # Very high default

        # Use unique storage URI to ensure complete isolation
        unique_storage_id = str(uuid.uuid4())
        return Limiter(
            key_func=get_remote_address,
            default_limits=list(limits),
            storage_uri=f"memory://{unique_storage_id}",
        )

    return _create


@pytest.fixture
def replace_global_limiter(
    monkeypatch: pytest.MonkeyPatch,
    isolated_limiter_factory: Callable[[Sequence[str] | None], "Limiter"],
) -> "Limiter":
    """Replace global limiter with isolated instance using aggressive monkeypatch.

    This fixture replaces the module-level limiter in both middleware and server
    modules, ensuring complete isolation even when code uses the global limiter
    directly. This is more aggressive than just replacing app.state.limiter.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        isolated_limiter_factory: Factory function to create isolated limiters

    Returns:
        The new isolated limiter instance

    Example:
        >>> def test_something(replace_global_limiter):
        ...     # Global limiter is now replaced, app will use it automatically
        ...     app = create_app(manifest)
    """
    # Create completely isolated limiter
    new_limiter = isolated_limiter_factory(None)

    # Replace in both modules
    import asap.transport.middleware as middleware_module
    import asap.transport.server as server_module

    monkeypatch.setattr(middleware_module, "limiter", new_limiter)
    monkeypatch.setattr(server_module, "limiter", new_limiter)

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
    isolated_limiter_factory: Callable[[Sequence[str] | None], "Limiter"],
) -> Callable[..., "FastAPI"]:
    """Factory fixture that returns a function to create isolated FastAPI apps.

    The returned function creates apps with isolated rate limiters to prevent
    test interference. Each app gets its own limiter instance.

    Args:
        monkeypatch: Pytest monkeypatch fixture for aggressive limiter replacement
        isolated_limiter_factory: Factory function to create isolated limiters

    Returns:
        A function that creates a new FastAPI app with isolated limiter

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
