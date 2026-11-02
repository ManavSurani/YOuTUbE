"""Plan 23 Phase 5: history and settings upgrades."""

import time
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QSystemTrayIcon

import app.ui.theme as theme
from app.core.history_db import HistoryItem
from app.ui.theme import tok

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def settings_store(monkeypatch):
    """In-memory settings for every module that reads or writes them."""
    from app.core import settings as settings_mod
    store = settings_mod.get_default_settings()
    load = lambda *a, **kw: dict(store)  # noqa: E731
    save = lambda s, *a, **kw: store.update(s)  # noqa: E731
    for mod in ("app.core.settings", "app.ui.settings_dialog", "app.ui.video_tab", "app.ui.audio_tab",
                "app.ui.main_window", "app.ui.history_tab"):
        monkeypatch.setattr(f"{mod}.load_settings", load, raising=False)
        monkeypatch.setattr(f"{mod}.save_settings", save, raising=False)
    return store


def _settle(ms: int = 30) -> None:
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def _show(widget, w=880, h=700):
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    widget.resize(w, h)
    widget.show()
    _settle()
    return widget


def _utc(dt_local: datetime) -> str:
    return dt_local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _item(i, when: datetime, title="Item", channel="Chan") -> HistoryItem:
    return HistoryItem(id=i, title=title, url=URL, type="video", quality="1080p", file_path="",
                       size_bytes=5000, duration=60, created_at=_utc(when), channel=channel)


# 5.1 Date groups ------------------------------------------------------------------

def test_history_groups_by_day(monkeypatch):
    from app.ui import history_tab
    now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    items = [_item(1, now), _item(2, now - timedelta(days=1)), _item(3, now - timedelta(days=3)),
             _item(4, now - timedelta(days=40))]
    monkeypatch.setattr(history_tab, "list_items", lambda *a, **kw: list(items))
    tab = _show(history_tab.HistoryTab())
    tab.reload_history()
    headers = [l.text() for l in tab.container_widget.findChildren(QLabel) if l.property("group_header")]
    assert headers == ["Today", "Yesterday", "This week", "Earlier"]


# 5.2 Rows --------------------------------------------------------------------------------

def test_history_row_compact_with_more_menu(monkeypatch):
    from app.ui.history_tab import HistoryRowWidget
    row = HistoryRowWidget(_item(1, datetime.now().astimezone()))
    assert row.height() == 64
    assert row.copy_btn.isHidden() and row.redownload_btn.isHidden() and row.delete_btn.isHidden()
    assert not row.more_btn.isHidden()
    labels = [a.text() for a in row.build_more_menu().actions() if a.text()]
    assert labels == ["Copy link", "Re-download", "Delete"]
    played = []
    monkeypatch.setattr(row, "_play_file", lambda: played.append(1))
    row.mouseDoubleClickEvent(None)
    assert played == [1]


# 5.4 Search -------------------------------------------------------------------------------

def test_search_matches_title_and_channel_with_count(monkeypatch):
    from app.ui import history_tab
    now = datetime.now().astimezone()
    items = [_item(1, now, title="Manhwa recap one"), _item(2, now, title="Other", channel="Recap Studio"),
             _item(3, now, title="Cooking")]
    monkeypatch.setattr(history_tab, "list_items", lambda *a, **kw: list(items))
    tab = _show(history_tab.HistoryTab())
    tab.search_input.setText("recap")
    _settle()  # rows added to a visible list are shown on the next event loop turn
    rows = tab.container_widget.findChildren(history_tab.HistoryRowWidget)
    assert sorted(r.item.id for r in rows if not r.isHidden() and r.parent() is not None) == [1, 2]
    assert tab.result_count.text() == "2 results"
    assert tab.search_input.isClearButtonEnabled()
    tab.search_input.setText("")
    assert not tab.result_count.isVisibleTo(tab)


# 5.5 / 5.6 Chips and Clear all -------------------------------------------------------------

def test_selected_chip_is_neutral():
    from app.ui.history_tab import FilterChip
    theme.ThemeManager.instance().apply("dark")
    chip = FilterChip("All")
    checked = chip.styleSheet().split("QPushButton:checked {", 1)[1].split("}", 1)[0]
    assert tok("accent") not in checked and tok("accent_hover") not in checked
    assert tok("text") in checked


def test_clear_all_moved_to_more_menu(monkeypatch):
    from app.ui import history_tab
    from app.ui.kit import AnimatedButton
    monkeypatch.setattr(history_tab, "list_items", lambda *a, **kw: [])
    tab = history_tab.HistoryTab()
    assert not [b for b in tab.findChildren(AnimatedButton) if b.text() == "Clear all"]
    assert [a.text() for a in tab.build_more_menu().actions()] == ["Clear all history…"]


# 5.7 Settings -----------------------------------------------------------------------------------

def test_settings_new_options_persist(settings_store, monkeypatch):
    from app.ui import settings_dialog
    monkeypatch.setattr(settings_dialog, "set_start_with_windows", lambda enabled: True)
    dlg = settings_dialog.SettingsDialog()
    assert dlg.theme_combo.findData("system") >= 0
    dlg.default_quality_combo.setCurrentIndex(dlg.default_quality_combo.findData("720p"))
    dlg.default_audio_combo.setCurrentIndex(dlg.default_audio_combo.findData("mp3"))
    for check, key in ((dlg.open_folder_check, "open_folder_when_done"), (dlg.reduce_motion_check, None),
                       (dlg.start_windows_check, "start_with_windows"), (dlg.notify_check, "notify_when_done"),
                       (dlg.auto_fetch_check, "auto_fetch_links")):
        check.setChecked(not check.isChecked())
    assert settings_store["default_video_quality"] == "720p"
    assert settings_store["default_audio_format"] == "mp3"
    assert settings_store["open_folder_when_done"] is True
    assert settings_store["animations_enabled"] is False
    assert settings_store["start_with_windows"] is True
    assert settings_store["notify_when_done"] is False
    assert settings_store["auto_fetch_links"] is False


def test_settings_still_fits_without_scrolling(settings_store):
    from PySide6.QtWidgets import QScrollArea
    from app.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog()
    dlg.show()
    assert not dlg.findChildren(QScrollArea)
    for w in (dlg.export_log_btn, dlg.credits_label, dlg.auto_fetch_check, dlg.default_audio_combo):
        top_left = w.mapTo(dlg, w.rect().topLeft())
        assert dlg.rect().contains(top_left) and dlg.rect().contains(top_left + w.rect().bottomRight())
    dlg.close()


def test_system_theme_follows_windows(monkeypatch):
    monkeypatch.setattr(theme, "windows_prefers_light", lambda: True)
    assert theme.resolve_theme("system") == "light"
    monkeypatch.setattr(theme, "windows_prefers_light", lambda: False)
    assert theme.resolve_theme("system") == "dark"
    assert theme.resolve_theme("light") == "light"


def test_auto_fetch_setting_respected(settings_store, monkeypatch):
    from app.ui.video_tab import VideoTab
    settings_store["auto_fetch_links"] = False
    tab = VideoTab()
    calls = []
    monkeypatch.setattr(tab, "fetch_url", lambda: calls.append(1))
    tab.url_input.setText(URL)
    assert calls == []


def test_default_quality_preselected(settings_store):
    from app.core.info_fetcher import VideoInfo
    from app.ui.video_tab import VideoTab
    settings_store["default_video_quality"] = "720p"
    tab = VideoTab()
    tab._on_info_fetched(VideoInfo(url=URL, title="T", channel="C", duration=1, duration_str="0:01", thumbnail_url="",
                                   qualities=[("Best available (1080p)", None), ("1080p", 1080), ("720p", 720)],
                                   filesize_approx=0))
    assert tab.quality_combo.currentData() == 720


def test_default_audio_format_preselected(settings_store):
    from app.ui.audio_tab import AudioTab
    settings_store["default_audio_format"] = "mp3"
    tab = AudioTab()
    assert tab.format_combo.currentData() == "mp3"


def test_open_folder_when_done(settings_store, monkeypatch, tmp_path):
    from app.core.info_fetcher import VideoInfo
    from app.core.jobs import DownloadJob
    from app.ui import video_tab
    settings_store["open_folder_when_done"] = True
    revealed = []
    monkeypatch.setattr(video_tab, "reveal_in_folder", lambda p: revealed.append(p) or (True, ""))
    tab = video_tab.VideoTab()
    job = DownloadJob.create(info=VideoInfo(url=URL, title="T", channel="C", duration=1, duration_str="0:01",
                                            thumbnail_url="", qualities=[], filesize_approx=0),
                             kind="video", quality_label="1080p", output_dir=str(tmp_path))
    tab._on_manager_finished(job, str(tmp_path / "v.mkv"))
    assert revealed == [str(tmp_path / "v.mkv")]


# 5.8 Tray -------------------------------------------------------------------------------------------

def test_tray_menu_and_notification_setting(settings_store, monkeypatch):
    from app.ui.main_window import MainWindow
    monkeypatch.setattr(QSystemTrayIcon, "show", lambda self: None)
    win = MainWindow()
    try:
        assert [a.text() for a in win.tray_icon.contextMenu().actions() if a.text()] == \
            ["Show", "Pause all", "Resume all", "Quit"]
        shown = []
        monkeypatch.setattr(win.tray_icon, "showMessage", lambda *a, **kw: shown.append(a))
        settings_store["notify_when_done"] = False
        win._on_download_finished_notification("T")
        assert shown == []
        win._update_tray_tooltip(46.0)
        assert "46%" in win.tray_icon.toolTip()
    finally:
        win.network_monitor.stop()
        win.close()
