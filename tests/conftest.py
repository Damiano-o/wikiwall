import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never let a test touch the real %LOCALAPPDATA%\\WikiWall data."""
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
