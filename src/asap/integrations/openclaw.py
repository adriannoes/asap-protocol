"""OpenClaw integration: OpenClawAsapBridge for hybrid pipelines (OpenClaw + ASAP)."""

from __future__ import annotations

from typing import Any

from asap.client.market import AgentSummary, MarketClient
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.ids import generate_id

# Sentinel prefix for error results returned by the bridge (string messages).
_ERROR_PREFIX = "Error:"


def is_error_result(result: str | dict[str, Any]) -> bool:
    """True if bridge returned an error string (starts with \"Error:\") instead of a dict."""
    return isinstance(result, str) and result.startswith(_ERROR_PREFIX)


def get_result(result: str | dict[str, Any]) -> dict[str, Any]:
    """Return success dict or raise ValueError with error message."""
    if is_error_result(result):
        raise ValueError(str(result))
    assert isinstance(result, dict)
    return result


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
        try:
            resolved = await self._client.resolve(urn)
            payload = {
                "conversation_id": generate_id(),
                "skill_id": skill_id,
                "input": input_payload,
            }
            return await resolved.run(payload, auth_token=auth_token)
        except AgentRevokedException as e:
            return f"{_ERROR_PREFIX} Agent revoked: {e!s}"
        except SignatureVerificationError as e:
            return f"{_ERROR_PREFIX} Signature verification failed: {e!s}"
        except ValueError as e:
            return f"{_ERROR_PREFIX} Invalid request or URN: {e!s}"

    async def run_asap_auto_skill(
        self,
        urn: str,
        input_payload: dict[str, Any],
        auth_token: str | None = None,
    ) -> str | dict[str, Any]:
        try:
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
        except AgentRevokedException as e:
            return f"{_ERROR_PREFIX} Agent revoked: {e!s}"
        except SignatureVerificationError as e:
            return f"{_ERROR_PREFIX} Signature verification failed: {e!s}"
        except ValueError as e:
            return f"{_ERROR_PREFIX} Invalid request or URN: {e!s}"
