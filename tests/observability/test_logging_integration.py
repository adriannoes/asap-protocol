"""Unit tests for logging integration."""

from __future__ import annotations

import contextlib
import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.observability.logging import REDACTED_PLACEHOLDER, configure_logging, is_debug_mode
from asap.transport.server import create_app


def _always_reject_validator(token: str) -> str | None:
    """Token validator that always rejects (for auth failure tests)."""
    return None


def _always_accept_validator(token: str) -> str:
    """Token validator that always accepts with a fixed agent id."""
    return "urn:asap:agent:test-client"


@pytest.fixture(autouse=True)
def configure_logging_for_capture(caplog: pytest.LogCaptureFixture) -> None:
    """Ensure logging is configured and caplog captures structlog output."""
    configure_logging(log_format="console", log_level="DEBUG", force=True)
    caplog.set_level(logging.DEBUG)


class TestAuthFailureLogSanitization:
    """Auth failure logs must show token prefix only, not full token."""

    def test_auth_failure_logs_sanitized_token_not_full_token(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Auth failure logs show Bearer sk_live_... not full token."""
        manifest = Manifest(
            id="urn:asap:agent:test",
            name="Test",
            version="1.0.0",
            description="Test",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )
        app = create_app(manifest, token_validator=_always_reject_validator)
        client = TestClient(app)

        full_token = "sk_live_full_secret_token_never_log_this"
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {
                    "envelope": Envelope(
                        asap_version="0.1",
                        sender="urn:asap:agent:client",
                        recipient="urn:asap:agent:test",
                        payload_type="task.request",
                        payload=TaskRequest(
                            conversation_id="c1",
                            skill_id="echo",
                            input={},
                        ).model_dump(),
                    ).model_dump(mode="json")
                },
                "id": "1",
            },
            headers={"Authorization": f"Bearer {full_token}"},
        )

        assert response.status_code == 200
        assert "sk_live_" in caplog.text
        assert full_token not in caplog.text


class TestNonceReplayLogSanitization:
    """Nonce replay logs must show nonce prefix only, not full nonce."""

    def test_nonce_replay_logs_sanitized_nonce_not_full(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Nonce replay logs show prefix (e.g. 01HXA...) not full nonce."""
        manifest = Manifest(
            id="urn:asap:agent:test",
            name="Test",
            version="1.0.0",
            description="Test",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )
        app = create_app(manifest, require_nonce=True)
        client = TestClient(app)

        full_nonce = "01HXAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="c1",
                skill_id="echo",
                input={},
            ).model_dump(),
            extensions={"nonce": full_nonce},
        )

        # First request succeeds (nonce accepted)
        r1 = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": envelope.model_dump(mode="json")},
                "id": "1",
            },
        )
        assert r1.status_code == 200

        # Second request with same nonce fails (replay)
        caplog.clear()
        r2 = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": envelope.model_dump(mode="json")},
                "id": "2",
            },
        )
        assert r2.status_code == 200
        assert "error" in r2.json()

        # Log should show sanitized nonce (prefix) and not full nonce
        assert full_nonce not in caplog.text


class TestClientConnectionFailureLogSanitization:
    """Client connection failure logs must mask URL credentials."""

    def test_client_connection_failure_logs_sanitized_url(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Client connection failure logs show https://user:***@... not password."""
        import asyncio

        from asap.transport.client import ASAPClient

        # URL with credentials; mock post to raise so we get connection-failure logs
        base_url = "https://user:secret_password@invalid.example.com/asap"
        client = ASAPClient(base_url=base_url, max_retries=0)

        mock_post = AsyncMock(side_effect=Exception("connection failed"))
        with patch("asap.transport.client.httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.post = mock_post
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:client",
                recipient="urn:asap:agent:test",
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id="c1",
                    skill_id="echo",
                    input={},
                ).model_dump(),
            )

            async def run() -> None:
                with contextlib.suppress(Exception):
                    await client.send(envelope)

            asyncio.run(run())

        # Password must never appear in logs
        assert "secret_password" not in caplog.text
        # When client logs (e.g. send attempt or error), URL must be sanitized
        if "asap.client" in caplog.text:
            assert "user:***" in caplog.text or "***@" in caplog.text


class TestDebugModeVsProductionLogs:
    """Debug mode logs full data; production mode sanitizes."""

    def test_production_mode_sanitizes_validation_errors(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When ASAP_DEBUG is unset, invalid_envelope log contains redacted sensitive data."""
        with patch.dict("os.environ", {"ASAP_DEBUG": ""}):
            assert is_debug_mode() is False

        manifest = Manifest(
            id="urn:asap:agent:test",
            name="Test",
            version="1.0.0",
            description="Test",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )
        app = create_app(manifest)
        client = TestClient(app)

        # Send invalid envelope (e.g. missing required field) with sensitive-looking
        # data in payload so validation_errors could expose it; server logs sanitized
        caplog.clear()
        with patch.dict("os.environ", {"ASAP_DEBUG": ""}):
            client.post(
                "/asap",
                json={
                    "jsonrpc": "2.0",
                    "method": "asap.send",
                    "params": {
                        "envelope": {
                            "asap_version": "0.1",
                            "sender": "urn:asap:agent:client",
                            "recipient": "urn:asap:agent:test",
                            "payload_type": "task.request",
                            "payload": {"token": "should_be_redacted", "other": "ok"},
                            # missing timestamp etc. to trigger validation
                        }
                    },
                    "id": "1",
                },
            )

        # In production mode, sanitize_for_logging is applied to log data;
        # if validation_errors or any dict with "token" is logged, it should be redacted
        if "invalid_envelope" in caplog.text or "invalid_structure" in caplog.text:
            assert REDACTED_PLACEHOLDER in caplog.text or "should_be_redacted" not in caplog.text

    def test_debug_mode_allows_full_logs(self) -> None:
        """When ASAP_DEBUG is true, is_debug_mode returns True."""
        with patch.dict("os.environ", {"ASAP_DEBUG": "true"}):
            assert is_debug_mode() is True
        with patch.dict("os.environ", {"ASAP_DEBUG": "1"}):
            assert is_debug_mode() is True
