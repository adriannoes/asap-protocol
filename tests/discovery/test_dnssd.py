"""Tests for DNS-SD / mDNS discovery (requires zeroconf, dns-sd extra).

Run with: uv run pytest tests/discovery/test_dnssd.py -v
Install zeroconf: uv sync --extra dns-sd
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("zeroconf")

from asap.discovery.dnssd import (
    ASAP_SERVICE_TYPE,
    AgentInfo,
    DNSSDAdvertiser,
    DNSSDDiscovery,
    TXT_KEY_CAPABILITIES,
    TXT_KEY_MANIFEST_URL,
    TXT_KEY_VERSION,
)
from asap.models.entities import Manifest


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_agent_info_creation(self) -> None:
        """AgentInfo accepts valid fields and serializes."""
        info = AgentInfo(
            name="TestAgent",
            version="1.0.0",
            capabilities="search,summarize",
            manifest_url="https://localhost:8000/.well-known/asap/manifest.json",
            host="192.168.1.1",
            port=8000,
        )
        assert info.name == "TestAgent"
        assert info.version == "1.0.0"
        assert info.capabilities == "search,summarize"
        assert info.manifest_url.endswith("manifest.json")
        assert info.host == "192.168.1.1"
        assert info.port == 8000

    def test_agent_info_model_dump(self) -> None:
        """AgentInfo.model_dump() returns JSON-serializable dict."""
        info = AgentInfo(
            name="A",
            version="1",
            capabilities="x",
            manifest_url="https://a/manifest.json",
            host="127.0.0.1",
            port=80,
        )
        d = info.model_dump()
        assert isinstance(d, dict)
        assert d["name"] == "A"
        assert d["port"] == 80


class TestDNSSDAdvertiser:
    """Tests for DNSSDAdvertiser service registration."""

    def test_start_registers_service(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """start() creates Zeroconf and registers ServiceInfo."""
        mock_zc = MagicMock()
        mock_zc_class = MagicMock(return_value=mock_zc)
        monkeypatch.setattr(
            "asap.discovery.dnssd.Zeroconf",
            mock_zc_class,
        )
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/.well-known/asap/manifest.json",
            8000,
            host="127.0.0.1",
        )
        adv.start()
        mock_zc.register_service.assert_called_once()
        call_args = mock_zc.register_service.call_args
        service_info = call_args[0][0]
        assert service_info.type == ASAP_SERVICE_TYPE
        assert service_info.port == 8000
        props = service_info.properties or {}

        # zeroconf may use bytes or str keys
        def get_prop(key: str) -> str:
            for k, v in props.items():
                key_match = (k == key) if isinstance(k, str) else (k.decode() == key)
                if key_match and v is not None:
                    return v.decode() if isinstance(v, bytes) else str(v)
            return ""

        assert get_prop(TXT_KEY_VERSION) == "1.0.0"
        assert "echo" in get_prop(TXT_KEY_CAPABILITIES)  # sample_manifest has echo skill
        assert get_prop(TXT_KEY_MANIFEST_URL).startswith("https://")

    def test_start_idempotent(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """start() called twice does not register twice."""
        mock_zc = MagicMock()
        monkeypatch.setattr("asap.discovery.dnssd.Zeroconf", MagicMock(return_value=mock_zc))
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/manifest.json",
            8000,
            host="127.0.0.1",
        )
        adv.start()
        adv.start()
        mock_zc.register_service.assert_called_once()

    def test_stop_unregisters_and_closes(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stop() unregisters service and closes Zeroconf."""
        mock_zc = MagicMock()
        monkeypatch.setattr("asap.discovery.dnssd.Zeroconf", MagicMock(return_value=mock_zc))
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/manifest.json",
            8000,
            host="127.0.0.1",
        )
        adv.start()
        captured_info = mock_zc.register_service.call_args[0][0]
        adv.stop()
        mock_zc.unregister_service.assert_called_once_with(captured_info)
        mock_zc.close.assert_called_once()

    def test_stop_idempotent(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stop() called twice or before start does not raise."""
        mock_zc = MagicMock()
        monkeypatch.setattr("asap.discovery.dnssd.Zeroconf", MagicMock(return_value=mock_zc))
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/manifest.json",
            8000,
            host="127.0.0.1",
        )
        adv.stop()
        adv.start()
        adv.stop()
        adv.stop()
        mock_zc.unregister_service.assert_called_once()


class TestDNSSDDiscovery:
    """Tests for DNSSDDiscovery service browser."""

    @pytest.mark.asyncio
    async def test_browse_returns_agents_when_handler_fired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """browse() returns AgentInfo list when handler receives Added events."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            b"version": b"1.0.0",
            b"capabilities": b"search,summarize",
            b"manifest_url": b"https://localhost:8000/.well-known/asap/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = ["192.168.1.1"]
        mock_info.port = 8000
        mock_info.server = "agent.local."
        mock_zc.get_service_info.return_value = mock_info

        handlers_captured: list = []
        original_browser = None

        def mock_service_browser(zc: object, types: list[str], handlers: list) -> MagicMock:
            nonlocal handlers_captured, original_browser
            handlers_captured = handlers
            original_browser = MagicMock()
            original_browser.cancel = MagicMock()
            return original_browser

        def mock_sleep(seconds: float) -> None:
            if handlers_captured:
                from zeroconf import ServiceStateChange

                for h in handlers_captured:
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name="TestAgent._asap._tcp.local.",
                        state_change=ServiceStateChange.Added,
                    )

        with (
            patch("asap.discovery.dnssd.Zeroconf", return_value=mock_zc),
            patch("asap.discovery.dnssd.ServiceBrowser", side_effect=mock_service_browser),
            patch("asap.discovery.dnssd.time.sleep", side_effect=mock_sleep),
        ):
            discovery = DNSSDDiscovery()
            agents = await discovery.browse(wait_seconds=0.1)
        assert len(agents) == 1
        assert agents[0].name == "TestAgent"
        assert agents[0].version == "1.0.0"
        assert agents[0].capabilities == "search,summarize"
        assert "manifest.json" in agents[0].manifest_url
        assert agents[0].host == "192.168.1.1"
        assert agents[0].port == 8000

    @pytest.mark.asyncio
    async def test_browse_invokes_on_service_added(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_service_added callback is invoked when agent discovered."""
        added: list[AgentInfo] = []
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            b"version": b"2.0.0",
            b"capabilities": b"x",
            b"manifest_url": b"https://a/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = ["10.0.0.1"]
        mock_info.port = 9000
        mock_info.server = "srv.local."
        mock_zc.get_service_info.return_value = mock_info
        handlers_captured: list = []

        def mock_service_browser(zc: object, types: list[str], handlers: list) -> MagicMock:
            nonlocal handlers_captured
            handlers_captured = handlers
            return MagicMock(cancel=MagicMock())

        def mock_sleep(seconds: float) -> None:
            if handlers_captured:
                from zeroconf import ServiceStateChange

                for h in handlers_captured:
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name="CallbackAgent._asap._tcp.local.",
                        state_change=ServiceStateChange.Added,
                    )

        with (
            patch("asap.discovery.dnssd.Zeroconf", return_value=mock_zc),
            patch("asap.discovery.dnssd.ServiceBrowser", side_effect=mock_service_browser),
            patch("asap.discovery.dnssd.time.sleep", side_effect=mock_sleep),
        ):
            discovery = DNSSDDiscovery(on_service_added=lambda a: added.append(a))
            await discovery.browse(wait_seconds=0.05)
        assert len(added) == 1
        assert added[0].name == "CallbackAgent"
        assert added[0].version == "2.0.0"

    @pytest.mark.asyncio
    async def test_browse_skips_services_without_manifest_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Services without manifest_url TXT are not included."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            b"version": b"1.0.0",
            b"capabilities": b"",
            b"manifest_url": b"",
        }
        mock_info.parsed_scoped_addresses.return_value = ["127.0.0.1"]
        mock_info.port = 80
        mock_info.server = "local."
        mock_zc.get_service_info.return_value = mock_info
        handlers_captured: list = []

        def mock_service_browser(zc: object, types: list[str], handlers: list) -> MagicMock:
            nonlocal handlers_captured
            handlers_captured = handlers
            return MagicMock(cancel=MagicMock())

        def mock_sleep(seconds: float) -> None:
            if handlers_captured:
                from zeroconf import ServiceStateChange

                for h in handlers_captured:
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name="NoManifest._asap._tcp.local.",
                        state_change=ServiceStateChange.Added,
                    )

        with (
            patch("asap.discovery.dnssd.Zeroconf", return_value=mock_zc),
            patch("asap.discovery.dnssd.ServiceBrowser", side_effect=mock_service_browser),
            patch("asap.discovery.dnssd.time.sleep", side_effect=mock_sleep),
        ):
            discovery = DNSSDDiscovery()
            agents = await discovery.browse(wait_seconds=0.05)
        assert len(agents) == 0
