from pathlib import Path
from app.core.shortcut import get_desktop_dir, create_desktop_shortcut


def test_get_desktop_dir():
    desktop = get_desktop_dir()
    assert isinstance(desktop, Path)
    assert desktop.exists()


def test_create_shortcut_skipped_in_dev():
    # In development / testing without force flag, creation is cleanly skipped
    res = create_desktop_shortcut(force=False)
    assert res is False
