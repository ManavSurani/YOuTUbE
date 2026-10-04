"""Tests for version and update manifest URLs."""

from urllib.parse import urlparse

from app.version import UPDATE_MANIFEST_URL


def test_update_manifest_url():
    parsed = urlparse(UPDATE_MANIFEST_URL)
    assert parsed.netloc == "raw.githubusercontent.com"
    assert parsed.path.startswith("/ManavSurani/YOuTUbE/")
