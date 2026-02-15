"""DNS-SD / mDNS support for local network agent discovery.

Enables agents to advertise themselves via mDNS (Bonjour) for LAN discovery
without a registry. Requires the dns-sd optional extra: uv sync --extra dns-sd.

**Network scope:** mDNS advertisement typically broadcasts on the local subnet only.
Services are discoverable by other agents on the same LAN, not across the internet.
"""

from __future__ import annotations

import asyncio
import re
import socket
import time
from collections.abc import Callable

from pydantic import Field

from asap.models.base import ASAPBaseModel
from asap.models.entities import Manifest

try:
    from zeroconf import (
        IPVersion,
        ServiceBrowser,
        ServiceInfo,
        ServiceStateChange,
        Zeroconf,
    )
except ImportError as exc:
    raise ImportError(
        "zeroconf is required for DNS-SD. Install with: uv sync --extra dns-sd"
    ) from exc

ASAP_SERVICE_TYPE = "_asap._tcp.local."
"""Standard DNS-SD service type for ASAP agents (RFC 6763)."""

TXT_KEY_VERSION = "version"
TXT_KEY_CAPABILITIES = "capabilities"
TXT_KEY_MANIFEST_URL = "manifest_url"

# Max length per TXT record value (RFC 6763: 0-255 bytes)
_TXT_VALUE_MAX_LEN = 255


def _sanitize_instance_name(name: str) -> str:
    """Sanitize string for use as DNS-SD instance name.

    Replaces spaces and invalid chars with hyphens, truncates if needed.
    """
    sanitized = re.sub(r"[^\w\-.]", "-", name)
    return sanitized.strip("-")[:63] or "asap-agent"


def _skill_ids_from_manifest(manifest: Manifest) -> str:
    """Extract comma-separated skill IDs from manifest capabilities."""
    skills = manifest.capabilities.skills
    ids = [s.id for s in skills]
    return ",".join(ids)[:_TXT_VALUE_MAX_LEN]


class DNSSDAdvertiser:
    """Advertise an ASAP agent via mDNS/DNS-SD for local network discovery.

    Registers the service type _asap._tcp.local. with TXT records containing
    version, capabilities, and manifest_url. Use start() to register and
    stop() to unregister.

    **Network scope:** Advertisement is broadcast on the local subnet; other
    agents on the same LAN can discover this service. Not visible across the internet.

    Example:
        >>> from asap.models.entities import Manifest, Capability, Endpoint
        >>> manifest = Manifest(
        ...     id="urn:asap:agent:demo",
        ...     name="Demo Agent",
        ...     version="1.0.0",
        ...     description="Demo",
        ...     capabilities=Capability(),
        ...     endpoints=Endpoint(asap="https://localhost:8000/asap"),
        ... )
        >>> adv = DNSSDAdvertiser(manifest, "https://localhost:8000/.well-known/asap/manifest.json", 8000)
        >>> adv.start()
        >>> # ... agent runs ...
        >>> adv.stop()
    """

    def __init__(
        self,
        manifest: Manifest,
        manifest_url: str,
        port: int,
        *,
        host: str | None = None,
    ) -> None:
        self._manifest = manifest
        self._manifest_url = manifest_url
        self._port = port
        self._host: str | None = host
        self._zeroconf: Zeroconf | None = None
        self._service_info: ServiceInfo | None = None

    def _get_default_host(self) -> str:
        """Return the primary local IP for advertisement. May block on DNS."""
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"

    def _build_properties(self) -> dict[str, str]:
        """Build TXT record properties for DNS-SD."""
        version = str(self._manifest.version)[:_TXT_VALUE_MAX_LEN]
        capabilities = _skill_ids_from_manifest(self._manifest)
        manifest_url = self._manifest_url[:_TXT_VALUE_MAX_LEN]
        return {
            TXT_KEY_VERSION: version,
            TXT_KEY_CAPABILITIES: capabilities,
            TXT_KEY_MANIFEST_URL: manifest_url,
        }

    def _create_service_info(self) -> ServiceInfo:
        """Create the ServiceInfo for registration."""
        assert self._host is not None
        host = self._host
        instance_name = _sanitize_instance_name(self._manifest.name)
        qualified_name = f"{instance_name}.{ASAP_SERVICE_TYPE}"
        server_name = socket.getfqdn()
        addresses = [socket.inet_aton(host)]

        return ServiceInfo(
            ASAP_SERVICE_TYPE,
            qualified_name,
            addresses=addresses,
            port=self._port,
            properties=self._build_properties(),
            server=server_name,
        )

    def start(self) -> None:
        """Register the ASAP service via mDNS. Idempotent (no-op if already started).

        If host was not set at construction, resolves it here (may block briefly).
        """
        if self._zeroconf is not None:
            return
        if self._host is None:
            self._host = self._get_default_host()
        self._service_info = self._create_service_info()
        self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self._zeroconf.register_service(self._service_info)

    def stop(self) -> None:
        """Unregister the service and release resources. Idempotent (no-op if already stopped)."""
        if self._zeroconf is None or self._service_info is None:
            return
        self._zeroconf.unregister_service(self._service_info)
        self._zeroconf.close()
        self._zeroconf = None
        self._service_info = None


class AgentInfo(ASAPBaseModel):
    """Discovered agent metadata from DNS-SD TXT records.

    Populated when browsing for _asap._tcp.local. services. Use manifest_url
    to fetch the full Manifest via ASAPClient.discover().

    Attributes:
        name: DNS-SD instance name (sanitized agent name).
        version: Agent version from TXT record.
        capabilities: Comma-separated skill IDs from TXT record.
        manifest_url: Full URL to the agent's manifest (well-known URI).
        host: Resolved host (IP or hostname) for the service.
        port: TCP port the ASAP server listens on.
    """

    name: str = Field(..., description="DNS-SD instance name")
    version: str = Field(..., description="Agent version")
    capabilities: str = Field(..., description="Comma-separated skill IDs")
    manifest_url: str = Field(..., description="URL to manifest")
    host: str = Field(..., description="Resolved host for the service")
    port: int = Field(..., description="TCP port")


def _decode_txt_value(val: bytes | str) -> str:
    """Decode TXT record value (zeroconf may return bytes)."""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


def _get_prop(props: dict[bytes, bytes | None] | dict[str, str | None], key: str) -> str:
    """Get TXT property value (zeroconf may use bytes or str keys)."""
    for k, v in props.items():
        if v is None:
            continue
        if (isinstance(k, str) and k == key) or (isinstance(k, bytes) and k.decode() == key):
            return _decode_txt_value(v)
    return ""


def _service_info_to_agent_info(zc: Zeroconf, service_type: str, name: str) -> AgentInfo | None:
    """Parse zeroconf ServiceInfo into AgentInfo. Returns None if info unavailable."""
    info = zc.get_service_info(service_type, name)
    if info is None:
        return None
    props = info.properties or {}
    version = _get_prop(props, TXT_KEY_VERSION)
    capabilities = _get_prop(props, TXT_KEY_CAPABILITIES)
    manifest_url = _get_prop(props, TXT_KEY_MANIFEST_URL)
    if not manifest_url:
        return None
    addresses = info.parsed_scoped_addresses()
    host = addresses[0] if addresses else str(info.server or "localhost")
    port = int(info.port) if info.port else 0
    # Instance name is the part before ._asap._tcp.local.
    instance_name = name.replace(f".{ASAP_SERVICE_TYPE}", "") if ASAP_SERVICE_TYPE in name else name
    return AgentInfo(
        name=instance_name,
        version=version,
        capabilities=capabilities,
        manifest_url=manifest_url,
        host=host,
        port=port,
    )


ServiceAddedCallback = Callable[[AgentInfo], None]
ServiceRemovedCallback = Callable[[AgentInfo], None]


class DNSSDDiscovery:
    """Browse for ASAP agents advertised via mDNS/DNS-SD.

    Discovers _asap._tcp.local. services. Use browse() for a one-shot discovery,
    or pass on_service_added/on_service_removed callbacks for ongoing updates.

    Example:
        >>> discovery = DNSSDDiscovery()
        >>> agents = await discovery.browse(timeout=3.0)
        >>> for a in agents:
        ...     print(a.name, a.manifest_url)
    """

    def __init__(
        self,
        *,
        on_service_added: ServiceAddedCallback | None = None,
        on_service_removed: ServiceRemovedCallback | None = None,
    ) -> None:
        self._on_added = on_service_added
        self._on_removed = on_service_removed

    def _run_browse(self, timeout: float) -> list[AgentInfo]:
        """Run synchronous browse and return discovered agents."""
        collected: list[AgentInfo] = []
        agents_by_name: dict[str, AgentInfo] = {}

        def handler(
            *,
            zeroconf: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
        ) -> None:
            if state_change is ServiceStateChange.Added:
                agent = _service_info_to_agent_info(zeroconf, service_type, name)
                if agent and agent.manifest_url:
                    collected.append(agent)
                    agents_by_name[name] = agent
                    if self._on_added:
                        self._on_added(agent)
            elif state_change is ServiceStateChange.Removed:
                agent = agents_by_name.pop(name, None)
                if agent and self._on_removed:
                    self._on_removed(agent)

        zc = Zeroconf(ip_version=IPVersion.V4Only)
        browser = ServiceBrowser(zc, [ASAP_SERVICE_TYPE], handlers=[handler])
        try:
            time.sleep(timeout)
        finally:
            browser.cancel()
            zc.close()
        return collected

    async def browse(self, wait_seconds: float = 2.0) -> list[AgentInfo]:
        async with asyncio.timeout(wait_seconds + 1.0):
            return await asyncio.to_thread(self._run_browse, wait_seconds)
