"""Connection pool for :class:`asap.transport.ws.client.WebSocketTransport`.

Split out of ``ws/client.py`` so each module in the ``ws/`` package stays
under the 400-LOC ceiling mandated by the v2.5.1 thermo-nuclear patch. The
pool reuses connections to a single WebSocket URL with idle eviction.

Example:
    >>> async with WebSocketConnectionPool("ws://localhost:8080/asap/ws") as pool:
    ...     async with pool.acquire_context() as transport:
    ...         await transport.send(envelope)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from asap.observability import get_logger
from asap.transport.ws.client import WebSocketTransport
from asap.transport.ws.codecs import DEFAULT_POOL_IDLE_TIMEOUT, DEFAULT_POOL_MAX_SIZE

logger = get_logger(__name__)


class WebSocketConnectionPool:
    """Reusable pool of :class:`WebSocketTransport` connections to one URL."""

    def __init__(
        self,
        url: str,
        max_size: int = DEFAULT_POOL_MAX_SIZE,
        idle_timeout: float = DEFAULT_POOL_IDLE_TIMEOUT,
        **transport_kwargs: Any,
    ) -> None:
        self._url = url
        self._max_size = max_size
        self._idle_timeout = idle_timeout
        self._transport_kwargs = transport_kwargs
        self._available: asyncio.Queue[tuple[WebSocketTransport, float]] = asyncio.Queue()
        self._in_use_count = 0
        self._total_count = 0
        self._closed = False
        self._lock = asyncio.Lock()

    async def acquire(self) -> WebSocketTransport:
        async with self._lock:
            if self._closed:
                raise RuntimeError("WebSocketConnectionPool is closed")
            now = time.monotonic()
            while True:
                try:
                    transport, last_used = self._available.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if now - last_used > self._idle_timeout:
                    await transport.close()
                    self._total_count -= 1
                    continue
                if transport._ws is None:
                    self._total_count -= 1
                    continue
                self._in_use_count += 1
                return transport
            if self._total_count < self._max_size:
                transport = WebSocketTransport(**self._transport_kwargs)
                await transport.connect(self._url)
                self._total_count += 1
                self._in_use_count += 1
                return transport

        while True:
            transport, last_used = await self._available.get()
            async with self._lock:
                if self._closed:
                    await transport.close()
                    raise RuntimeError("WebSocketConnectionPool is closed")
                now = time.monotonic()
                if now - last_used > self._idle_timeout:
                    await transport.close()
                    self._total_count -= 1
                    continue
                if transport._ws is None:
                    self._total_count -= 1
                    continue
                self._in_use_count += 1
                return transport

    async def release(self, transport: WebSocketTransport) -> None:
        async with self._lock:
            self._in_use_count -= 1
            if self._closed:
                await transport.close()
                return
            if transport._ws is None:
                self._total_count -= 1
                return
            self._available.put_nowait((transport, time.monotonic()))

    @asynccontextmanager
    async def acquire_context(self) -> AsyncIterator[WebSocketTransport]:
        transport = await self.acquire()
        try:
            yield transport
        finally:
            await self.release(transport)

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
        while True:
            try:
                transport, _ = self._available.get_nowait()
            except asyncio.QueueEmpty:
                break
            with suppress(OSError):
                await transport.close()
        self._total_count = 0
        self._in_use_count = 0
        logger.debug("asap.websocket.pool_closed", url=self._url)


__all__ = ["WebSocketConnectionPool"]
