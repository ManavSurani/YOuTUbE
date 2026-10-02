"""Unit tests for desktop shortcut creation across all 4 lifecycle situations."""

from pathlib import Path
import pytest
from app.version import APP_NAME
from app.core.shortcut import get_desktop_dir, create_desktop_shortcut


def test_get_desktop_dir():
    desktop = get_desktop_dir()
    assert isinstance(desktop, Path)
    assert desktop.exists()


def test_create_shortcut_skipped_in_dev():
    # In development / testing without force flag, creation is cleanly skipped
    res = create_desktop_shortcut(force=False)
    assert res is False


def test_situation_1_installer_made(tmp_path: Path, monkeypatch):
    """Situation 1: Shortcut was created by Inno Setup installer before first run."""
    import app.core.shortcut as sc_mod

    settings_store = {"shortcut_created": False}
    monkeypatch.setattr(sc_mod, "load_settings", lambda: dict(settings_store))
    monkeypatch.setattr(sc_mod, "save_settings", lambda s: settings_store.update(s))

    fake_desktop = tmp_path / "Desktop"
    fake_desktop.mkdir()
    existing_lnk = fake_desktop / f"{APP_NAME}.lnk"
    existing_lnk.write_text("installer_shortcut")

    # Run shortcut creator (with force=True to simulate frozen/first-run logic in tests)
    res = create_desktop_shortcut(
        force=False,  # Should check shortcut_path existence
        desktop_dir_override=fake_desktop,
    )
    # When not frozen and not force, returns False by rule 1
    assert res is False

    # Now simulate frozen environment (sys.frozen = True)
    monkeypatch.setattr(sc_mod.sys, "frozen", True, raising=False)
    res = create_desktop_shortcut(
        force=False,
        desktop_dir_override=fake_desktop,
    )
    assert res is True
    assert settings_store["shortcut_created"] is True
    # Ensure existing content wasn't overwritten
    assert existing_lnk.read_text() == "installer_shortcut"


def test_situation_2_missing_on_first_run(tmp_path: Path, monkeypatch):
    """Situation 2: First run without installer (shortcut missing, shortcut_created is False)."""
    import app.core.shortcut as sc_mod

    settings_store = {"shortcut_created": False}
    monkeypatch.setattr(sc_mod, "load_settings", lambda: dict(settings_store))
    monkeypatch.setattr(sc_mod, "save_settings", lambda s: settings_store.update(s))
    monkeypatch.setattr(sc_mod.sys, "frozen", True, raising=False)

    fake_desktop = tmp_path / "Desktop"
    fake_desktop.mkdir()
    fake_exe = tmp_path / "YOuTUbE.exe"
    fake_exe.write_text("dummy")

    res = create_desktop_shortcut(
        force=False,
        custom_target=fake_exe,
        desktop_dir_override=fake_desktop,
    )
    assert res is True
    assert (fake_desktop / f"{APP_NAME}.lnk").exists()
    assert settings_store["shortcut_created"] is True


def test_situation_3_already_exists(tmp_path: Path, monkeypatch):
    """Situation 3: App restarts when shortcut already exists and flag is True."""
    import app.core.shortcut as sc_mod

    settings_store = {"shortcut_created": True}
    monkeypatch.setattr(sc_mod, "load_settings", lambda: dict(settings_store))
    monkeypatch.setattr(sc_mod, "save_settings", lambda s: settings_store.update(s))
    monkeypatch.setattr(sc_mod.sys, "frozen", True, raising=False)

    fake_desktop = tmp_path / "Desktop"
    fake_desktop.mkdir()
    lnk = fake_desktop / f"{APP_NAME}.lnk"
    lnk.write_text("existing")

    res = create_desktop_shortcut(
        force=False,
        desktop_dir_override=fake_desktop,
    )
    # Should skip because shortcut_created is True
    assert res is False
    assert lnk.read_text() == "existing"


def test_situation_4_user_deleted(tmp_path: Path, monkeypatch):
    """Situation 4: User intentionally deleted the desktop shortcut; app must never recreate it."""
    import app.core.shortcut as sc_mod

    settings_store = {"shortcut_created": True}
    monkeypatch.setattr(sc_mod, "load_settings", lambda: dict(settings_store))
    monkeypatch.setattr(sc_mod, "save_settings", lambda s: settings_store.update(s))
    monkeypatch.setattr(sc_mod.sys, "frozen", True, raising=False)

    fake_desktop = tmp_path / "Desktop"
    fake_desktop.mkdir()
    shortcut_file = fake_desktop / f"{APP_NAME}.lnk"
    # Shortcut does NOT exist because user deleted it!
    assert not shortcut_file.exists()

    res = create_desktop_shortcut(
        force=False,
        desktop_dir_override=fake_desktop,
    )
    # Must NOT recreate!
    assert res is False
    assert not shortcut_file.exists(), "App recreated shortcut after user deleted it!"
