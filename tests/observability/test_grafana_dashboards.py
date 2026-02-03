"""Tests for Grafana dashboard JSON files.

Validates that dashboard JSON under src/asap/observability/dashboards/
is well-formed and contains expected panels and metric queries.
"""

import json
from pathlib import Path

import pytest

# Directory containing dashboard JSON (from repo root)
DASHBOARDS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "asap" / "observability" / "dashboards"
)


def _dashboard_files() -> list[Path]:
    """Return paths to dashboard JSON files."""
    if not DASHBOARDS_DIR.is_dir():
        return []
    return list(DASHBOARDS_DIR.glob("*.json"))


@pytest.mark.parametrize("path", _dashboard_files(), ids=lambda p: p.name)
def test_dashboard_json_valid(path: Path) -> None:
    """Each dashboard file must be valid JSON."""
    content = path.read_text()
    data = json.loads(content)
    assert isinstance(data, dict), "Dashboard root must be a dict"


@pytest.mark.parametrize("path", _dashboard_files(), ids=lambda p: p.name)
def test_dashboard_has_schema_and_panels(path: Path) -> None:
    """Dashboard must have schemaVersion and panels array."""
    data = json.loads(path.read_text())
    assert "schemaVersion" in data, f"{path.name}: missing schemaVersion"
    assert "panels" in data, f"{path.name}: missing panels"
    assert isinstance(data["panels"], list), f"{path.name}: panels must be a list"
    assert len(data["panels"]) >= 1, f"{path.name}: at least one panel required"


@pytest.mark.parametrize("path", _dashboard_files(), ids=lambda p: p.name)
def test_dashboard_panels_have_targets(path: Path) -> None:
    """Panels that have targets must include at least one target with expr (Prometheus)."""
    data = json.loads(path.read_text())
    panels = data.get("panels", [])
    for i, panel in enumerate(panels):
        targets = panel.get("targets", [])
        if not targets:
            continue
        has_expr = any(isinstance(t, dict) and t.get("expr") for t in targets)
        assert has_expr, (
            f"{path.name} panel[{i}] ({panel.get('title', '')}) has targets but no expr"
        )


def test_red_dashboard_has_red_panels() -> None:
    """ASAP RED dashboard must have request rate, error rate, and latency panels."""
    red_path = DASHBOARDS_DIR / "asap-red.json"
    if not red_path.exists():
        pytest.skip("asap-red.json not found")
    data = json.loads(red_path.read_text())
    titles = [p.get("title", "") for p in data.get("panels", []) if isinstance(p.get("title"), str)]
    assert "Request Rate" in titles, "RED dashboard should have Request Rate panel"
    assert "Error Rate" in titles, "RED dashboard should have Error Rate panel"
    assert any("atency" in t for t in titles), "RED dashboard should have a Latency panel"


def test_detailed_dashboard_has_state_panels() -> None:
    """ASAP Detailed dashboard must have state-related panels."""
    detailed_path = DASHBOARDS_DIR / "asap-detailed.json"
    if not detailed_path.exists():
        pytest.skip("asap-detailed.json not found")
    data = json.loads(detailed_path.read_text())
    titles = [p.get("title", "") for p in data.get("panels", []) if isinstance(p.get("title"), str)]
    assert any("tate" in t for t in titles), "Detailed dashboard should have state-related panel(s)"
    assert any("andler" in t or "ircuit" in t for t in titles), (
        "Detailed dashboard should have handler or circuit panel"
    )
