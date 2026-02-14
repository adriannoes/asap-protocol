"""WebSocket transport for ASAP protocol.

This module provides WebSocket server and client support for real-time
bidirectional communication. ASAP messages are framed as JSON over WebSocket
at the path /asap/ws. Uses JSON-RPC 2.0 over WebSocket (same as HTTP transport).

Message framing:
- One WebSocket text frame = one JSON-RPC 2.0 request or response.
- Request: {"jsonrpc":"2.0","method":"asap.send","params":{"envelope":{...}},"id":...}
- Response: {"jsonrpc":"2.0","result":{"envelope":{...}},"id":...} or error object.
- Binary mode (base64) reserved for future use via FRAME_ENCODING_BINARY.
"""

from __future__ import annotations

import asyncio
import ssl
import base64
import itertools
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

import websockets
from fastapi import WebSocket
from pydantic import ValidationError
from starlette.requests import Request

from asap.models.envelope import Envelope
from asap.models.payloads import MessageAck
from asap.observability import get_logger
from asap.transport.circuit_breaker import CircuitBreaker
from asap.transport.jsonrpc import ASAP_METHOD
from asap.transport.rate_limit import (
    DEFAULT_WS_MESSAGES_PER_SECOND,
    WebSocketTokenBucket,
)

# JSON-RPC method for server push of MessageAck (ADR-16)
ASAP_ACK_METHOD = "asap.ack"

if TYPE_CHECKING:
    from asap.transport.server import ASAPRequestHandler
    from websockets.legacy.client import WebSocketClientProtocol

logger = get_logger(__name__)

# Frame encoding: JSON text (current) or binary base64 (reserved for future)
FRAME_ENCODING_JSON: Literal["json"] = "json"
FRAME_ENCODING_BINARY: Literal["binary"] = "binary"

# Default timeout for WebSocket receive (seconds)
DEFAULT_WS_RECEIVE_TIMEOUT = 60.0

# Heartbeat: server sends ping every N seconds; connections stale if no activity for M seconds
HEARTBEAT_PING_INTERVAL = 30.0
STALE_CONNECTION_TIMEOUT = 90.0

# Application-level ping/pong frame type (for server-initiated heartbeat; client responds with pong)
HEARTBEAT_FRAME_TYPE_PING = "ping"
HEARTBEAT_FRAME_TYPE_PONG = "pong"

# Reconnection: exponential backoff (1s, 2s, 4s, ...) capped at 30s
RECONNECT_INITIAL_BACKOFF = 1.0
RECONNECT_MAX_BACKOFF = 30.0

# Connection pool: reuse connections to same host
DEFAULT_POOL_MAX_SIZE = 10
DEFAULT_POOL_IDLE_TIMEOUT = 60.0

# Payload types that require MessageAck over WebSocket (ADR-16)
PAYLOAD_TYPES_REQUIRING_ACK = frozenset(
    {
        "TaskRequest",
        "task.request",
        "TaskCancel",
        "task.cancel",
        "StateRestore",
        "state_restore",
        "MessageSend",
        "message.send",
        "message_send",
    }
)

# Ack-aware client (ADR-16): check pending acks every N seconds
ACK_CHECK_INTERVAL = 5.0
DEFAULT_ACK_TIMEOUT = 30.0
DEFAULT_MAX_ACK_RETRIES = 3


@dataclass
class PendingAck:
    envelope_id: str
    sent_at: float
    retries: int
    original_envelope: Envelope


def _reconnect_delay(
    attempt: int,
    initial_backoff: float = RECONNECT_INITIAL_BACKOFF,
    max_backoff: float = RECONNECT_MAX_BACKOFF,
) -> float:
    return float(min(initial_backoff * (2 ** (attempt - 1)), max_backoff))


__all__ = [
    "ACK_CHECK_INTERVAL",
    "DEFAULT_ACK_TIMEOUT",
    "DEFAULT_MAX_ACK_RETRIES",
    "DEFAULT_POOL_IDLE_TIMEOUT",
    "DEFAULT_POOL_MAX_SIZE",
    "DEFAULT_WS_RECEIVE_TIMEOUT",
    "FRAME_ENCODING_BINARY",
    "FRAME_ENCODING_JSON",
    "HEARTBEAT_FRAME_TYPE_PING",
    "HEARTBEAT_FRAME_TYPE_PONG",
    "HEARTBEAT_PING_INTERVAL",
    "OnMessageCallback",
    "PendingAck",
    "RECONNECT_INITIAL_BACKOFF",
    "RECONNECT_MAX_BACKOFF",
    "STALE_CONNECTION_TIMEOUT",
    "WebSocketConnectionPool",
    "WebSocketRemoteError",
    "WebSocketTransport",
    "WS_CLOSE_GOING_AWAY",
    "WS_CLOSE_POLICY_VIOLATION",
    "WS_CLOSE_REASON_SHUTDOWN",
    "decode_frame_to_json",
    "encode_envelope_frame",
    "handle_websocket_connection",
]


class WebSocketRemoteError(Exception):
    def __init__(
        self,
        code: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"WebSocket remote error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data or {}


def encode_envelope_frame(
    envelope: dict[str, Any],
    request_id: str | int = "",
    encoding: Literal["json", "binary"] = FRAME_ENCODING_JSON,
) -> str | bytes:
    payload = {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {"envelope": envelope},
        "id": request_id,
    }
    text = json.dumps(payload)
    if encoding == FRAME_ENCODING_BINARY:
        return base64.b64encode(text.encode("utf-8"))
    return text


def decode_frame_to_json(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Invalid binary frame (base64): {e}") from e
    return cast(dict[str, Any], json.loads(raw))


# Type for optional callback on server-push messages (sync or async)
OnMessageCallback = Callable[[Envelope], None] | Callable[[Envelope], Awaitable[None]]


class WebSocketTransport:
    def __init__(
        self,
        receive_timeout: float = DEFAULT_WS_RECEIVE_TIMEOUT,
        on_message: OnMessageCallback | None = None,
        ping_interval: float | None = HEARTBEAT_PING_INTERVAL,
        ping_timeout: float | None = 20.0,
        reconnect_on_disconnect: bool = False,
        max_reconnect_attempts: int | None = None,
        initial_backoff: float = RECONNECT_INITIAL_BACKOFF,
        max_backoff: float = RECONNECT_MAX_BACKOFF,
        ack_timeout_seconds: float = DEFAULT_ACK_TIMEOUT,
        max_ack_retries: int = DEFAULT_MAX_ACK_RETRIES,
        circuit_breaker: CircuitBreaker | None = None,
        ack_check_interval: float = ACK_CHECK_INTERVAL,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._ws: WebSocketClientProtocol | None = None
        self._receive_timeout = receive_timeout
        self._on_message = on_message
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._reconnect_on_disconnect = reconnect_on_disconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._ack_timeout_seconds = ack_timeout_seconds
        self._max_ack_retries = max_ack_retries
        self._circuit_breaker = circuit_breaker
        self._ack_check_interval = ack_check_interval
        self._request_counter = itertools.count(1)
        self._pending: dict[str, asyncio.Future[Envelope]] = {}
        self._pending_acks: dict[str, PendingAck] = {}
        self._recv_task: asyncio.Task[None] | None = None
        self._ack_check_task: asyncio.Task[None] | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._closed = False
        self._connected_event: asyncio.Event = asyncio.Event()
        self._connect_error: Exception | None = None
        self._ssl_context = ssl_context

    async def _do_connect(self, url: str) -> None:
        if self._ws is not None:
            return
        if self._ack_check_task is not None:
            self._ack_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ack_check_task
            self._ack_check_task = None
        self._connect_error = None
        logger.info("asap.websocket.client_connecting", url=url)
        # cast: connect() return type varies by websockets version (legacy vs asyncio client)
        connect_kwargs: dict[str, Any] = {
            "open_timeout": 10.0,
            "close_timeout": 5.0,
            "ping_interval": self._ping_interval,
            "ping_timeout": self._ping_timeout,
        }
        if self._ssl_context is not None:
            connect_kwargs["ssl"] = self._ssl_context
        self._ws = cast(
            Any,
            await websockets.connect(url, **connect_kwargs),
        )
        if self._closed:
            ws = self._ws
            if ws is not None:
                await ws.close()
            self._ws = None
            return
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._ack_check_task = asyncio.create_task(self._ack_check_loop())
        self._connected_event.set()
        logger.info("asap.websocket.client_connected", url=url)

    async def _run_loop(self, url: str) -> None:
        attempt = 0
        while not self._closed:
            self._connected_event.clear()
            try:
                await self._do_connect(url)
            except Exception as e:
                if attempt == 0:
                    self._connect_error = e
                    self._connected_event.set()
                    raise
                logger.warning(
                    "asap.websocket.reconnect_connect_error",
                    error=str(e),
                    attempt=attempt,
                )
                self._ws = None
                self._recv_task = None
                attempt += 1
                if (
                    self._max_reconnect_attempts is not None
                    and attempt >= self._max_reconnect_attempts
                ):
                    return
                delay = _reconnect_delay(
                    attempt,
                    self._initial_backoff,
                    self._max_backoff,
                )
                await asyncio.sleep(delay)
                continue
            if attempt > 0:
                logger.info(
                    "asap.websocket.reconnected",
                    url=url,
                    attempt=attempt,
                )
            if self._recv_task is not None:
                with suppress(asyncio.CancelledError):
                    await self._recv_task
            if self._closed:
                break
            if self._ws is not None:
                with suppress(OSError):
                    await self._ws.close()
                self._ws = None
            self._recv_task = None
            attempt += 1
            if self._max_reconnect_attempts is not None and attempt >= self._max_reconnect_attempts:
                logger.warning(
                    "asap.websocket.reconnect_max_attempts",
                    attempt=attempt,
                )
                break
            delay = _reconnect_delay(
                attempt,
                self._initial_backoff,
                self._max_backoff,
            )
            logger.debug(
                "asap.websocket.reconnect_backoff",
                delay=delay,
                attempt=attempt,
            )
            await asyncio.sleep(delay)

    async def connect(self, url: str) -> None:
        if self._ws is not None:
            return
        self._closed = False
        if self._reconnect_on_disconnect:
            self._run_task = asyncio.create_task(self._run_loop(url))
            await self._connected_event.wait()
            if self._connect_error is not None:
                err = self._connect_error
                self._connect_error = None
                if self._run_task is not None:
                    with suppress(asyncio.CancelledError):
                        await self._run_task
                    self._run_task = None
                raise err
        else:
            await self._do_connect(url)

    async def _recv_loop(self) -> None:
        if self._ws is None:
            return
        try:
            while self._ws is not None:
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    data = decode_frame_to_json(raw)
                except ValueError as e:
                    logger.warning("asap.websocket.recv_loop_parse_error", error=str(e))
                    continue
                if data.get("type") == HEARTBEAT_FRAME_TYPE_PING and "method" not in data:
                    if self._ws is not None:
                        await self._ws.send(json.dumps({"type": HEARTBEAT_FRAME_TYPE_PONG}))
                    continue
                if data.get("method") == ASAP_ACK_METHOD and "params" in data:
                    params = data.get("params") or {}
                    env_dict = params.get("envelope") if isinstance(params, dict) else None
                    if isinstance(env_dict, dict):
                        try:
                            ack_env = Envelope.model_validate(env_dict)
                            if ack_env.payload_type == "MessageAck" and isinstance(
                                ack_env.payload, dict
                            ):
                                ack = MessageAck.model_validate(ack_env.payload)
                                self._pending_acks.pop(ack.original_envelope_id, None)
                        except ValidationError:
                            pass
                    continue
                request_id = data.get("id")
                if "error" in data:
                    err = data["error"]
                    code = err.get("code", -32603)
                    msg = err.get("message", "Unknown error")
                    err_data = err.get("data")
                    exc = WebSocketRemoteError(code, msg, err_data)
                    if request_id is not None and request_id in self._pending:
                        future = self._pending.pop(request_id, None)
                        if future is not None and not future.done():
                            future.set_exception(exc)
                    else:
                        logger.warning(
                            "asap.websocket.recv_loop_error_frame",
                            code=code,
                            message=msg,
                        )
                    continue
                result = data.get("result")
                if not result or "envelope" not in result:
                    if request_id is not None and request_id in self._pending:
                        future = self._pending.pop(request_id, None)
                        if future is not None and not future.done():
                            future.set_exception(
                                WebSocketRemoteError(
                                    -32603,
                                    "Missing result.envelope in response",
                                    data=data,
                                )
                            )
                    continue
                envelope = Envelope.model_validate(result["envelope"])
                if request_id is not None and request_id in self._pending:
                    future = self._pending.pop(request_id, None)
                    if future is not None and not future.done():
                        future.set_result(envelope)
                elif self._on_message is not None:
                    try:
                        cb = self._on_message(envelope)
                        if asyncio.iscoroutine(cb):
                            await cb
                    except Exception as e:
                        logger.warning(
                            "asap.websocket.on_message_error",
                            error=str(e),
                        )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("asap.websocket.recv_loop_error", error=str(e))
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(WebSocketRemoteError(-32603, str(e)))
            self._pending.clear()

    async def close(self) -> None:
        self._closed = True
        self._connected_event.set()
        if self._ack_check_task is not None:
            self._ack_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ack_check_task
            self._ack_check_task = None
        if self._run_task is not None:
            self._run_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._run_task
            self._run_task = None
        if self._recv_task is not None:
            self._recv_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._recv_task
            self._recv_task = None
        self._pending_acks.clear()
        for future in self._pending.values():
            if not future.done():
                future.set_exception(asyncio.TimeoutError("Connection closed"))
        self._pending.clear()
        if self._ws is not None:
            with suppress(OSError):
                await self._ws.close()
            self._ws = None
            logger.debug("asap.websocket.client_closed")

    async def __aenter__(self) -> "WebSocketTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _next_request_id(self) -> str:
        return f"ws-req-{next(self._request_counter)}"

    def _envelope_dict_for_send(self, envelope: Envelope) -> dict[str, Any]:
        dump = envelope.model_dump(mode="json")
        if not dump.get("requires_ack") and dump.get("payload_type") in PAYLOAD_TYPES_REQUIRING_ACK:
            dump = {**dump, "requires_ack": True}
        return dump

    def _requires_ack(self, envelope: Envelope) -> bool:
        if envelope.requires_ack:
            return True
        return envelope.payload_type in PAYLOAD_TYPES_REQUIRING_ACK

    def _register_pending_ack(self, envelope: Envelope) -> None:
        if not envelope.id or not self._requires_ack(envelope):
            return
        self._pending_acks[envelope.id] = PendingAck(
            envelope_id=envelope.id,
            sent_at=time.monotonic(),
            retries=0,
            original_envelope=envelope,
        )

    async def _send_envelope_only(self, envelope: Envelope) -> None:
        if self._ws is None:
            return
        request_id = self._next_request_id()
        frame = encode_envelope_frame(
            self._envelope_dict_for_send(envelope),
            request_id=request_id,
            encoding=FRAME_ENCODING_JSON,
        )
        if not isinstance(frame, str):
            raise TypeError(f"Expected text frame (str), got {type(frame).__name__}")
        await self._ws.send(frame)

    async def _ack_check_loop(self) -> None:
        while not self._closed:
            try:
                await asyncio.sleep(self._ack_check_interval)
            except asyncio.CancelledError:
                break
            if self._closed or self._ws is None:
                break
            now = time.monotonic()
            timeout = self._ack_timeout_seconds
            max_retries = self._max_ack_retries
            to_retransmit: list[tuple[str, PendingAck]] = []
            to_remove: list[str] = []
            for eid, pending in list(self._pending_acks.items()):
                if now - pending.sent_at <= timeout:
                    continue
                if pending.retries < max_retries:
                    to_retransmit.append((eid, pending))
                else:
                    to_remove.append(eid)
            for eid, pending in to_retransmit:
                try:
                    await self._send_envelope_only(pending.original_envelope)
                    pending.sent_at = time.monotonic()
                    pending.retries += 1
                    logger.info(
                        "asap.websocket.ack_retransmit",
                        envelope_id=eid,
                        retries=pending.retries,
                        max_retries=max_retries,
                    )
                except Exception as e:
                    logger.warning(
                        "asap.websocket.ack_retransmit_failed",
                        envelope_id=eid,
                        error=str(e),
                    )
            for eid in to_remove:
                self._pending_acks.pop(eid, None)
                if self._circuit_breaker is not None:
                    self._circuit_breaker.record_failure()
                    logger.warning(
                        "asap.websocket.ack_max_retries",
                        envelope_id=eid,
                        max_retries=max_retries,
                        message=f"Ack not received for {eid} after {max_retries} retries; circuit breaker recorded",
                    )
        logger.debug("asap.websocket.ack_check_loop_exit")

    async def send(self, envelope: Envelope) -> None:
        if self._ws is None:
            raise RuntimeError("WebSocket not connected; call connect(url) first")
        request_id = self._next_request_id()
        frame = encode_envelope_frame(
            self._envelope_dict_for_send(envelope),
            request_id=request_id,
            encoding=FRAME_ENCODING_JSON,
        )
        if not isinstance(frame, str):
            raise TypeError(f"Expected text frame (str), got {type(frame).__name__}")
        await self._ws.send(frame)
        self._register_pending_ack(envelope)

    async def send_and_receive(self, envelope: Envelope) -> Envelope:
        if self._ws is None:
            raise RuntimeError("WebSocket not connected; call connect(url) first")
        request_id = self._next_request_id()
        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        frame = encode_envelope_frame(
            self._envelope_dict_for_send(envelope),
            request_id=request_id,
            encoding=FRAME_ENCODING_JSON,
        )
        if not isinstance(frame, str):
            raise TypeError(f"Expected text frame (str), got {type(frame).__name__}")
        try:
            await self._ws.send(frame)
            self._register_pending_ack(envelope)
            return await asyncio.wait_for(future, timeout=self._receive_timeout)
        finally:
            self._pending.pop(request_id, None)

    async def receive(self) -> Envelope:
        if self._ws is None:
            raise RuntimeError("WebSocket not connected; call connect(url) first")
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self._receive_timeout)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = decode_frame_to_json(raw)
        if "error" in data:
            err = data["error"]
            raise WebSocketRemoteError(
                err.get("code", -32603),
                err.get("message", "Unknown error"),
                err.get("data"),
            )
        result = data.get("result")
        if not result or "envelope" not in result:
            raise WebSocketRemoteError(
                -32603,
                "Missing result.envelope in response",
                data=data,
            )
        return Envelope.model_validate(result["envelope"])


class WebSocketConnectionPool:
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


async def _make_fake_request(body: str, websocket: WebSocket) -> Request:
    body_bytes = body.encode("utf-8")
    headers = list(websocket.scope.get("headers", []))
    headers.append((b"content-length", str(len(body_bytes)).encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "headers": headers,
        "path": websocket.scope.get("path", "/asap"),
        "root_path": "",
        "query_string": b"",
        "server": websocket.scope.get("server", ("localhost", 8000)),
    }
    first_receive = True

    async def receive() -> dict[str, Any]:
        nonlocal first_receive
        if first_receive:
            first_receive = False
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(_: MutableMapping[str, Any]) -> None:
        pass

    return Request(scope, receive, send)


def _is_heartbeat_pong(data: dict[str, Any]) -> bool:
    return data.get("type") == HEARTBEAT_FRAME_TYPE_PONG and "method" not in data


def _build_ack_notification_frame(
    original_envelope_id: str,
    status: Literal["received", "processed", "rejected"],
    sender: str,
    recipient: str,
    asap_version: str = "0.1",
    error: str | None = None,
) -> str:
    ack_payload = MessageAck(
        original_envelope_id=original_envelope_id,
        status=status,
        error=error,
    )
    ack_envelope = Envelope(
        asap_version=asap_version,
        sender=sender,
        recipient=recipient,
        payload_type="MessageAck",
        payload=ack_payload.model_dump(),
    )
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "method": ASAP_ACK_METHOD,
            "params": {"envelope": ack_envelope.model_dump(mode="json")},
        }
    )


async def _heartbeat_loop(
    websocket: WebSocket,
    last_received: list[float],
    closed: asyncio.Event,
) -> None:
    while not closed.is_set():
        try:
            await asyncio.sleep(HEARTBEAT_PING_INTERVAL)
            if closed.is_set():
                return
            now = time.monotonic()
            if now - last_received[0] > STALE_CONNECTION_TIMEOUT:
                logger.info(
                    "asap.websocket.stale_connection",
                    idle_seconds=now - last_received[0],
                )
                closed.set()
                return
            ping_frame = json.dumps({"type": HEARTBEAT_FRAME_TYPE_PING})
            await websocket.send_text(ping_frame)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.debug("asap.websocket.heartbeat_error", error=str(e))
            closed.set()
            return


# Close code and reason for graceful server shutdown (RFC 6455)
WS_CLOSE_GOING_AWAY = 1001
WS_CLOSE_REASON_SHUTDOWN = "Server shutting down"

# Rate limit: close code when client exceeds message rate (RFC 6455 policy violation)
WS_CLOSE_POLICY_VIOLATION = 1008


async def handle_websocket_connection(
    websocket: WebSocket,
    request_handler: "ASAPRequestHandler",
    active_connections: set[WebSocket] | None = None,
    ws_message_rate_limit: float | None = DEFAULT_WS_MESSAGES_PER_SECOND,
) -> None:
    await websocket.accept()
    if active_connections is not None:
        active_connections.add(websocket)
    logger.info("asap.websocket.connected", client=websocket.client)
    last_received: list[float] = [time.monotonic()]
    closed = asyncio.Event()
    rate_limited = False
    bucket: WebSocketTokenBucket | None = (
        WebSocketTokenBucket(rate=ws_message_rate_limit)
        if ws_message_rate_limit is not None and ws_message_rate_limit > 0
        else None
    )
    heartbeat_task: asyncio.Task[None] | None = None
    try:
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(websocket, last_received, closed),
        )
        while not closed.is_set():
            try:
                raw = await websocket.receive_text()
            except Exception as e:
                logger.warning(
                    "asap.websocket.receive_error",
                    error=str(e),
                )
                break
            last_received[0] = time.monotonic()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if _is_heartbeat_pong(data):
                continue
            if bucket is not None and not bucket.consume(1):
                rate_limited = True
                logger.warning(
                    "asap.websocket.rate_limit_exceeded",
                    client=websocket.client,
                    limit_per_sec=bucket.rate,
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32001,
                                "message": "Rate limit exceeded; too many messages per second",
                            },
                            "id": data.get("id"),
                        }
                    )
                )
                break
            envelope_for_ack: Envelope | None = None
            requires_ack = False
            params = data.get("params")
            envelope_dict = params.get("envelope") if isinstance(params, dict) else None
            if isinstance(envelope_dict, dict):
                try:
                    envelope_for_ack = Envelope.model_validate(envelope_dict)
                    requires_ack = envelope_for_ack.requires_ack
                except ValidationError:
                    pass
            if requires_ack and envelope_for_ack is not None and envelope_for_ack.id:
                ack_frame = _build_ack_notification_frame(
                    original_envelope_id=envelope_for_ack.id,
                    status="received",
                    sender=envelope_for_ack.recipient,
                    recipient=envelope_for_ack.sender,
                    asap_version=envelope_for_ack.asap_version,
                )
                await websocket.send_text(ack_frame)
            try:
                request = await _make_fake_request(raw, websocket)
                response = await request_handler.handle_message(request)
                body = response.body
                await websocket.send_text(
                    body.decode("utf-8") if isinstance(body, bytes) else str(body)
                )
            except Exception as e:
                logger.warning(
                    "asap.websocket.message_error",
                    error=str(e),
                )
                if requires_ack and envelope_for_ack is not None and envelope_for_ack.id:
                    reject_frame = _build_ack_notification_frame(
                        original_envelope_id=envelope_for_ack.id,
                        status="rejected",
                        sender=envelope_for_ack.recipient,
                        recipient=envelope_for_ack.sender,
                        asap_version=envelope_for_ack.asap_version,
                        error=str(e),
                    )
                    await websocket.send_text(reject_frame)
                try:
                    error_payload = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": {"error": str(e)},
                        },
                        "id": None,
                    }
                    await websocket.send_text(json.dumps(error_payload))
                except Exception:
                    break
    except Exception as e:
        logger.warning("asap.websocket.connection_error", error=str(e))
    finally:
        closed.set()
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
        if active_connections is not None:
            active_connections.discard(websocket)
        try:
            await websocket.close(
                code=WS_CLOSE_POLICY_VIOLATION if rate_limited else WS_CLOSE_GOING_AWAY
            )
        except (OSError, RuntimeError) as close_err:
            logger.debug("asap.websocket.close_error", error=str(close_err))
        logger.info("asap.websocket.closed", client=websocket.client)
