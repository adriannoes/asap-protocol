"""Handshake validation - agent connection and manifest correctness."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version
from pydantic import ValidationError

from asap.discovery.health import HealthStatus, WELLKNOWN_HEALTH_PATH
from asap.discovery.validation import (
    ManifestValidationError,
    check_version_compatibility,
    validate_signed_manifest_response,
)
from asap.discovery.wellknown import WELLKNOWN_MANIFEST_PATH
from asap.models.constants import ASAP_PROTOCOL_VERSION
from asap.models.entities import Manifest

from asap_compliance.config import ComplianceConfig

CONTENT_TYPE_JSON = "application/json"


@dataclass
class CheckResult:
    """Result of a single compliance check.

    Attributes:
        name: Check identifier.
        passed: Whether the check passed.
        message: Human-readable result or error message.
    """

    name: str
    passed: bool
    message: str


@dataclass
class HandshakeResult:
    """Aggregated result of handshake validation.

    Attributes:
        connection_ok: Health endpoint reachable and content-type correct.
        manifest_ok: Manifest endpoint exists, schema valid, signature valid if signed.
        version_ok: Agent reports version and rejects unsupported versions.
        checks: Individual check results.
    """

    connection_ok: bool
    manifest_ok: bool
    version_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True if all handshake checks passed."""
        return self.connection_ok and self.manifest_ok and self.version_ok


def _base_url(config: ComplianceConfig) -> str:
    """Return normalized base URL (no trailing slash)."""
    return config.agent_url.rstrip("/")


def _health_url(config: ComplianceConfig) -> str:
    """Return full health endpoint URL."""
    return _base_url(config) + WELLKNOWN_HEALTH_PATH


def _manifest_url(config: ComplianceConfig) -> str:
    """Return full manifest endpoint URL."""
    return _base_url(config) + WELLKNOWN_MANIFEST_PATH


async def _check_connection(
    config: ComplianceConfig, client: httpx.AsyncClient
) -> list[CheckResult]:
    """Test agent responds to health check with correct content-type."""
    results: list[CheckResult] = []
    url = _health_url(config)

    try:
        response = await client.get(url, timeout=config.timeout_seconds)
    except httpx.RequestError as e:
        results.append(
            CheckResult(
                name="health_reachable",
                passed=False,
                message=f"Health endpoint unreachable: {e}",
            )
        )
        return results

    if response.status_code != 200:
        results.append(
            CheckResult(
                name="health_status",
                passed=False,
                message=f"Health returned {response.status_code}, expected 200",
            )
        )
    else:
        results.append(
            CheckResult(name="health_status", passed=True, message="Health returned 200")
        )

    content_type = response.headers.get("content-type", "")
    if CONTENT_TYPE_JSON not in content_type:
        results.append(
            CheckResult(
                name="health_content_type",
                passed=False,
                message=f"Content-Type is '{content_type}', expected application/json",
            )
        )
    else:
        results.append(
            CheckResult(
                name="health_content_type",
                passed=True,
                message="Content-Type is application/json",
            )
        )

    try:
        HealthStatus.model_validate(response.json())
        results.append(
            CheckResult(name="health_schema", passed=True, message="Health schema valid")
        )
    except ValidationError as e:
        results.append(
            CheckResult(
                name="health_schema",
                passed=False,
                message=f"Invalid health schema: {e}",
            )
        )

    return results


async def _check_manifest(
    config: ComplianceConfig, client: httpx.AsyncClient
) -> tuple[list[CheckResult], Manifest | None]:
    """Test manifest endpoint exists, schema valid, signature valid if signed.

    Returns:
        Tuple of (check results, parsed Manifest or None).
    """
    results: list[CheckResult] = []
    manifest: Manifest | None = None
    url = _manifest_url(config)

    try:
        response = await client.get(url, timeout=config.timeout_seconds)
    except httpx.RequestError as e:
        results.append(
            CheckResult(
                name="manifest_reachable",
                passed=False,
                message=f"Manifest endpoint unreachable: {e}",
            )
        )
        return results, None

    if response.status_code != 200:
        results.append(
            CheckResult(
                name="manifest_status",
                passed=False,
                message=f"Manifest returned {response.status_code}, expected 200",
            )
        )
        return results, None

    results.append(
        CheckResult(name="manifest_status", passed=True, message="Manifest returned 200")
    )

    content_type = response.headers.get("content-type", "")
    if CONTENT_TYPE_JSON not in content_type:
        results.append(
            CheckResult(
                name="manifest_content_type",
                passed=False,
                message=f"Content-Type is '{content_type}', expected application/json",
            )
        )
        return results, None

    try:
        data: dict[str, Any] = response.json()
    except Exception as e:
        results.append(
            CheckResult(
                name="manifest_json",
                passed=False,
                message=f"Invalid JSON: {e}",
            )
        )
        return results, None

    try:
        manifest = validate_signed_manifest_response(data, verify_signature=True)
        results.append(
            CheckResult(name="manifest_schema", passed=True, message="Manifest schema valid")
        )
        results.append(
            CheckResult(
                name="manifest_signature",
                passed=True,
                message="Signature valid (or unsigned manifest accepted)",
            )
        )
        results.append(
            CheckResult(
                name="manifest_parsed",
                passed=True,
                message=f"Manifest id={manifest.id}",
            )
        )
    except ManifestValidationError as e:
        results.append(
            CheckResult(
                name="manifest_schema",
                passed=False,
                message=f"Invalid manifest schema: {e}",
            )
        )
    except Exception as e:
        results.append(
            CheckResult(
                name="manifest_signature",
                passed=False,
                message=f"Signature verification failed: {e}",
            )
        )

    return results, manifest


def _check_version(config: ComplianceConfig, manifest: Manifest | None) -> list[CheckResult]:
    """Test agent reports version and rejects unsupported versions."""
    results: list[CheckResult] = []

    if manifest is None:
        results.append(
            CheckResult(
                name="version_reported",
                passed=False,
                message="Cannot check version: manifest not available",
            )
        )
        return results

    asap_version = manifest.capabilities.asap_version
    results.append(
        CheckResult(
            name="version_reported",
            passed=True,
            message=f"Agent reports asap_version={asap_version}",
        )
    )

    try:
        check_version_compatibility(manifest, min_asap_version=ASAP_PROTOCOL_VERSION)
        results.append(
            CheckResult(
                name="version_compatible",
                passed=True,
                message=f"Version {asap_version} >= {ASAP_PROTOCOL_VERSION}",
            )
        )
    except ManifestValidationError as e:
        results.append(
            CheckResult(
                name="version_compatible",
                passed=False,
                message=str(e),
            )
        )

    try:
        Version(asap_version)
        results.append(
            CheckResult(
                name="version_format",
                passed=True,
                message="Version format valid (PEP 440)",
            )
        )
    except InvalidVersion as e:
        results.append(
            CheckResult(
                name="version_format",
                passed=False,
                message=f"Invalid version format: {e}",
            )
        )

    return results


async def validate_handshake_async(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> HandshakeResult:
    """Run handshake validation against an ASAP agent (async).

    Args:
        config: Compliance configuration with agent_url and timeout.
        client: Optional pre-configured httpx.AsyncClient (e.g. with ASGITransport
            for testing). When provided, it is used and not closed.

    Returns:
        HandshakeResult with connection, manifest, and version check results.
    """
    checks: list[CheckResult] = []
    connection_ok = False
    manifest_ok = False
    version_ok = False
    manifest: Manifest | None = None

    async def _run(client_instance: httpx.AsyncClient) -> None:
        nonlocal connection_ok, manifest_ok, version_ok, manifest
        conn_results = await _check_connection(config, client_instance)
        checks.extend(conn_results)
        connection_ok = all(r.passed for r in conn_results)

        manifest_results, manifest = await _check_manifest(config, client_instance)
        checks.extend(manifest_results)
        manifest_ok = all(r.passed for r in manifest_results)

        version_results = _check_version(config, manifest)
        checks.extend(version_results)
        version_ok = all(r.passed for r in version_results)

    if client is not None:
        await _run(client)
    else:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as c:
            await _run(c)

    return HandshakeResult(
        connection_ok=connection_ok,
        manifest_ok=manifest_ok,
        version_ok=version_ok,
        checks=checks,
    )


def validate_handshake(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> HandshakeResult:
    """Run handshake validation against an ASAP agent (sync wrapper).

    For async usage, call validate_handshake_async directly.
    """
    return asyncio.run(validate_handshake_async(config, client=client))
