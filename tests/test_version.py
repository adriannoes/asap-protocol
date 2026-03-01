import importlib.metadata

from asap import __version__


def test_version():
    """Package __version__ matches installed package metadata (pyproject.toml)."""
    expected = importlib.metadata.version("asap-protocol")
    assert __version__ == expected
