"""Tests for Phase 6 Settings dialog and atomic settings persistence."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
import pytest

from app.core.app_updater import UpdateInfo
import app.core.settings as settings_mod
from app.core.settings import load_settings, save_settings
from app.ui.settings_dialog import SettingsDialog, validate_download_dir


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", settings_file)
    initial = {
        "download_dir": str(tmp_path / "downloads"),
        "theme": "dark",
        "auto_update": True,
    }
    (tmp_path / "downloads").mkdir(parents=True, exist_ok=True)
    save_settings(initial, settings_file)
    return settings_file


def test_settings_dialog_read_only_path_and_no_bottom_buttons(isolated_settings):
    """Path input is read-only, has no focus, and bottom Save/Cancel are absent."""
    dlg = SettingsDialog()

    # Path box checks
    assert dlg.folder_input.isReadOnly() is True
    assert dlg.folder_input.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert dlg.folder_input.cursor().shape() == Qt.CursorShape.ArrowCursor

    # No bottom Save/Cancel buttons
    assert not hasattr(dlg, "save_btn")
    assert not hasattr(dlg, "cancel_btn")

    # Header close button exists
    assert dlg.close_btn is not None
    assert not dlg.save_folder_btn.isVisible()


def test_settings_dialog_folder_change_and_save_flow(tmp_path, isolated_settings, monkeypatch):
    """Selecting a new folder reveals Save button; saving persists atomically."""
    dlg = SettingsDialog()
    assert not dlg.save_folder_btn.isVisible()

    new_dir = tmp_path / "new_download_dir"
    new_dir.mkdir()

    # Mock QFileDialog.getExistingDirectory
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(new_dir),
    )

    dlg._on_browse()

    assert dlg.folder_input.text() == str(new_dir)
    assert not dlg.save_folder_btn.isHidden()

    # Click save
    dlg._on_save_folder()

    # Verify settings file updated
    reloaded = load_settings(isolated_settings)
    assert reloaded["download_dir"] == str(new_dir.resolve())
    assert dlg.save_folder_btn._is_success is True


def test_settings_dialog_unwritable_folder_rejected(tmp_path, isolated_settings, monkeypatch):
    """Unwritable or invalid folder triggers warning and reverts path."""
    dlg = SettingsDialog()
    orig_path = dlg.folder_input.text()

    # Mock validate_download_dir to fail
    monkeypatch.setattr(
        "app.ui.settings_dialog.validate_download_dir",
        lambda p: (False, "Permission denied"),
    )

    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: warnings.append(args),
    )

    dlg.folder_input.setText("Z:\\nonexistent_network_share\\invalid")
    dlg._on_save_folder()

    assert len(warnings) == 1
    assert dlg.folder_input.text() == orig_path
    assert not dlg.save_folder_btn.isVisible()

    # Settings unchanged
    reloaded = load_settings(isolated_settings)
    assert reloaded["download_dir"] == orig_path


def test_settings_dialog_instant_theme_switch(isolated_settings, monkeypatch):
    """Changing appearance dropdown instantly updates stylesheet and settings."""
    app = QApplication.instance()
    mock_set_style = MagicMock()
    monkeypatch.setattr(app, "setStyleSheet", mock_set_style)

    dlg = SettingsDialog()
    idx_light = dlg.theme_combo.findData("light")
    dlg.theme_combo.setCurrentIndex(idx_light)

    # Instantly called stylesheet update
    assert mock_set_style.called

    # Instantly saved to settings.json
    reloaded = load_settings(isolated_settings)
    assert reloaded["theme"] == "light"


def test_settings_dialog_instant_auto_update_toggle(isolated_settings):
    """Toggling auto update checkbox immediately saves without Save button."""
    dlg = SettingsDialog()
    assert dlg.auto_update_check.isChecked() is True

    dlg.auto_update_check.setChecked(False)

    reloaded = load_settings(isolated_settings)
    assert reloaded["auto_update"] is False


def test_settings_dialog_check_now_available_and_offline(isolated_settings, monkeypatch):
    """Check now shows loading state, then handles available update or offline."""
    dlg = SettingsDialog()

    # 1. Test update available
    class MockAvailableWorker:
        def __init__(self, parent=None):
            self.checked = MagicMock()
            self.failed = MagicMock()

        def start(self):
            info = UpdateInfo(status="available", latest_version="2.5.0")
            dlg._on_checked_result(info)

    monkeypatch.setattr("app.ui.settings_dialog.UpdateCheckWorker", MockAvailableWorker)
    dlg._on_check_updates_now()

    assert "Version 2.5.0 is available" in dlg.update_status_label.text()
    assert not dlg.install_update_btn.isHidden()

    # 2. Test offline failure
    dlg._on_check_failed("Connection timed out")
    assert "No internet connection" in dlg.update_status_label.text()


def test_settings_dialog_export_log(tmp_path, isolated_settings, monkeypatch):
    """Export log copies app.log to user chosen path."""
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-10-02 12:00:00 [INFO] test log contents", encoding="utf-8")
    monkeypatch.setattr("app.ui.settings_dialog.APP_LOG_FILE", log_file)

    export_dest = tmp_path / "exported_YOuTUbE.log"
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(export_dest), "Log Files (*.log)"),
    )

    dlg = SettingsDialog()
    dlg._on_export_log()

    assert export_dest.exists()
    assert "test log contents" in export_dest.read_text(encoding="utf-8")
    assert dlg.export_log_btn._is_success is True


def test_atomic_settings_write(tmp_path, monkeypatch):
    """Settings saving uses atomic temporary file replacement."""
    target_file = tmp_path / "atomic_settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", target_file)

    save_settings({"key": "initial_value"}, target_file)
    assert target_file.exists()

    # Temporary file .tmp must not be left behind
    tmp_candidate = target_file.with_suffix(".tmp")
    assert not tmp_candidate.exists()

    # Re-save
    save_settings({"key": "updated_value"}, target_file)
    reloaded = load_settings(target_file)
    assert reloaded["key"] == "updated_value"
    assert not tmp_candidate.exists()
