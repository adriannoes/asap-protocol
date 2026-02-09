"""Tests for DNS-SD / mDNS discovery (requires zeroconf, dns-sd extra).

Run with: uv run pytest tests/discovery/test_dnssd.py -v
Install zeroconf: uv sync --extra dns-sd
"""

from __future__ import annotations

import socket
from typing import Any
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
    _decode_txt_value,
    _get_prop,
    _sanitize_instance_name,
    _service_info_to_agent_info,
    _skill_ids_from_manifest,
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

    def test_start_resolves_host_when_none(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """start() resolves host via _get_default_host when host is None."""
        mock_zc = MagicMock()
        monkeypatch.setattr("asap.discovery.dnssd.Zeroconf", MagicMock(return_value=mock_zc))
        monkeypatch.setattr("asap.discovery.dnssd.socket.gethostbyname", lambda _: "10.0.0.42")
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/manifest.json",
            8000,
            # host intentionally omitted (None)
        )
        adv.start()
        mock_zc.register_service.assert_called_once()
        service_info = mock_zc.register_service.call_args[0][0]
        assert service_info.port == 8000

    def test_get_default_host_oserror_fallback(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_get_default_host returns 127.0.0.1 when socket raises OSError."""
        monkeypatch.setattr(
            "asap.discovery.dnssd.socket.gethostbyname",
            MagicMock(side_effect=OSError("DNS failure")),
        )
        mock_zc = MagicMock()
        monkeypatch.setattr("asap.discovery.dnssd.Zeroconf", MagicMock(return_value=mock_zc))
        adv = DNSSDAdvertiser(
            sample_manifest,
            "https://localhost:8000/manifest.json",
            8000,
            # host intentionally omitted to trigger _get_default_host
        )
        adv.start()
        mock_zc.register_service.assert_called_once()
        service_info = mock_zc.register_service.call_args[0][0]
        # Verify fallback address was used (127.0.0.1)
        assert socket.inet_aton("127.0.0.1") in service_info.addresses


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_sanitize_instance_name_replaces_invalid_chars(self) -> None:
        """_sanitize_instance_name replaces spaces and special chars with hyphens."""
        assert _sanitize_instance_name("My Agent @v1") == "My-Agent--v1"

    def test_sanitize_instance_name_truncates_at_63(self) -> None:
        """_sanitize_instance_name truncates long names to 63 chars."""
        long_name = "a" * 100
        assert len(_sanitize_instance_name(long_name)) == 63

    def test_sanitize_instance_name_fallback(self) -> None:
        """_sanitize_instance_name returns 'asap-agent' for all-invalid input."""
        assert _sanitize_instance_name("---") == "asap-agent"

    def test_skill_ids_from_manifest(self, sample_manifest: Manifest) -> None:
        """_skill_ids_from_manifest extracts comma-separated skill IDs."""
        result = _skill_ids_from_manifest(sample_manifest)
        assert "echo" in result

    def test_decode_txt_value_bytes(self) -> None:
        """_decode_txt_value decodes bytes to string."""
        assert _decode_txt_value(b"hello") == "hello"

    def test_decode_txt_value_string(self) -> None:
        """_decode_txt_value passes through string values."""
        assert _decode_txt_value("already-str") == "already-str"

    def test_get_prop_with_string_keys(self) -> None:
        """_get_prop retrieves value from dict with string keys."""
        props: dict[str, str | None] = {
            "version": "2.0.0",
            "capabilities": "search",
            "manifest_url": "https://a/manifest.json",
        }
        assert _get_prop(props, "version") == "2.0.0"
        assert _get_prop(props, "capabilities") == "search"

    def test_get_prop_with_bytes_keys(self) -> None:
        """_get_prop retrieves value from dict with bytes keys."""
        props: dict[bytes, bytes | None] = {
            b"version": b"1.0.0",
            b"capabilities": b"x",
        }
        assert _get_prop(props, "version") == "1.0.0"

    def test_get_prop_skips_none_values(self) -> None:
        """_get_prop skips keys with None values and returns empty string."""
        props: dict[str, str | None] = {
            "version": None,
            "capabilities": "x",
        }
        assert _get_prop(props, "version") == ""
        assert _get_prop(props, "capabilities") == "x"

    def test_get_prop_returns_empty_for_missing_key(self) -> None:
        """_get_prop returns empty string when key is not found."""
        props: dict[str, str | None] = {"version": "1.0.0"}
        assert _get_prop(props, "missing") == ""

    def test_service_info_to_agent_info_returns_none_for_no_info(self) -> None:
        """_service_info_to_agent_info returns None when get_service_info is None."""
        mock_zc = MagicMock()
        mock_zc.get_service_info.return_value = None
        result = _service_info_to_agent_info(mock_zc, ASAP_SERVICE_TYPE, "Test._asap._tcp.local.")
        assert result is None

    def test_service_info_to_agent_info_returns_none_without_manifest_url(self) -> None:
        """_service_info_to_agent_info returns None when manifest_url is empty."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {b"version": b"1.0.0", b"capabilities": b"x", b"manifest_url": b""}
        mock_zc.get_service_info.return_value = mock_info
        result = _service_info_to_agent_info(mock_zc, ASAP_SERVICE_TYPE, "Test._asap._tcp.local.")
        assert result is None

    def test_service_info_to_agent_info_uses_server_fallback(self) -> None:
        """_service_info_to_agent_info falls back to info.server when no addresses."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            "version": "1.0.0",
            "capabilities": "x",
            "manifest_url": "https://a/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = []
        mock_info.port = 9000
        mock_info.server = "agent.local."
        mock_zc.get_service_info.return_value = mock_info
        result = _service_info_to_agent_info(
            mock_zc, ASAP_SERVICE_TYPE, "TestAgent._asap._tcp.local."
        )
        assert result is not None
        assert result.host == "agent.local."
        assert result.name == "TestAgent"
        assert result.port == 9000

    def test_service_info_to_agent_info_with_string_properties(self) -> None:
        """_service_info_to_agent_info handles string keys in TXT properties."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            "version": "2.0.0",
            "capabilities": "search,code",
            "manifest_url": "https://example.com/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = ["192.168.1.5"]
        mock_info.port = 8080
        mock_info.server = "test.local."
        mock_zc.get_service_info.return_value = mock_info
        result = _service_info_to_agent_info(
            mock_zc, ASAP_SERVICE_TYPE, "MyAgent._asap._tcp.local."
        )
        assert result is not None
        assert result.version == "2.0.0"
        assert result.capabilities == "search,code"
        assert result.host == "192.168.1.5"


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

        handlers_captured: list[Any] = []
        original_browser = None

        def mock_service_browser(zc: object, types: list[str], handlers: list[Any]) -> MagicMock:
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
        handlers_captured: list[Any] = []

        def mock_service_browser(zc: object, types: list[str], handlers: list[Any]) -> MagicMock:
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
        handlers_captured: list[Any] = []

        def mock_service_browser(zc: object, types: list[str], handlers: list[Any]) -> MagicMock:
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

    @pytest.mark.asyncio
    async def test_browse_invokes_on_service_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_service_removed callback is invoked when agent is removed after being added."""
        added: list[AgentInfo] = []
        removed: list[AgentInfo] = []
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            b"version": b"1.0.0",
            b"capabilities": b"echo",
            b"manifest_url": b"https://a/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = ["10.0.0.1"]
        mock_info.port = 8000
        mock_info.server = "agent.local."
        mock_zc.get_service_info.return_value = mock_info
        handlers_captured: list[Any] = []
        service_name = "RemovedAgent._asap._tcp.local."

        def mock_service_browser(zc: object, types: list[str], handlers: list[Any]) -> MagicMock:
            nonlocal handlers_captured
            handlers_captured = handlers
            return MagicMock(cancel=MagicMock())

        def mock_sleep(seconds: float) -> None:
            if handlers_captured:
                from zeroconf import ServiceStateChange

                for h in handlers_captured:
                    # First add the service
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name=service_name,
                        state_change=ServiceStateChange.Added,
                    )
                    # Then remove it
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name=service_name,
                        state_change=ServiceStateChange.Removed,
                    )

        with (
            patch("asap.discovery.dnssd.Zeroconf", return_value=mock_zc),
            patch("asap.discovery.dnssd.ServiceBrowser", side_effect=mock_service_browser),
            patch("asap.discovery.dnssd.time.sleep", side_effect=mock_sleep),
        ):
            discovery = DNSSDDiscovery(
                on_service_added=lambda a: added.append(a),
                on_service_removed=lambda a: removed.append(a),
            )
            agents = await discovery.browse(wait_seconds=0.05)
        # Agent was added then removed
        assert len(added) == 1
        assert len(removed) == 1
        assert removed[0].name == "RemovedAgent"
        # Still in collected list since it was added
        assert len(agents) == 1

    @pytest.mark.asyncio
    async def test_browse_removed_without_callback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removed event without on_service_removed callback does not raise."""
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.properties = {
            b"version": b"1.0.0",
            b"capabilities": b"x",
            b"manifest_url": b"https://a/manifest.json",
        }
        mock_info.parsed_scoped_addresses.return_value = ["10.0.0.1"]
        mock_info.port = 8000
        mock_info.server = "agent.local."
        mock_zc.get_service_info.return_value = mock_info
        handlers_captured: list[Any] = []

        def mock_service_browser(zc: object, types: list[str], handlers: list[Any]) -> MagicMock:
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
                        name="NoCallback._asap._tcp.local.",
                        state_change=ServiceStateChange.Added,
                    )
                    h(
                        zeroconf=mock_zc,
                        service_type=ASAP_SERVICE_TYPE,
                        name="NoCallback._asap._tcp.local.",
                        state_change=ServiceStateChange.Removed,
                    )

        with (
            patch("asap.discovery.dnssd.Zeroconf", return_value=mock_zc),
            patch("asap.discovery.dnssd.ServiceBrowser", side_effect=mock_service_browser),
            patch("asap.discovery.dnssd.time.sleep", side_effect=mock_sleep),
        ):
            # No on_service_removed callback
            discovery = DNSSDDiscovery()
            agents = await discovery.browse(wait_seconds=0.05)
        assert len(agents) == 1
