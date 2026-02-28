"""OpenClaw integration: OpenClawAsapBridge for hybrid pipelines (OpenClaw + ASAP)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from asap.client.market import AgentSummary, MarketClient
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.ids import generate_id

# Sentinel prefix for error results returned by the bridge (string messages).
_ERROR_PREFIX = "Error:"

logger = logging.getLogger(__name__)


def is_error_result(result: str | dict[str, Any]) -> bool:
    """True if bridge returned an error string (starts with \"Error:\") instead of a dict."""
    return isinstance(result, str) and result.startswith(_ERROR_PREFIX)


def get_result(result: str | dict[str, Any]) -> dict[str, Any]:
    """Return success dict or raise ValueError/TypeError with error message."""
    if is_error_result(result):
        raise ValueError(str(result))
    if not isinstance(result, dict):
        raise TypeError(f"Expected dict result, got {type(result).__name__}")
    return result


def _format_bridge_error(kind: str, message: str) -> str:
    """Return a consistent error string for bridge failures."""
    return f"{_ERROR_PREFIX} {kind}: {message}"


async def _safe_invoke(
    urn: str,
    coro_fn: Callable[[], Awaitable[str | dict[str, Any]]],
) -> str | dict[str, Any]:
    """Run the given coroutine and convert known exceptions to error strings with logging."""
    try:
        return await coro_fn()
    except AgentRevokedException as e:
        logger.warning("agent_revoked", extra={"urn": urn, "error": str(e)})
        return _format_bridge_error("Agent revoked", str(e))
    except SignatureVerificationError as e:
        logger.warning("signature_verification_failed", extra={"urn": urn, "error": str(e)})
        return _format_bridge_error("Signature verification failed", str(e))
    except ValueError as e:
        logger.warning("invalid_request_or_urn", extra={"urn": urn, "error": str(e)})
        return _format_bridge_error("Invalid request or URN", str(e))


class OpenClawAsapBridge:
    """Bridge for hybrid pipelines: invoke ASAP agents from OpenClaw workflows via Lite Registry."""

    def __init__(
        self,
        client: MarketClient | None = None,
        *,
        registry_url: str | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        elif registry_url is not None:
            self._client = MarketClient(registry_url=registry_url)
        else:
            self._client = MarketClient()

    async def list_agents(self) -> list[AgentSummary]:
        """List agents from the Lite Registry (URN, name, skill_ids)."""
        return await self._client.list_agents()

    async def run_asap(
        self,
        urn: str,
        skill_id: str,
        input_payload: dict[str, Any],
        auth_token: str | None = None,
    ) -> str | dict[str, Any]:
        async def _do_run() -> str | dict[str, Any]:
            resolved = await self._client.resolve(urn)
            payload = {
                "conversation_id": generate_id(),
                "skill_id": skill_id,
                "input": input_payload,
            }
            return await resolved.run(payload, auth_token=auth_token)

        return await _safe_invoke(urn, _do_run)

    async def run_asap_auto_skill(
        self,
        urn: str,
        input_payload: dict[str, Any],
        auth_token: str | None = None,
    ) -> str | dict[str, Any]:
        async def _do_run() -> str | dict[str, Any]:
            resolved = await self._client.resolve(urn)
            skills = getattr(resolved.manifest.capabilities, "skills", None) or []
            if not skills:
                return f"{_ERROR_PREFIX} Agent has no skills; cannot build task request."
            skill_id = getattr(skills[0], "id", "unknown") or "unknown"
            payload = {
                "conversation_id": generate_id(),
                "skill_id": skill_id,
                "input": input_payload,
            }
            return await resolved.run(payload, auth_token=auth_token)

        return await _safe_invoke(urn, _do_run)
