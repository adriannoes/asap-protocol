from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from asap.auth.jwks import audience_matches_expected, issuer_matches_expected
from asap.auth.middleware import parse_expected_audience_from_env


class TestAudienceMatchesExpected:
    @pytest.mark.parametrize(
        ("claims", "expected", "want"),
        [
            ({"aud": "a"}, "a", True),
            ({"aud": "a"}, ["a", "b"], True),
            ({"aud": ["a", "b"]}, ["b", "c"], True),
            ({"aud": ["a", "b"]}, ["c", "d"], False),
            ({"aud": 123}, "a", False),
            ({}, "a", False),
            ({"aud": ["a", 1, "b"]}, ["b"], True),
        ],
    )
    def test_audience_matching(
        self,
        claims: Mapping[str, Any],
        expected: str | list[str],
        want: bool,
    ) -> None:
        assert audience_matches_expected(claims, expected) is want


class TestIssuerMatchesExpected:
    def test_match_with_trailing_slash_normalization(self) -> None:
        claims = {"iss": "https://issuer.example/"}
        assert issuer_matches_expected(claims, "https://issuer.example") is True

    def test_no_match_different_issuer(self) -> None:
        assert issuer_matches_expected({"iss": "https://a.example"}, "https://b.example") is False

    @pytest.mark.parametrize("claims", [{}, {"iss": ""}, {"iss": "   "}, {"iss": 42}])
    def test_missing_or_invalid_iss(self, claims: dict[str, object]) -> None:
        assert issuer_matches_expected(claims, "https://issuer.example") is False


class TestParseExpectedAudienceFromEnv:
    @pytest.mark.parametrize("raw", [None, "", "   ", ",,,", " , "])
    def test_empty_values_return_none(self, raw: str | None) -> None:
        assert parse_expected_audience_from_env(raw) is None

    def test_single_value(self) -> None:
        assert parse_expected_audience_from_env("urn:asap:agent:identity") == (
            "urn:asap:agent:identity"
        )

    def test_csv_list_with_spaces(self) -> None:
        assert parse_expected_audience_from_env(" a , b , c ") == ["a", "b", "c"]
