"""Async HTTP client package for ASAP protocol communication.

This package provides an async client for sending ASAP messages between agents
using JSON-RPC 2.0 over HTTP, with optional WebSocket transport support.

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

The public surface is re-exported here for ``from asap.transport.client import
ASAPClient`` compatibility. ``asyncio``, ``time``, and ``httpx`` are also bound
on this package for test patching of client internals.

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

# Re-exported for test patching of client internals.
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
