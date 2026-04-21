"""Compliance Harness v2 baseline for the example agent (CI regression guard)."""

from __future__ import annotations

import pytest

from asap.testing.asgi_factory import make_compliance_test_app
from asap.testing.compliance import run_compliance_harness_v2

EXPECTED_COMPLIANCE_SCORE = 1.0


@pytest.mark.asyncio
async def test_compliance_harness_v2_baseline() -> None:
    """Fail CI if the reference app scores below 1.0 on Harness v2."""
    app = make_compliance_test_app()
    report = await run_compliance_harness_v2(app)
    assert report.score == EXPECTED_COMPLIANCE_SCORE, report.summary
    failed = [c for c in report.checks if not c.passed]
    assert not failed, [(c.name, c.category, c.message) for c in failed]
