"""ASAP testing utilities for easier test authoring.

This package provides pytest fixtures, mock agents, and custom assertions
to reduce boilerplate when testing ASAP protocol integrations.

Modules:
    fixtures: Pytest fixtures (mock_agent, mock_client, mock_snapshot_store)
              and context managers (test_agent, test_client).
    mocks: MockAgent for configurable mock agents with pre-set responses
           and request recording.
    assertions: Custom assertions (assert_envelope_valid, assert_task_completed,
              assert_response_correlates).

Example:
    >>> from asap.testing import MockAgent, assert_envelope_valid
    >>> from asap.testing.fixtures import mock_agent, test_client
"""

from asap.testing.assertions import (
    assert_envelope_valid,
    assert_response_correlates,
    assert_task_completed,
)
from asap.testing.mocks import MockAgent

__all__ = [
    "MockAgent",
    "assert_envelope_valid",
    "assert_response_correlates",
    "assert_task_completed",
]
