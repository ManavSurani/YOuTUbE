"""Plan 23 Phase 3: verified P0 UI/UX bugs."""

import time
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.core.history_db import HistoryItem
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob

LONG = "Very long title " * 25
INFO = VideoInfo(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="Title", channel="C", duration=60,
                 duration_str="1:00", thumbnail_url="", qualities=[("1080p", 1080)], filesize_approx=0)


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


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


def _item(**kw) -> HistoryItem:
    base = dict(id=1, title="Item", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", type="video",
                quality="1080p", file_path="", size_bytes=0, duration=60)
    base.update(kw)
    return HistoryItem(**base)


# 3.1 Local time + relative dates -------------------------------------------

def _utc_str(dt_local: datetime) -> str:
    return dt_local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def test_dates_are_local_and_relative():
    from app.ui.history_tab import format_date_str
    now = datetime.now().astimezone().replace(hour=15, minute=30, second=0, microsecond=0)
    today_morning = now.replace(hour=9, minute=51)
    yesterday = now - timedelta(days=1, hours=-3)  # yesterday 18:30
    older = now.replace(month=1, day=17) if now.month != 1 or now.day > 18 else now - timedelta(days=40)
    assert format_date_str(_utc_str(today_morning), now=now) == "Today, 9:51 AM"
    assert format_date_str(_utc_str(yesterday), now=now) == "Yesterday, 6:30 PM"
    expected_older = f"{older.day} {older.strftime('%b')}"
    assert format_date_str(_utc_str(older), now=now) == expected_older
    last_year = now.replace(year=now.year - 1)
    assert format_date_str(_utc_str(last_year), now=now) == f"{last_year.day} {last_year.strftime('%b')} {last_year.year}"


def test_dates_bad_input_safe():
    from app.ui.history_tab import format_date_str
    assert format_date_str("") == ""
    assert format_date_str(None) == ""
    assert format_date_str("not a date") == "not a date"


# 3.2 Elide long titles ------------------------------------------------------

def test_elided_label_keeps_full_text_and_tooltip():
    from app.ui.kit.elided_label import ElidedLabel
    lbl = _show(ElidedLabel(LONG), w=200, h=20)
    assert lbl.text() == LONG
    assert lbl.toolTip() == LONG
    assert lbl.displayed_text().endswith("…")
    assert lbl.fontMetrics().horizontalAdvance(lbl.displayed_text()) <= 200


def test_history_has_no_horizontal_scroll(monkeypatch):
    from app.ui import history_tab
    monkeypatch.setattr(history_tab, "list_items", lambda *a, **kw: [_item(id=i, title=LONG) for i in range(3)])
    tab = _show(history_tab.HistoryTab(), w=700)
    tab.refresh_items()
    _settle()
    assert tab.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    for row in tab.findChildren(history_tab.HistoryRowWidget):
        assert row.width() <= tab.scroll_area.viewport().width()


def test_queue_and_recent_titles_elide():
    from app.ui.kit.elided_label import ElidedLabel
    from app.ui.queue_widget import QueueRow
    from app.ui.recent_list import RecentRow
    job = DownloadJob.create(info=VideoInfo(**{**INFO.__dict__, "title": LONG}), kind="video", quality_label="1080p")
    assert isinstance(QueueRow(job=job).title_lbl, ElidedLabel)
    assert isinstance(RecentRow(_item(title=LONG)).title_lbl, ElidedLabel)


# 3.4 Header status only when offline ----------------------------------------

def test_header_status_hidden_online_visible_offline():
    from app.ui.header import Header
    header = _show(Header())
    assert not header.status_label.isVisibleTo(header)
    header.set_online(False)
    assert header.status_label.isVisibleTo(header)
    assert header.status_label.text() == "Offline"
    header.set_online(True)
    assert not header.status_label.isVisibleTo(header)


# 3.5 / 3.6 Errors at the input, stale card cleared ---------------------------

@pytest.mark.parametrize("tab_name", ["video_tab", "audio_tab"])
def test_invalid_link_clears_card_and_marks_input(tab_name, monkeypatch):
    import importlib
    mod = importlib.import_module(f"app.ui.{tab_name}")
    monkeypatch.setattr(mod, "find_duplicate", lambda *a, **kw: None, raising=False)
    cls = mod.VideoTab if tab_name == "video_tab" else mod.AudioTab
    tab = _show(cls())
    tab._on_info_fetched(INFO)
    assert tab.info_card.isVisibleTo(tab)

    tab.url_input.blockSignals(True)
    tab.url_input.setText("not a link")
    tab.url_input.blockSignals(False)
    tab.fetch_url()

    assert not tab.info_card.isVisibleTo(tab)
    assert tab.inline_msg.isVisibleTo(tab)
    assert "border" in tab.url_input.styleSheet()
    # Validation errors stay until the text changes
    assert not tab.inline_msg._timer.isActive()
    tab.url_input.setText("still not a link x")
    assert not tab.inline_msg.isVisibleTo(tab)
    assert "border" not in tab.url_input.styleSheet()


# 3.8 No progress bar on waiting rows -------------------------------------------

def test_waiting_row_has_hidden_progress_bar():
    from app.ui.queue_widget import QueueRow
    job = DownloadJob.create(info=INFO, kind="video", quality_label="1080p")
    row = _show(QueueRow(job=job), w=600, h=58)
    assert not row.progress_bar.isVisibleTo(row)


# 3.9 Compact update banner ----------------------------------------------------

def test_update_banner_compact_text_buttons():
    from app.core.app_updater import UpdateInfo
    from app.ui.main_window import UpdateBanner
    banner = _show(UpdateBanner(), w=880, h=44)
    banner.show_update(UpdateInfo(status="available", latest_version="9.9.9", installer_url="u", sha256="s"))
    _settle()
    assert banner.height() <= 44
    for btn in (banner.update_btn, banner.later_btn):
        assert btn.width() < 140, f"{btn.text()} stretched to {btn.width()}"
        assert "background: transparent" in banner.styleSheet().split(f"#{btn.objectName()}", 1)[1].split("}", 1)[0]


# 3.10 One left edge and no layout shift from the scrollbar ---------------------

@pytest.mark.parametrize("tab_name", ["video_tab", "audio_tab"])
def test_scrollbar_space_is_reserved(tab_name):
    import importlib
    mod = importlib.import_module(f"app.ui.{tab_name}")
    cls = mod.VideoTab if tab_name == "video_tab" else mod.AudioTab
    tab = _show(cls(), w=880, h=400)
    tab.scroll.widget().setMinimumHeight(100)
    _settle()
    right_no_bar = tab.fetch_btn.geometry().right()
    tab.scroll.widget().setMinimumHeight(3000)  # force a scrollbar
    _settle()
    assert tab.scroll.verticalScrollBar().maximum() > 0
    assert tab.fetch_btn.geometry().right() == right_no_bar


def test_section_headers_share_left_edge(monkeypatch):
    from app.ui import recent_list
    from app.ui.video_tab import VideoTab
    monkeypatch.setattr(recent_list, "list_items", lambda *a, **kw: [_item(id=1, title="A")])
    tab = _show(VideoTab())
    tab.recent_list.refresh()
    _settle()
    container = tab.scroll.widget()
    header = next(l for l in tab.recent_list.findChildren(QLabel) if l.text() == "Recently downloaded")
    x_input = tab.url_input.mapTo(container, tab.url_input.rect().topLeft()).x()
    x_header = header.mapTo(container, header.rect().topLeft()).x()
    assert x_header == x_input


# 3.11 Incomplete files ----------------------------------------------------------

def test_tiny_files_marked_incomplete(tmp_path):
    from app.ui.history_tab import HistoryRowWidget
    from app.ui.recent_list import RecentRow
    f = tmp_path / "Test [abc].mkv"
    f.write_bytes(b"1234567")
    item = _item(title="Test", file_path=str(f), size_bytes=7)
    recent = RecentRow(item)
    assert "Incomplete file" in recent.meta_lbl.text()
    assert not recent.play_btn.isVisibleTo(recent)
    hist = HistoryRowWidget(item)
    assert "Incomplete file" in hist.meta_label.text()


# 3.12 Copy fixes -------------------------------------------------------------------

def test_audio_placeholder_plain():
    from app.ui.audio_tab import AudioTab
    assert AudioTab().url_input.placeholderText() == "Paste a YouTube link to save its audio"


def test_best_original_shows_codec(tmp_path):
    from app.ui.recent_list import RecentRow
    f = tmp_path / "Song [abc].opus"
    f.write_bytes(b"x" * 4096)
    row = RecentRow(_item(type="audio", quality="Best original", file_path=str(f), size_bytes=4096))
    assert "Original (Opus)" in row.meta_lbl.text()


# 3.7 Failed group (owner approved) -----------------------------------------------

def test_failed_group_retry_all(monkeypatch):
    from unittest.mock import MagicMock
    from app.ui.queue_widget import QueueWidget
    waiting = DownloadJob.create(info=INFO, kind="video", quality_label="1080p")
    failed = DownloadJob.create(info=INFO, kind="video", quality_label="720p")
    mgr = MagicMock()
    mgr.waiting_jobs = [waiting]
    mgr.failed_jobs = [(failed, "Network error")]
    monkeypatch.setattr("app.ui.queue_widget.get_download_manager", lambda kind="video": mgr)
    widget = QueueWidget(kind="video")
    labels = [l.text() for l in widget.findChildren(QLabel)]
    assert "Up next (1)" in labels and "Failed (1)" in labels
    retry = next(b for b in widget.findChildren(QPushButton) if b.text() == "Retry all")
    retry.click()
    mgr.retry_job.assert_called_once_with(failed.job_id)
