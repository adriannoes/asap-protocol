"""Tests for auth utils (e.g. parse_scope)."""

from __future__ import annotations

from asap.auth.utils import parse_scope


def test_parse_scope_none_returns_empty() -> None:
    """parse_scope(None) returns []."""
    assert parse_scope(None) == []


def test_parse_scope_list_returns_strings() -> None:
    """parse_scope(list) returns list of strings."""
    assert parse_scope(["a", "b", "c"]) == ["a", "b", "c"]
    assert parse_scope([1, 2]) == ["1", "2"]


def test_parse_scope_str_splits_and_strips() -> None:
    """parse_scope(str) splits on whitespace and strips."""
    assert parse_scope("asap:read asap:execute") == ["asap:read", "asap:execute"]
    assert parse_scope("  a   b  ") == ["a", "b"]


def test_parse_scope_invalid_type_returns_empty() -> None:
    """parse_scope with non-None, non-list, non-str (e.g. int, dict) returns []."""
    assert parse_scope(123) == []
    assert parse_scope({}) == []
    assert parse_scope(True) == []
