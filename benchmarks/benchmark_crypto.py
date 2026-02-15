"""Benchmarks for v1.2.0 crypto and compliance features.

Measures performance of:
- Ed25519 signing and verification
- JCS canonicalization overhead
- Compliance harness execution time (handshake)

Run with: uv run pytest benchmarks/benchmark_crypto.py --benchmark-only -v
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from asap.crypto.keys import generate_keypair
from asap.crypto.signing import canonicalize, sign_manifest, verify_manifest
from asap.models.entities import Capability, Endpoint, Manifest, Skill


@pytest.fixture
def benchmark_manifest() -> Manifest:
    """Sample manifest for crypto benchmarks."""
    return Manifest(
        id="urn:asap:agent:benchmark-crypto",
        name="Benchmark Crypto Agent",
        version="1.0.0",
        description="Agent for crypto benchmarks",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )


@pytest.fixture
def benchmark_keypair() -> tuple[Any, Any]:
    """Pre-generated keypair for benchmarks (avoids keygen in hot path)."""
    return generate_keypair()


class TestEd25519Signing:
    """Benchmarks for Ed25519 manifest signing."""

    def test_sign_manifest(
        self,
        benchmark: Any,
        benchmark_manifest: Manifest,
        benchmark_keypair: tuple[Any, Any],
    ) -> None:
        """Benchmark sign_manifest (canonicalize + Ed25519 sign)."""
        private_key, _ = benchmark_keypair

        def do_sign() -> Any:
            return sign_manifest(benchmark_manifest, private_key)

        result = benchmark(do_sign)
        assert result.manifest.id == benchmark_manifest.id
        assert result.signature.alg == "ed25519"


class TestEd25519Verification:
    """Benchmarks for Ed25519 signature verification."""

    def test_verify_manifest(
        self,
        benchmark: Any,
        benchmark_manifest: Manifest,
        benchmark_keypair: tuple[Any, Any],
    ) -> None:
        """Benchmark verify_manifest (canonicalize + Ed25519 verify)."""
        private_key, _ = benchmark_keypair
        signed = sign_manifest(benchmark_manifest, private_key)

        def do_verify() -> bool:
            return verify_manifest(signed)

        result = benchmark(do_verify)
        assert result is True


class TestJcsCanonicalization:
    """Benchmarks for JCS canonicalization overhead."""

    def test_canonicalize_manifest(
        self,
        benchmark: Any,
        benchmark_manifest: Manifest,
    ) -> None:
        """Benchmark JCS canonicalization of manifest (excludes signature)."""
        result = benchmark(canonicalize, benchmark_manifest)
        assert isinstance(result, bytes)
        assert result.startswith(b"{")


class TestComplianceHarnessExecution:
    """Benchmarks for compliance harness execution time."""

    def test_handshake_validation_execution_time(
        self,
        benchmark: Any,
        benchmark_app: Any,
    ) -> None:
        """Benchmark full handshake validation against in-process agent."""
        from asap_compliance.config import ComplianceConfig
        from asap_compliance.validators.handshake import validate_handshake_async

        transport = httpx.ASGITransport(app=benchmark_app.app)
        config = ComplianceConfig(
            agent_url="http://testserver",
            timeout_seconds=10.0,
        )

        async def run_handshake() -> Any:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                return await validate_handshake_async(config, client=client)

        def sync_wrapper() -> Any:
            return asyncio.run(run_handshake())

        result = benchmark(sync_wrapper)
        assert result.passed
