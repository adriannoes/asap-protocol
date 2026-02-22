"""Unit tests for scripts/process_registration.py (IssueOps registration parsing and validation)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.process_registration import (
    fetch_manifest,
    load_registry,
    parse_issue_body,
    run,
    save_registry,
)


# Sample GitHub Issue Form body (markdown with ### headers from register_agent.yml)
VALID_BODY_MINIMAL = """
### Agent name (slug-friendly)
my-agent

### Description
An agent that does research.

### Manifest URL
https://example.com/manifest.json

### HTTP Endpoint
https://example.com/asap

### WebSocket Endpoint (optional)


### Skills
web_research, summarization

### Built with (framework)


### Repository URL (optional)


### Documentation URL (optional)


### Confirmation
- [x] I confirm
"""

VALID_BODY_WITH_OPTIONALS = """
### Agent name (slug-friendly)
other-agent

### Description
Another agent.

### Manifest URL
https://api.example.com/.well-known/asap-manifest.json

### HTTP Endpoint
https://api.example.com/asap

### WebSocket Endpoint (optional)
wss://api.example.com/asap/events

### Skills
code_review

### Built with (framework)
LangChain

### Repository URL (optional)
https://github.com/me/repo

### Documentation URL (optional)
https://docs.example.com/agent

### Confirmation
- [x] I confirm
"""

# Minimal valid Manifest JSON (matches expected_id for author "testuser", name "my-agent")
VALID_MANIFEST_JSON = {
    "id": "urn:asap:agent:testuser:my-agent",
    "name": "my-agent",
    "version": "1.0.0",
    "description": "An agent that does research.",
    "capabilities": {
        "asap_version": "1.1.0",
        "skills": [
            {"id": "web_research", "description": "Research"},
            {"id": "summarization", "description": "Summarize"},
        ],
        "state_persistence": False,
        "streaming": False,
        "mcp_tools": [],
    },
    "endpoints": {
        "asap": "https://example.com/asap",
        "events": None,
    },
}


class TestParseIssueBody:
    """Tests for parse_issue_body."""

    def test_parses_valid_minimal_body(self) -> None:
        out = parse_issue_body(VALID_BODY_MINIMAL)
        assert out["name"] == "my-agent"
        assert out["description"] == "An agent that does research."
        assert out["manifest_url"] == "https://example.com/manifest.json"
        assert out["http_endpoint"] == "https://example.com/asap"
        assert out["skills"] == "web_research, summarization"
        assert out.get("websocket_endpoint") == ""
        assert out.get("built_with") == ""

    def test_parses_valid_body_with_optionals(self) -> None:
        out = parse_issue_body(VALID_BODY_WITH_OPTIONALS)
        assert out["name"] == "other-agent"
        assert out["repository_url"] == "https://github.com/me/repo"
        assert out["documentation_url"] == "https://docs.example.com/agent"
        assert out["built_with"] == "LangChain"
        assert out["websocket_endpoint"] == "wss://api.example.com/asap/events"

    def test_parses_empty_body(self) -> None:
        assert parse_issue_body("") == {}
        assert parse_issue_body("   \n  ") == {}

    def test_parses_invalid_markdown_gracefully(self) -> None:
        """Non-form markdown returns only matched fields."""
        body = "### Agent name (slug-friendly)\nfoo\n### Unknown section\nbar"
        out = parse_issue_body(body)
        assert out.get("name") == "foo"
        assert "Unknown section" not in out


class TestFetchManifestSSRF:
    """Tests for fetch_manifest SSRF protection (RF-1)."""

    def test_blocks_metadata_url(self) -> None:
        """Block cloud metadata endpoints."""
        with pytest.raises(ValueError, match="Blocked URL"):
            fetch_manifest("http://169.254.169.254/latest/meta-data/")

    def test_blocks_localhost(self) -> None:
        """Block loopback addresses."""
        with pytest.raises(ValueError, match="Blocked URL"):
            fetch_manifest("http://localhost/manifest.json")

    def test_blocks_private_ip(self) -> None:
        """Block private IP ranges."""
        with pytest.raises(ValueError, match="Blocked URL"):
            fetch_manifest("http://192.168.1.1/manifest.json")


def _mock_httpx_client(response_json: dict) -> MagicMock:
    """Build a MagicMock for httpx.Client that returns the given JSON as manifest."""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(response_json)
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_resp
    mock_client.__exit__.return_value = None
    return mock_client


class TestProcessRegistrationRun:
    """Tests for run() with mocked manifest fetch and temp files."""

    def test_valid_issue_writes_registry_and_valid_result(
        self,
        tmp_path: Path,
    ) -> None:
        with patch(
            "scripts.process_registration.httpx.Client",
            return_value=_mock_httpx_client(VALID_MANIFEST_JSON),
        ):
            registry_path = tmp_path / "registry.json"
            registry_path.write_text("[]")
            output_path = tmp_path / "result.json"

            run(
                body=VALID_BODY_MINIMAL,
                issue_number="1",
                author="testuser",
                output_path=str(output_path),
                registry_path=str(registry_path),
            )

        result = json.loads(output_path.read_text())
        assert result["valid"] is True

        registry = json.loads(registry_path.read_text())
        assert len(registry) == 1
        entry = registry[0]
        assert entry["id"] == "urn:asap:agent:testuser:my-agent"
        assert entry["name"] == "my-agent"
        assert entry["skills"] == ["web_research", "summarization"]
        assert "http" in entry["endpoints"]
        assert entry["endpoints"]["manifest"] == "https://example.com/manifest.json"

    def test_valid_issue_with_optionals_passes_through(
        self,
        tmp_path: Path,
    ) -> None:
        manifest = dict(VALID_MANIFEST_JSON)
        manifest["id"] = "urn:asap:agent:testuser:other-agent"
        manifest["name"] = "other-agent"
        manifest["capabilities"] = dict(manifest["capabilities"])
        manifest["capabilities"]["skills"] = [{"id": "code_review", "description": "Review"}]
        manifest["endpoints"] = dict(manifest["endpoints"])
        manifest["endpoints"]["asap"] = "https://api.example.com/asap"
        manifest["endpoints"]["events"] = "wss://api.example.com/asap/events"

        with patch(
            "scripts.process_registration.httpx.Client",
            return_value=_mock_httpx_client(manifest),
        ):
            registry_path = tmp_path / "registry.json"
            registry_path.write_text("[]")
            output_path = tmp_path / "result.json"

            run(
                body=VALID_BODY_WITH_OPTIONALS,
                issue_number="2",
                author="testuser",
                output_path=str(output_path),
                registry_path=str(registry_path),
            )

        result = json.loads(output_path.read_text())
        assert result["valid"] is True
        registry = json.loads(registry_path.read_text())
        entry = registry[0]
        assert entry.get("repository_url") == "https://github.com/me/repo"
        assert entry.get("documentation_url") == "https://docs.example.com/agent"
        assert entry.get("built_with") == "LangChain"

    def test_invalid_missing_required_fields(self, tmp_path: Path) -> None:
        output_path = tmp_path / "result.json"
        run(
            body="### Agent name (slug-friendly)\n\n### Description\n\n### Manifest URL\n\n### HTTP Endpoint\n\n### Skills\n",
            issue_number="3",
            author="user",
            output_path=str(output_path),
            registry_path=str(tmp_path / "registry.json"),
        )
        result = json.loads(output_path.read_text())
        assert result["valid"] is False
        assert "errors" in result
        assert "Missing" in result["errors"] or "required" in result["errors"].lower()

    def test_invalid_manifest_id_mismatch(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_wrong_id = dict(VALID_MANIFEST_JSON)
        manifest_wrong_id["id"] = "urn:asap:agent:other:my-agent"
        with patch(
            "scripts.process_registration.httpx.Client",
            return_value=_mock_httpx_client(manifest_wrong_id),
        ):
            registry_path = tmp_path / "registry.json"
            registry_path.write_text("[]")
            output_path = tmp_path / "result.json"

            run(
                body=VALID_BODY_MINIMAL,
                issue_number="4",
                author="testuser",
                output_path=str(output_path),
                registry_path=str(registry_path),
            )

        result = json.loads(output_path.read_text())
        assert result["valid"] is False
        assert (
            "Manifest id must be" in result["errors"]
            or "urn:asap:agent:testuser" in result["errors"]
        )

    def test_invalid_manifest_unreachable(
        self,
        tmp_path: Path,
    ) -> None:
        import httpx

        with patch(
            "scripts.process_registration.httpx.Client",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            output_path = tmp_path / "result.json"
            run(
                body=VALID_BODY_MINIMAL,
                issue_number="5",
                author="testuser",
                output_path=str(output_path),
                registry_path=str(tmp_path / "registry.json"),
            )
        result = json.loads(output_path.read_text())
        assert result["valid"] is False
        assert "unreachable" in result["errors"].lower() or "error" in result["errors"].lower()

    def test_invalid_duplicate_agent_id(
        self,
        tmp_path: Path,
    ) -> None:
        existing = [
            {
                "id": "urn:asap:agent:testuser:my-agent",
                "name": "my-agent",
                "description": "Existing",
                "endpoints": {
                    "http": "https://example.com/asap",
                    "manifest": "https://example.com/m.json",
                },
                "skills": ["web_research"],
                "asap_version": "1.1.0",
            }
        ]
        registry_path = tmp_path / "registry.json"
        registry_path.write_text(json.dumps(existing))
        output_path = tmp_path / "result.json"

        with patch(
            "scripts.process_registration.httpx.Client",
            return_value=_mock_httpx_client(VALID_MANIFEST_JSON),
        ):
            run(
                body=VALID_BODY_MINIMAL,
                issue_number="6",
                author="testuser",
                output_path=str(output_path),
                registry_path=str(registry_path),
            )

        result = json.loads(output_path.read_text())
        assert result["valid"] is False
        assert "already registered" in result["errors"].lower()
        # Registry unchanged
        assert json.loads(registry_path.read_text()) == existing

    def test_blocks_ssrf_manifest_url(
        self,
        tmp_path: Path,
    ) -> None:
        """Blocked manifest URL (SSRF) returns validation error (RF-1)."""
        output_path = tmp_path / "result.json"
        body = VALID_BODY_MINIMAL.replace(
            "https://example.com/manifest.json",
            "http://169.254.169.254/latest/meta-data/",
        )
        run(
            body=body,
            issue_number="7",
            author="testuser",
            output_path=str(output_path),
            registry_path=str(tmp_path / "registry.json"),
        )
        result = json.loads(output_path.read_text())
        assert result["valid"] is False
        assert "Blocked" in result["errors"] or "private" in result["errors"].lower()


class TestLoadRegistry:
    """Tests for load_registry."""

    def test_load_empty_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns empty list."""
        assert load_registry(str(tmp_path / "nonexistent.json")) == []

    def test_load_malformed_json_raises(self, tmp_path: Path) -> None:
        """Malformed JSON raises json.JSONDecodeError."""
        bad = tmp_path / "bad.json"
        bad.write_text("{ invalid")
        with pytest.raises(json.JSONDecodeError):
            load_registry(str(bad))

    def test_load_lite_registry_wrapper_format(self, tmp_path: Path) -> None:
        """LiteRegistry wrapper format (agents key) is supported."""
        data = {
            "version": "1.0",
            "agents": [{"id": "urn:asap:agent:test", "name": "Test"}],
        }
        path = tmp_path / "registry.json"
        path.write_text(json.dumps(data))
        result = load_registry(str(path))
        assert len(result) == 1
        assert result[0]["id"] == "urn:asap:agent:test"

    def test_load_array_format(self, tmp_path: Path) -> None:
        """Array format (direct list) is supported."""
        data = [{"id": "urn:asap:agent:one", "name": "One"}]
        path = tmp_path / "registry.json"
        path.write_text(json.dumps(data))
        result = load_registry(str(path))
        assert len(result) == 1
        assert result[0]["id"] == "urn:asap:agent:one"


class TestSaveRegistry:
    """Tests for save_registry atomic write."""

    def test_save_registry_atomic(self, tmp_path: Path) -> None:
        """save_registry writes atomically."""
        path = tmp_path / "registry.json"
        agents = [
            {
                "id": "urn:asap:agent:test",
                "name": "Test",
                "description": "Test agent",
                "endpoints": {"http": "https://example.com/asap"},
                "skills": ["skill1"],
                "asap_version": "1.1.0",
            }
        ]
        save_registry(str(path), agents)
        assert json.loads(path.read_text()) == agents
