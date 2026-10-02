import sys
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.settings import load_settings, save_settings
from app.ui.settings_dialog import SettingsDialog

_app = QApplication.instance() or QApplication(sys.argv)


def test_settings_dialog_load_and_save(tmp_path, monkeypatch):
    import app.core.settings as settings_mod

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", settings_file)

    initial = {
        "download_dir": str(tmp_path),
        "theme": "dark",
        "container": "mp4",
        "auto_update": False,
        "last_app_check": 0,
        "last_tool_check": 0,
    }
    save_settings(initial, settings_file)

    dlg = SettingsDialog()
    assert dlg.folder_input.text() == str(tmp_path)
    assert dlg.container_combo.currentData() == "mp4"
    assert dlg.theme_combo.currentData() == "dark"
    assert dlg.auto_update_check.isChecked() is False

    # Note about resolution limitation is visible for container
    assert "MP4 may limit" in dlg.container_note.text()

    # Modify settings in dialog
    new_dir = tmp_path / "custom_downloads"
    new_dir.mkdir()
    dlg.folder_input.setText(str(new_dir))
    dlg.container_combo.setCurrentIndex(dlg.container_combo.findData("mkv"))
    dlg.auto_update_check.setChecked(True)

    dlg._on_save()

    # Verify saved settings
    reloaded = load_settings(settings_file)
    assert reloaded["download_dir"] == str(new_dir)
    assert reloaded["container"] == "mkv"
    assert reloaded["auto_update"] is True


def test_theme_switch_applies_stylesheet(monkeypatch):
    mock_set_style = MagicMock()
    monkeypatch.setattr(_app, "setStyleSheet", mock_set_style)

    dlg = SettingsDialog()
    # Switch to light theme
    light_idx = dlg.theme_combo.findData("light")
    dlg.theme_combo.setCurrentIndex(light_idx)

    assert mock_set_style.called
