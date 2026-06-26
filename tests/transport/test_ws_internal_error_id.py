"""WS internal-error frames must preserve the JSON-RPC ``id`` (CR#5).

``_send_internal_error_frame`` hardcoded ``"id": None`` even though the request
``response_id`` was in scope at both call sites, so clients could not correlate
internal-error failures back to the request that triggered them. The fix threads
``response_id`` through so the frame carries the request id when known.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import WebSocket

from asap.transport.ws._dispatch import _send_internal_error_frame


def _ws_stub(sent: list[str]) -> Any:
    ws = MagicMock(spec=WebSocket)

    async def _send_text(payload: str) -> None:
        sent.append(payload)

    ws.send_text = _send_text
    return ws


class TestWSInternalErrorIdPreserved:
    """CR#5: the request id is preserved on internal-error frames."""

    @pytest.mark.asyncio
    async def test_response_id_is_set_on_error_frame(self) -> None:
        """A known response_id is carried onto the internal-error frame."""
        sent: list[str] = []
        ws = _ws_stub(sent)

        await _send_internal_error_frame(ws, RuntimeError("boom"), response_id="req-99")

        assert len(sent) == 1
        frame = json.loads(sent[0])
        assert frame["id"] == "req-99"
        assert frame["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_response_id_defaults_to_none_when_unknown(self) -> None:
        """When response_id is not provided, the frame falls back to ``None`` (no regression)."""
        sent: list[str] = []
        ws = _ws_stub(sent)

        await _send_internal_error_frame(ws, RuntimeError("boom"))

        assert len(sent) == 1
        frame = json.loads(sent[0])
        assert frame["id"] is None
