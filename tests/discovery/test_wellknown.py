"""Tests for well-known URI handler (RFC 8615) and manifest discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from asap.discovery import wellknown
from asap.models.entities import Manifest
from asap.transport.server import create_app

if TYPE_CHECKING:
    from fastapi import FastAPI


@pytest.fixture
def app(sample_manifest: Manifest) -> "FastAPI":
    """Create FastAPI app with sample manifest (high rate limit for tests)."""
    return create_app(sample_manifest, rate_limit="999999/minute")


@pytest.fixture
def client(app: "FastAPI") -> TestClient:
    """Create test client for the app."""
    return TestClient(app)


class TestGetManifestJson:
    """Tests for get_manifest_json()."""

    def test_returns_dict_equal_to_model_dump(
        self, sample_manifest: Manifest
    ) -> None:
        """Endpoint payload equals manifest.model_dump()."""
        result = wellknown.get_manifest_json(sample_manifest)
        assert result == sample_manifest.model_dump()
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == sample_manifest.id

    def test_returns_json_serializable(self, sample_manifest: Manifest) -> None:
        """Returned dict is JSON-serializable (no custom types)."""
        import json

        result = wellknown.get_manifest_json(sample_manifest)
        # Should not raise
        json.dumps(result)


class TestComputeManifestEtag:
    """Tests for compute_manifest_etag()."""

    def test_returns_64_char_hex_string(self, sample_manifest: Manifest) -> None:
        """ETag is SHA-256 hex (64 chars)."""
        etag = wellknown.compute_manifest_etag(sample_manifest)
        assert len(etag) == 64
        assert all(c in "0123456789abcdef" for c in etag)

    def test_deterministic_same_manifest(self, sample_manifest: Manifest) -> None:
        """Same manifest always yields same ETag."""
        assert wellknown.compute_manifest_etag(
            sample_manifest
        ) == wellknown.compute_manifest_etag(sample_manifest)

    def test_different_manifest_different_etag(
        self, sample_manifest: Manifest
    ) -> None:
        """Different manifest yields different ETag."""
        other = Manifest(
            id="urn:asap:agent:other",
            name="Other",
            version="1.0.0",
            description="Other agent",
            capabilities=sample_manifest.capabilities,
            endpoints=sample_manifest.endpoints,
        )
        assert wellknown.compute_manifest_etag(
            sample_manifest
        ) != wellknown.compute_manifest_etag(other)


class TestWellKnownEndpointViaApp:
    """Tests for GET /.well-known/asap/manifest.json via create_app."""

    def test_returns_valid_manifest_json(
        self, client: TestClient, sample_manifest: Manifest
    ) -> None:
        """Endpoint returns valid manifest JSON."""
        response = client.get(wellknown.WELLKNOWN_MANIFEST_PATH)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_manifest.id
        assert data["name"] == sample_manifest.name
        assert "capabilities" in data
        assert "endpoints" in data

    def test_content_type_is_application_json(self, client: TestClient) -> None:
        """Content-Type is application/json."""
        response = client.get(wellknown.WELLKNOWN_MANIFEST_PATH)
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_cache_headers_present_and_correct(self, client: TestClient) -> None:
        """Cache-Control and ETag headers are present and valid."""
        response = client.get(wellknown.WELLKNOWN_MANIFEST_PATH)
        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "public" in response.headers["cache-control"]
        assert "max-age=300" in response.headers["cache-control"]
        assert "etag" in response.headers
        etag = response.headers["etag"]
        assert etag.startswith('"') and etag.endswith('"')

    def test_etag_conditional_returns_304_when_matches(
        self, client: TestClient
    ) -> None:
        """If-None-Match with current ETag returns 304 Not Modified."""
        first = client.get(wellknown.WELLKNOWN_MANIFEST_PATH)
        assert first.status_code == 200
        etag = first.headers.get("etag")
        assert etag is not None
        second = client.get(
            wellknown.WELLKNOWN_MANIFEST_PATH,
            headers={"If-None-Match": etag},
        )
        assert second.status_code == 304
        assert len(second.content) == 0 or second.content in (b"", b"None")

    def test_etag_conditional_returns_200_when_no_match(
        self, client: TestClient
    ) -> None:
        """If-None-Match with wrong ETag returns 200 with body."""
        response = client.get(
            wellknown.WELLKNOWN_MANIFEST_PATH,
            headers={"If-None-Match": '"wrong-etag-value"'},
        )
        assert response.status_code == 200
        assert response.json() is not None
