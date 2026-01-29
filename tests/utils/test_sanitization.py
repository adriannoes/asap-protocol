"""Unit tests for log sanitization utilities.

This module tests the sanitization functions that prevent sensitive data
from being exposed in logs.
"""

from asap.utils.sanitization import sanitize_nonce, sanitize_token, sanitize_url


class TestSanitizeToken:
    """Tests for token sanitization."""

    def test_long_token_shows_prefix_only(self) -> None:
        """Test that long tokens show only first 8 characters."""
        token = "sk_live_1234567890abcdef"
        result = sanitize_token(token)
        assert result == "sk_live_..."
        assert len(result) == 11  # 8 chars + "..."

    def test_short_token_unchanged(self) -> None:
        """Test that short tokens (<=8 chars) are returned unchanged."""
        token = "short"
        result = sanitize_token(token)
        assert result == "short"

    def test_exactly_8_chars_unchanged(self) -> None:
        """Test that exactly 8-character tokens are returned unchanged."""
        token = "12345678"
        result = sanitize_token(token)
        assert result == "12345678"

    def test_empty_token_returns_empty(self) -> None:
        """Test that empty tokens return empty string."""
        result = sanitize_token("")
        assert result == ""

    def test_preserves_token_type_prefix(self) -> None:
        """Test that token type prefixes are preserved for identification."""
        test_cases = [
            ("pk_test_abc123", "pk_test_..."),
            ("sk_live_xyz789", "sk_live_..."),
            ("bearer_token_12345", "bearer_t..."),
        ]
        for token, expected in test_cases:
            result = sanitize_token(token)
            assert result == expected


class TestSanitizeNonce:
    """Tests for nonce sanitization."""

    def test_long_nonce_shows_prefix_only(self) -> None:
        """Test that long nonces show only first 8 characters."""
        nonce = "a1b2c3d4e5f6g7h8i9j0"
        result = sanitize_nonce(nonce)
        assert result == "a1b2c3d4..."
        assert len(result) == 11  # 8 chars + "..."

    def test_short_nonce_unchanged(self) -> None:
        """Test that short nonces (<=8 chars) are returned unchanged."""
        nonce = "short"
        result = sanitize_nonce(nonce)
        assert result == "short"

    def test_exactly_8_chars_unchanged(self) -> None:
        """Test that exactly 8-character nonces are returned unchanged."""
        nonce = "12345678"
        result = sanitize_nonce(nonce)
        assert result == "12345678"

    def test_empty_nonce_returns_empty(self) -> None:
        """Test that empty nonces return empty string."""
        result = sanitize_nonce("")
        assert result == ""

    def test_various_nonce_formats(self) -> None:
        """Test sanitization with various nonce formats."""
        test_cases = [
            ("uuid-like-1234-5678-90ab", "uuid-lik..."),
            ("random123456789", "random12..."),
            ("hex_abcdef123456", "hex_abcd..."),
        ]
        for nonce, expected in test_cases:
            result = sanitize_nonce(nonce)
            assert result == expected


class TestSanitizeUrl:
    """Tests for URL sanitization."""

    def test_url_with_password_masks_password(self) -> None:
        """Test that URLs with passwords mask the password."""
        url = "https://user:secret@example.com/api"
        result = sanitize_url(url)
        assert result == "https://user:***@example.com/api"
        assert "secret" not in result
        assert "user" in result

    def test_url_without_password_unchanged(self) -> None:
        """Test that URLs without passwords are unchanged."""
        url = "https://example.com/api"
        result = sanitize_url(url)
        assert result == url

    def test_url_with_username_only_unchanged(self) -> None:
        """Test that URLs with username but no password are unchanged."""
        url = "https://user@example.com/api"
        result = sanitize_url(url)
        assert result == url

    def test_url_with_port_and_password(self) -> None:
        """Test that URLs with port and password mask password correctly."""
        url = "https://user:pass@example.com:8080/api"
        result = sanitize_url(url)
        assert result == "https://user:***@example.com:8080/api"
        assert "pass" not in result
        assert ":8080" in result

    def test_http_url_with_credentials(self) -> None:
        """Test that HTTP URLs with credentials are sanitized."""
        url = "http://admin:password123@localhost:8000/asap"
        result = sanitize_url(url)
        assert result == "http://admin:***@localhost:8000/asap"
        assert "password123" not in result

    def test_url_with_query_and_fragment(self) -> None:
        """Test that URLs with query params and fragments preserve them."""
        url = "https://user:secret@example.com/api?param=value#fragment"
        result = sanitize_url(url)
        assert result == "https://user:***@example.com/api?param=value#fragment"
        assert "secret" not in result
        assert "param=value" in result
        assert "#fragment" in result

    def test_empty_url_returns_empty(self) -> None:
        """Test that empty URLs return empty string."""
        result = sanitize_url("")
        assert result == ""

    def test_invalid_url_fallback(self) -> None:
        """Test that invalid URLs use fallback sanitization."""
        # This should trigger the exception handler
        invalid_url = "not-a-valid-url://user:pass@host"
        result = sanitize_url(invalid_url)
        # Should mask credentials even if parsing fails
        assert "pass" not in result or "***" in result

    def test_url_with_special_characters_in_password(self) -> None:
        """Test that URLs with special characters in password are sanitized."""
        url = "https://user:p@ssw0rd!@example.com/api"
        result = sanitize_url(url)
        assert result == "https://user:***@example.com/api"
        assert "p@ssw0rd!" not in result
