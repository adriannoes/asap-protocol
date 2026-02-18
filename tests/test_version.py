from asap import __version__


def test_version():
    """Test that the package version is exposed correctly."""
    assert __version__ == "1.3.0"
