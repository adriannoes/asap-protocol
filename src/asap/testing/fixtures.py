"""Pytest fixtures and context managers for ASAP tests.

This module provides shared fixtures and context managers to reduce
boilerplate when testing agents, clients, and snapshot stores.

Fixtures (use with pytest):
    mock_agent: Configurable mock agent for request/response tests.
    mock_client: ASAP client configured for testing (async; use in async tests).
    mock_snapshot_store: In-memory snapshot store for state persistence tests.

Context managers:
    test_agent(): Sync context manager yielding a MockAgent for the scope.
    test_client(): Async context manager yielding an ASAPClient for the scope.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

import pytest

from asap.state.snapshot import InMemorySnapshotStore
from asap.testing.mocks import MockAgent
from asap.transport.client import ASAPClient

DEFAULT_TEST_BASE_URL = "http://localhost:9999"


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a fresh MockAgent for the test.

    Returns:
        A MockAgent instance (cleared between tests via fresh fixture).
    """
    return MockAgent()


@pytest.fixture
def mock_snapshot_store() -> InMemorySnapshotStore:
    """Create an in-memory snapshot store for the test.

    Returns:
        An InMemorySnapshotStore instance (empty, isolated per test).
    """
    return InMemorySnapshotStore()


@pytest.fixture
async def mock_client() -> AsyncIterator[ASAPClient]:
    """Provide an ASAPClient entered for the test (async fixture).

    Yields an open ASAPClient pointing at DEFAULT_TEST_BASE_URL.
    Use in async tests; the client is closed after the test.

    Yields:
        ASAPClient instance (already in async context).
    """
    async with ASAPClient(DEFAULT_TEST_BASE_URL) as client:
        yield client


@contextmanager
def test_agent(agent_id: str = "urn:asap:agent:mock") -> Iterator[MockAgent]:
    """Context manager that provides a MockAgent for the scope.

    On exit, the agent is cleared (requests and responses reset).

    Args:
        agent_id: URN for the mock agent.

    Yields:
        A MockAgent instance.

    Example:
        >>> with test_agent() as agent:
        ...     agent.set_response("echo", {"status": "completed"})
        ...     out = agent.handle(request_envelope)
    """
    agent = MockAgent(agent_id)
    try:
        yield agent
    finally:
        agent.clear()


@asynccontextmanager
async def test_client(
    base_url: str = DEFAULT_TEST_BASE_URL,
) -> AsyncIterator[ASAPClient]:
    """Async context manager that provides an ASAPClient for the scope.

    Args:
        base_url: Agent base URL (default: localhost:9999 for test servers).

    Yields:
        An open ASAPClient instance.

    Example:
        >>> async with test_client("http://localhost:8000") as client:
        ...     response = await client.send(envelope)
    """
    async with ASAPClient(base_url) as client:
        yield client


__all__ = [
    "DEFAULT_TEST_BASE_URL",
    "mock_agent",
    "mock_client",
    "mock_snapshot_store",
    "test_agent",
    "test_client",
]
