"""Tests for Chunk 9.1: Startup history repair off the UI thread (U3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication
import pytest

from app.version import APP_VERSION


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    import app.core.settings as settings_mod
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", settings_file)
    initial = {
        "download_dir": str(tmp_path / "downloads"),
        "theme": "dark",
        "auto_update": True,
    }
    settings_mod.save_settings(initial)
    return settings_file


def test_startup_repair_worker_calls_configured_folder_and_not_ui_thread(isolated_settings, monkeypatch):
    """(a) called with configured folder, (b) not on UI thread."""
    from app.main import maybe_start_history_repair
    from app.ui.main_window import MainWindow

    custom_dir = "C:/TestCustomDownloads"
    from app.core.settings import save_settings, load_settings
    s = load_settings()
    s["download_dir"] = custom_dir
    s["history_repair_version"] = "0.0.0"
    save_settings(s)

    called_threads = []
    called_dirs = []

    def mock_repair(download_dir=None, custom_db=None):
        called_threads.append(QThread.currentThread())
        called_dirs.append(download_dir)
        return 2

    monkeypatch.setattr("app.core.history_service.repair_existing_rows", mock_repair)

    with patch("app.ui.main_window.NetworkMonitor.start"):
        win = MainWindow()
        try:
            worker = maybe_start_history_repair(win)
            assert worker is not None
            worker.wait(3000)

            # (a) Configured folder was passed
            assert custom_dir in called_dirs
            # (b) Was not executed on UI main thread
            ui_thread = QApplication.instance().thread()
            assert len(called_threads) == 1
            assert called_threads[0] != ui_thread
        finally:
            win.close()


def test_startup_repair_skipped_when_version_matches(isolated_settings, monkeypatch):
    """(c) A second start with the same version does not call it."""
    from app.main import maybe_start_history_repair
    from app.ui.main_window import MainWindow
    from app.core.settings import save_settings, load_settings

    s = load_settings()
    s["history_repair_version"] = APP_VERSION
    save_settings(s)

    mock_repair = MagicMock()
    monkeypatch.setattr("app.core.history_service.repair_existing_rows", mock_repair)

    with patch("app.ui.main_window.NetworkMonitor.start"):
        win = MainWindow()
        try:
            worker = maybe_start_history_repair(win)
            assert worker is None
            mock_repair.assert_not_called()
        finally:
            win.close()


def test_history_refresh_happens_after_worker_signals(isolated_settings, monkeypatch):
    """(d) History refresh happens after the worker signals."""
    from app.main import maybe_start_history_repair
    from app.ui.main_window import MainWindow
    from app.core.settings import save_settings, load_settings

    s = load_settings()
    s["history_repair_version"] = "0.0.0"
    save_settings(s)

    monkeypatch.setattr("app.core.history_service.repair_existing_rows", lambda download_dir=None: 3)

    with patch("app.ui.main_window.NetworkMonitor.start"):
        win = MainWindow()
        try:
            refreshed = []
            monkeypatch.setattr(win.history_tab, "refresh_items", lambda: refreshed.append(True))

            worker = maybe_start_history_repair(win)
            assert worker is not None
            worker.wait(3000)
            QApplication.processEvents()

            assert len(refreshed) >= 1
            # Check that settings updated to APP_VERSION
            updated_settings = load_settings()
            assert updated_settings.get("history_repair_version") == APP_VERSION
        finally:
            win.close()

