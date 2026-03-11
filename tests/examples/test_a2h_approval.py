"""Smoke tests for A2H approval example module."""

from __future__ import annotations


def test_a2h_approval_module_importable() -> None:
    """Module imports without errors."""
    from asap.examples.a2h_approval import main, parse_args, run_approval_demo

    assert callable(main)
    assert callable(parse_args)
    assert callable(run_approval_demo)


def test_a2h_approval_parse_args_defaults() -> None:
    """parse_args returns expected defaults."""
    from asap.examples.a2h_approval import parse_args

    args = parse_args([])
    assert args.gateway_url == "http://localhost:3000"
    assert args.principal_id == "user@example.com"


def test_a2h_approval_parse_args_custom() -> None:
    """parse_args accepts custom arguments."""
    from asap.examples.a2h_approval import parse_args

    args = parse_args(["--gateway-url", "http://gw:4000", "--principal-id", "alice"])
    assert args.gateway_url == "http://gw:4000"
    assert args.principal_id == "alice"
