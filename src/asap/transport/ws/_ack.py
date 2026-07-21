"""Acknowledgement retransmit layer for the ASAP WebSocket client.

The ``_AckRetransmit`` mixin owns the ADR-16 pending-ack tracker, periodic
timeout checks, retransmission budget, expiration handling, and circuit-breaker
integration.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from asap.models.envelope import Envelope
from asap.observability import get_logger
from asap.transport.ws.codecs import PAYLOAD_TYPES_REQUIRING_ACK

logger = get_logger(__name__)


@dataclass
class PendingAck:
    """Tracker for an envelope awaiting a server ``MessageAck`` (ADR-16)."""

    envelope_id: str
    sent_at: float
    retries: int
    original_envelope: Envelope


class _AckRetransmit:
    """Mixin: pending-ack tracking and retransmit/expire policy for WS sends.

    Hosts the ADR-16 reliability layer. The host class must initialize
    ``_pending_acks``, ``_ack_timeout_seconds``, ``_max_ack_retries``,
    ``_ack_check_interval``, ``_circuit_breaker``, ``_closed``, and ``_ws``
    before calling :meth:`_ack_check_loop` / :meth:`_register_pending_ack`.
    """

    _pending_acks: dict[str, PendingAck]
    _ack_timeout_seconds: float
    _max_ack_retries: int
    _ack_check_interval: float
    _circuit_breaker: Any
    _closed: bool
    _ws: Any

    def _requires_ack(self, envelope: Envelope) -> bool:
        """True when *envelope* opts into ack or its payload type mandates one."""
        if envelope.requires_ack:
            return True
        return envelope.payload_type in PAYLOAD_TYPES_REQUIRING_ACK

    def _register_pending_ack(self, envelope: Envelope) -> None:
        """Track *envelope* for retransmit if it requires a server ``MessageAck``."""
        if not envelope.id or not self._requires_ack(envelope):
            return
        self._pending_acks[envelope.id] = PendingAck(
            envelope_id=envelope.id,
            sent_at=time.monotonic(),
            retries=0,
            original_envelope=envelope,
        )

    async def _send_envelope_only(self, envelope: Envelope) -> None:
        """Send a frame without registering a pending ack (retransmit path)."""
        if self._ws is None:
            return
        await self._send_frame(envelope, register_ack=False)  # type: ignore[attr-defined]

    async def _ack_check_loop(self) -> None:
        """Periodically retransmit timed-out pending acks until the transport closes."""
        while not self._closed:
            try:
                await asyncio.sleep(self._ack_check_interval)
            except asyncio.CancelledError:
                break
            if self._closed or self._ws is None:
                break
            await self._retransmit_or_expire_pending_acks()
        logger.debug("asap.websocket.ack_check_loop_exit")

    async def _retransmit_or_expire_pending_acks(self) -> None:
        """Retransmit timed-out pending acks under the retry budget; expire the rest."""
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
        await self._run_retransmissions(to_retransmit, max_retries)
        for eid in to_remove:
            self._expire_pending_ack(eid, max_retries)

    def _expire_pending_ack(self, eid: str, max_retries: int) -> None:
        """Drop a pending ack past its retry budget and record a circuit failure."""
        self._pending_acks.pop(eid, None)
        if self._circuit_breaker is None:
            return
        self._circuit_breaker.record_failure()
        logger.warning(
            "asap.websocket.ack_max_retries",
            envelope_id=eid,
            max_retries=max_retries,
            message=(
                f"Ack not received for {eid} after {max_retries} retries; circuit breaker recorded"
            ),
        )

    async def _run_retransmissions(
        self, to_retransmit: list[tuple[str, PendingAck]], max_retries: int
    ) -> None:
        """Send each retransmission sequentially; record per-envelope retry state."""
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
            except Exception as e:  # noqa: BLE001 — one failed retransmit must not stop others
                logger.warning(
                    "asap.websocket.ack_retransmit_failed", envelope_id=eid, error=str(e)
                )


__all__ = ["_AckRetransmit"]
