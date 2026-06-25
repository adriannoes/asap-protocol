"""Async HTTP client for ASAP protocol communication.

This package provides an async HTTP client for sending ASAP messages
between agents using JSON-RPC 2.0 over HTTP.

The ASAPClient provides:
- Async context manager for connection lifecycle (use is mandatory; see below)
- send() method for envelope exchange
- Automatic JSON-RPC wrapping
- Retry logic with idempotency keys
- Proper error handling and timeouts
- Structured logging for observability
- Compression support (gzip/brotli) for bandwidth reduction

**Context manager:** Always use ``async with ASAPClient(...) as client:`` so that
the underlying HTTP connection is closed when done. Instantiating without the
context manager may leave connections open.

The public surface (``ASAPClient``, ``RetryConfig``, ``CapabilityRequestReceipt``,
``ASAPConnectionError``, ``ASAPRemoteError``, ``ASAPTimeoutError``,
``_parse_max_age_from_cache_control``, ``DEFAULT_POOL_TIMEOUT``, ``logger``) is
re-exported here so ``from asap.transport.client import ASAPClient`` keeps working
after the v2.5.1 thermo-nuclear decomposition (S2 Task 2.3) split the original
monolithic ``client.py`` into ``client/{_helpers,_send,_discovery,_core}.py``.

The ``asyncio``, ``time``, and ``httpx`` modules are re-bound onto this package so
that existing ``patch("asap.transport.client.asyncio.sleep")`` /
``patch("asap.transport.client.time.time")`` /
``patch("asap.transport.client.httpx.AsyncClient")`` monkeypatch targets continue
to resolve (they patch the attribute on this package namespace, which the helpers
and core import from).

Example:
    >>> from asap.transport.client import ASAPClient
    >>> from asap.models.envelope import Envelope
    >>>
    >>> async with ASAPClient("http://agent.example.com") as client:
    ...     response = await client.send(request_envelope)
    ...     print(response.payload_type)
    >>>
    >>> # With compression enabled (default for payloads > 1KB)
    >>> async with ASAPClient("http://agent.example.com", compression=True) as client:
    ...     response = await client.send(large_envelope)  # Compressed automatically
"""

from __future__ import annotations

# Re-bind stdlib / third-party modules used as monkeypatch targets by tests and
# chaos suites (e.g. ``patch("asap.transport.client.asyncio.sleep")``). These
# names must exist on the package namespace so the patches resolve.
import asyncio as asyncio
import time as time

import httpx as httpx

from asap.errors import (
    ASAPConnectionError,
    ASAPRemoteError,
    ASAPTimeoutError,
)
from asap.transport.client._core import ASAPClient as ASAPClient, RetryConfig as RetryConfig
from asap.transport.client._discovery import CapabilityRequestReceipt as CapabilityRequestReceipt
from asap.transport.client._helpers import (
    DEFAULT_POOL_TIMEOUT as DEFAULT_POOL_TIMEOUT,
    _parse_max_age_from_cache_control as _parse_max_age_from_cache_control,
    logger as logger,
)

__all__ = [
    "ASAPClient",
    "RetryConfig",
    "CapabilityRequestReceipt",
    "ASAPConnectionError",
    "ASAPRemoteError",
    "ASAPTimeoutError",
]
