"""Plan 23 Phase 4: core flow upgrades."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from app.core.info_fetcher import VideoInfo, build_quality_list, build_quality_sizes
from app.core.jobs import DownloadJob

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def no_dup(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.find_duplicate", lambda *a, **kw: None)
    monkeypatch.setattr("app.ui.audio_tab.find_duplicate", lambda *a, **kw: None)
    monkeypatch.setattr(QSystemTrayIcon, "show", lambda self: None)


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


def _sample_formats():
    return json.loads((ROOT / "tests" / "sample_info.json").read_text(encoding="utf-8"))["formats"]


def _info(**kw) -> VideoInfo:
    base = dict(url=URL, title="Title", channel="C", duration=60, duration_str="1:00", thumbnail_url="",
                qualities=[("Best available (1080p)", None), ("1080p", 1080), ("720p", 720)], filesize_approx=0)
    base.update(kw)
    return VideoInfo(**base)


# 4.1 Size per quality -------------------------------------------------------------

def test_quality_sizes_from_formats():
    formats = _sample_formats()
    heights = [h for _, h in build_quality_list(formats)]
    sizes = build_quality_sizes(formats, heights)
    assert sizes, "expected at least one size"
    assert all(isinstance(v, int) and v > 0 for v in sizes.values())
    known = [h for h in heights if h is not None and h in sizes]
    # A lower height is never bigger than a higher one
    for lo, hi in zip(sorted(known), sorted(known)[1:]):
        assert sizes[lo] <= sizes[hi]


def test_quality_sizes_missing_data_safe():
    assert build_quality_sizes([], [None, 1080]) == {}
    assert build_quality_sizes([{"vcodec": "avc1", "acodec": "none", "height": 720}], [720]) == {}


def test_dropdown_shows_size_but_job_keeps_clean_label():
    from app.ui.video_tab import VideoTab
    tab = _show(VideoTab())
    tab.url_input.blockSignals(True)
    tab.url_input.setText(URL)
    tab.url_input.blockSignals(False)
    tab._on_info_fetched(_info(quality_sizes={None: 723_600_000, 1080: 723_600_000, 720: 410_000_000}))
    texts = [tab.quality_combo.itemText(i) for i in range(tab.quality_combo.count())]
    assert texts[1] == "1080p · ≈ 690.1 MB"
    assert texts[2] == "720p · ≈ 391.0 MB"
    tab.quality_combo.setCurrentIndex(1)
    job = tab._build_job()
    assert job.quality_label == "1080p"


def test_dropdown_without_sizes_unchanged():
    from app.ui.video_tab import VideoTab
    tab = _show(VideoTab())
    tab._on_info_fetched(_info())
    assert tab.quality_combo.itemText(1) == "1080p"


# 4.2 Info card -------------------------------------------------------------------------

def test_info_card_layout():
    from app.ui.video_tab import VideoTab
    tab = _show(VideoTab())
    tab._on_info_fetched(_info(title="A title " * 30))
    card = tab.info_card
    assert card.thumb_label.size().width() == 160 and card.thumb_label.size().height() == 90
    assert card.thumb_label.pixmap() is not None and not card.thumb_label.pixmap().isNull()  # placeholder
    lines = card.title_label.height() / card.title_label.fontMetrics().lineSpacing()
    assert lines <= 2.2
    assert "Saves to" in card.dest_label.text()


def test_info_card_change_folder_signal():
    from app.ui.video_tab import MediaInfoCard
    card = MediaInfoCard()
    seen = []
    card.change_folder_requested.connect(lambda: seen.append(1))
    card.dest_label.linkActivated.emit("change")
    assert seen == [1]


# 4.4 Pause / Resume -------------------------------------------------------------------------

def test_manager_pause_resume_uses_offline_path(monkeypatch):
    from app.core.download_manager import DownloadManager
    mgr = DownloadManager(kind="video")
    worker = MagicMock()
    mgr._active_job = MagicMock(job_id="j1")
    mgr._worker = worker
    resumed = []
    monkeypatch.setattr(mgr, "_resume_active_job", lambda: resumed.append(1))

    assert mgr.pause_active() is True
    worker.pause.assert_called_once()
    assert mgr.is_paused
    mgr.set_online(False)
    mgr.set_online(True)  # network coming back must not resume a user pause
    assert resumed == []
    assert mgr.resume_active() is True
    assert resumed == [1]
    assert not mgr.is_paused


def test_progress_card_pause_button_toggles():
    from app.ui.kit import ProgressCard
    card = _show(ProgressCard(), w=600, h=120)
    card.bind_job(DownloadJob.create(info=_info(), kind="video", quality_label="1080p"))
    seen = []
    card.pause_toggled.connect(lambda: seen.append(1))
    assert card.pause_btn.isVisibleTo(card)
    card.pause_btn.click()
    assert seen == [1]
    card.set_paused(True)
    assert card.pause_btn.icon_name == "play"
    card.set_paused(False)
    assert card.pause_btn.icon_name == "pause"


# 4.5 Done state -------------------------------------------------------------------------------

def test_done_state_offers_open_and_folder(tmp_path, monkeypatch):
    from app.ui.kit import progress_card
    f = tmp_path / "v.mkv"
    f.write_bytes(b"x" * 2048)
    opened, revealed = [], []
    monkeypatch.setattr(progress_card, "open_file", lambda p: opened.append(p) or (True, ""))
    monkeypatch.setattr(progress_card, "reveal_in_folder", lambda p: revealed.append(p) or (True, ""))
    card = _show(progress_card.ProgressCard(), w=600, h=120)
    card.show_done(out_dir=str(tmp_path), final_path=str(f))
    assert card.open_btn.isVisibleTo(card) and card.folder_btn.isVisibleTo(card)
    assert not card.pause_btn.isVisibleTo(card)
    assert card._collapse_timer.interval() >= 4000
    card.open_btn.click()
    card.folder_btn.click()
    assert opened == [str(f)] and revealed == [str(f)]


# 4.6 Clipboard detect --------------------------------------------------------------------------

def test_clipboard_chip_offers_new_link_once():
    from app.ui.video_tab import VideoTab
    tab = _show(VideoTab())
    tab.offer_clipboard_link(URL)
    assert tab.clip_chip.isVisibleTo(tab)
    tab.clip_chip.click()
    assert tab.url_input.text() == URL
    assert not tab.clip_chip.isVisibleTo(tab)
    tab.offer_clipboard_link(URL)  # same link again: no chip
    assert not tab.clip_chip.isVisibleTo(tab)
    tab.offer_clipboard_link("hello world")  # not a link: no chip
    assert not tab.clip_chip.isVisibleTo(tab)


def test_window_activation_checks_clipboard(monkeypatch):
    from app.ui.main_window import MainWindow
    win = MainWindow()
    seen = []
    monkeypatch.setattr(win.video_tab, "offer_clipboard_link", lambda text: seen.append(text))
    QApplication.clipboard().setText(URL)
    win._check_clipboard()
    assert seen == [URL]
    win.network_monitor.stop()
    win.close()


# 4.7 Auto-fetch on paste (already present) ---------------------------------------------------

def test_pasting_link_fetches(monkeypatch):
    from app.ui.video_tab import VideoTab
    tab = VideoTab()
    calls = []
    monkeypatch.setattr(tab, "fetch_url", lambda: calls.append(1))
    tab.url_input.setText(URL)
    assert calls == [1]


# 4.8 Drag & drop ------------------------------------------------------------------------------

def test_drop_link_fills_current_tab(monkeypatch):
    from app.ui.main_window import MainWindow
    win = MainWindow()
    calls = []
    monkeypatch.setattr(win.video_tab, "fetch_url", lambda: calls.append(1))
    mime = QMimeData()
    mime.setText(URL)
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert win.acceptDrops()
    win.dropEvent(event)
    assert win.video_tab.url_input.text() == URL
    win.network_monitor.stop()
    win.close()


# 4.9 Shortcuts ----------------------------------------------------------------------------------

def test_shortcuts_registered():
    from PySide6.QtGui import QShortcut
    from app.ui.main_window import MainWindow
    win = MainWindow()
    keys = {s.key().toString() for s in win.findChildren(QShortcut)}
    for k in ("Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+F", "Ctrl+,", "Ctrl+V", "Esc", "Space"):
        assert k in keys, k
    tab_shortcut = next(s for s in win.findChildren(QShortcut) if s.key().toString() == "Ctrl+3")
    tab_shortcut.activated.emit()
    assert win.header._current_tab == 2
    win.network_monitor.stop()
    win.close()


def test_enter_downloads_when_ready(monkeypatch):
    from app.ui.video_tab import VideoTab
    tab = _show(VideoTab())
    tab.url_input.blockSignals(True)
    tab.url_input.setText(URL)
    tab.url_input.blockSignals(False)
    tab._last_fetched_url = URL
    tab._on_info_fetched(_info())
    started = []
    monkeypatch.setattr(tab, "start_download", lambda: started.append(1))
    tab.url_input.returnPressed.emit()
    assert started == [1]


# 4.10 Thumbnail from bytes ----------------------------------------------------------------------

def test_progress_card_uses_job_thumbnail_bytes():
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage
    from app.ui.kit import ProgressCard
    img = QImage(64, 36, QImage.Format.Format_RGB32)
    img.fill(QColor(0, 200, 0))
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    job = DownloadJob.create(info=_info(), kind="video", quality_label="1080p", thumbnail_bytes=bytes(data),
                             video_id="no_cache_vid")
    card = ProgressCard()
    card.bind_job(job)
    px = card.thumb.pixmap().toImage().pixelColor(24, 13)
    assert px.green() > 150 and px.red() < 80


def test_quality_sizes_follow_ytdlp_choice_not_bitrate():
    """yt-dlp lists formats worst -> best and downloads the last match (e.g. AV1 over a bigger VP9)."""
    formats = [
        {"format_id": "251", "vcodec": "none", "acodec": "opus", "abr": 130, "filesize": 3_433_755},
        {"format_id": "313", "vcodec": "vp9", "acodec": "none", "height": 2160, "tbr": 13466, "filesize": 358_608_461},
        {"format_id": "401", "vcodec": "av01.0.12M.08", "acodec": "none", "height": 2160, "tbr": 9025, "filesize": 240_334_643},
    ]
    sizes = build_quality_sizes(formats, [None, 2160])
    assert sizes[None] == sizes[2160] == 240_334_643 + 3_433_755  # what yt-dlp really downloads


def test_quality_size_skipped_when_chosen_format_has_no_size():
    formats = [
        {"format_id": "251", "vcodec": "none", "acodec": "opus", "filesize": 3_000_000},
        {"format_id": "313", "vcodec": "vp9", "acodec": "none", "height": 2160, "filesize": 358_000_000},
        {"format_id": "625", "vcodec": "vp9", "acodec": "none", "height": 2160},  # chosen, but no size
    ]
    assert build_quality_sizes(formats, [2160]) == {}
