"""Tests for Phase 3 VideoTab and AudioTab flow and state contracts."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
import pytest

from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob
from app.ui.audio_tab import AudioTab
from app.ui.video_tab import TabState, VideoTab


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class FakeManager(QObject):
    job_started = Signal(DownloadJob)
    progress = Signal(str, float, str, str, int, int)
    stage = Signal(str, str)
    job_finished = Signal(DownloadJob)
    job_failed = Signal(DownloadJob, str)
    job_cancelled = Signal(DownloadJob)

    def __init__(self):
        super().__init__()
        self.enqueued_jobs = []
        self.active_job = None

    def enqueue(self, job: DownloadJob):
        self.enqueued_jobs.append(job)
        self.active_job = job
        self.job_started.emit(job)

    def cancel_active(self):
        if self.active_job:
            self.job_cancelled.emit(self.active_job)
            self.active_job = None


def test_video_tab_start_download_preserves_downloading_state(monkeypatch):
    """Chunk 3.1: start_download should not be reset to IDLE by clearing the url input."""
    tab = VideoTab()
    fake_mgr = FakeManager()
    monkeypatch.setattr("app.ui.video_tab.get_download_manager", lambda kind="video": fake_mgr)
    tab._wire_manager()

    # Setup ready state with a valid info without triggering live fetch
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        channel="RickAstleyVEVO",
        duration=212,
        duration_str="3:32",
        thumbnail_url="",
        qualities=[("1080p", 1000000)],
        filesize_approx=1000000,
    )
    tab._on_info_fetched(info)
    assert tab._state == TabState.READY

    # Start download
    tab.start_download()

    assert tab._state == TabState.DOWNLOADING
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


def test_audio_tab_start_download_preserves_downloading_state(monkeypatch):
    """Chunk 3.1: AudioTab start_download should not be reset to IDLE by clearing url input."""
    tab = AudioTab()
    fake_mgr = FakeManager()
    monkeypatch.setattr("app.ui.audio_tab.get_download_manager", lambda kind="audio": fake_mgr)
    tab._wire_manager()

    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        channel="RickAstleyVEVO",
        duration=212,
        duration_str="3:32",
        thumbnail_url="",
        qualities=[("1080p", 1000000)],
        filesize_approx=1000000,
    )
    tab._on_info_fetched(info)
    assert tab._state == TabState.READY

    tab.start_download()

    assert tab._state == TabState.DOWNLOADING
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


@pytest.mark.parametrize("TabClass,combo_attr", [
    (VideoTab, "quality_combo"),
    (AudioTab, "format_combo"),
])
def test_tab_state_visibility_contract(TabClass, combo_attr):
    tab = TabClass()
    combo = getattr(tab, combo_attr)

    # 1. IDLE
    tab.set_state(TabState.IDLE)
    assert not combo.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)
    assert not tab.queue_btn.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)
    assert not tab.info_card.isVisibleTo(tab)
    assert not tab.progress_card.isVisibleTo(tab)
    if hasattr(tab, "hint_label"):
        assert not tab.hint_label.isVisibleTo(tab)

    # 2. FETCHING
    tab.set_state(TabState.FETCHING)
    assert not combo.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)
    assert not tab.queue_btn.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)
    assert not tab.info_card.isVisibleTo(tab)
    assert not tab.progress_card.isVisibleTo(tab)
    assert not tab.url_input.isEnabled()

    # 3. READY
    tab.set_state(TabState.READY)
    assert combo.isVisibleTo(tab)
    assert tab.download_btn.isVisibleTo(tab)
    assert not tab.queue_btn.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)
    assert tab.info_card.isVisibleTo(tab)
    assert not tab.progress_card.isVisibleTo(tab)

    # 4. DOWNLOADING (running job, no new link fetched yet)
    tab._current_info = None
    tab.set_state(TabState.DOWNLOADING)
    assert not combo.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)
    assert tab.queue_btn.isVisibleTo(tab)
    assert not tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.info_card.isVisibleTo(tab)
    assert tab.progress_card.isVisibleTo(tab)

    # 5. DOWNLOADING (new link fetched)
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=newlink12345",
        title="New Video",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    tab._current_info = info
    tab._apply_state_visibility(TabState.DOWNLOADING)
    assert combo.isVisibleTo(tab)
    assert tab.info_card.isVisibleTo(tab)
    assert tab.queue_btn.isVisibleTo(tab)
    assert tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


@pytest.mark.parametrize("TabClass,kind", [
    (VideoTab, "video"),
    (AudioTab, "audio"),
])
def test_tab_finish_clears_inputs_and_returns_to_idle(TabClass, kind, monkeypatch):
    tab = TabClass()
    fake_mgr = FakeManager()
    module_name = "video_tab" if TabClass is VideoTab else "audio_tab"
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda kind=None: fake_mgr)
    tab._wire_manager()

    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Rick Astley",
        channel="RickAstleyVEVO",
        duration=212,
        duration_str="3:32",
        thumbnail_url="",
        qualities=[("1080p", 1000000)],
        filesize_approx=1000000,
    )
    tab._on_info_fetched(info)
    job = DownloadJob.create(
        info=info,
        kind=kind,
        quality_label="1080p" if kind == "video" else "best",
        output_dir="C:/Downloads",
    )
    tab.set_state(TabState.DOWNLOADING)

    # Simulate finish
    tab._on_manager_finished(job, "C:/Downloads/video.mp4")

    # Assert Idle state and inputs cleared
    assert tab._state == TabState.IDLE
    assert tab.url_input.text() == ""
    assert tab._current_info is None
    assert not tab.info_card.isVisibleTo(tab)
    assert not tab.progress_card.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)
    assert tab.url_input.isVisibleTo(tab)
    assert tab.fetch_btn.isVisibleTo(tab)


@pytest.mark.parametrize("TabClass,module_name", [
    (VideoTab, "video_tab"),
    (AudioTab, "audio_tab"),
])
def test_thumbnail_saved_before_enqueue(TabClass, module_name, monkeypatch):
    tab = TabClass()
    fake_mgr = FakeManager()
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda kind=None: fake_mgr)
    tab._wire_manager()

    call_order = []

    def mock_save_thumb(vid, data):
        call_order.append(("save_thumbnail", vid, data))
        return "thumb_path"

    def mock_enqueue(job):
        call_order.append(("enqueue", job))

    monkeypatch.setattr(f"app.ui.{module_name}.save_thumbnail", mock_save_thumb)
    fake_mgr.enqueue = mock_enqueue

    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Video",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    tab._on_info_fetched(info)
    tab.info_card.thumb_bytes = b"fake_thumb_bytes"

    tab.start_download()

    assert len(call_order) == 2
    assert call_order[0][0] == "save_thumbnail"
    assert call_order[0][1] == "dQw4w9WgXcQ"
    assert call_order[0][2] == b"fake_thumb_bytes"
    assert call_order[1][0] == "enqueue"


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_return_pressed_triggers_fetch(TabClass, monkeypatch):
    tab = TabClass()
    fetch_called = False

    def mock_fetch():
        nonlocal fetch_called
        fetch_called = True

    tab.fetch_url = mock_fetch
    tab.url_input.returnPressed.emit()
    assert fetch_called is True


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_reset_messages_clears_inline_message(TabClass):
    tab = TabClass()
    tab.inline_msg.show_error("Test Error")
    assert tab.inline_msg.isVisibleTo(tab)

    tab.reset_messages()
    assert not tab.inline_msg.isVisibleTo(tab)


def test_audio_job_quality_label_short():
    tab = AudioTab()
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Audio",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[],
        filesize_approx=1000,
    )
    tab._current_info = info

    # Default option: "Best original (Opus/M4A)"
    job = tab._build_job()
    assert job is not None
    assert job.quality_label == "Best original"

    # Second option: "MP3 (320 kbps)"
    tab.format_combo.setCurrentIndex(1)
    job = tab._build_job()
    assert job is not None
    assert job.quality_label == "MP3"


def test_audio_hint_visibility_idle_and_ready():
    tab = AudioTab()
    tab.set_state(TabState.IDLE)
    assert not tab.hint_label.isVisibleTo(tab)

    tab.set_state(TabState.READY)
    assert tab.hint_label.isVisibleTo(tab)
    assert tab.hint_label.text() == "Best original keeps the YouTube audio as it is."


def test_see_all_clicked_switches_to_history_with_filter():
    from app.ui.main_window import MainWindow

    with patch("app.ui.main_window.NetworkMonitor.start"), patch.object(MainWindow, "_check_for_updates"):
        win = MainWindow()
        try:
            # Emitting see_all_clicked on audio tab
            win.audio_tab.recent_list.see_all_clicked.emit("audio")
            assert win.stacked_widget.currentIndex() == 2
            assert win.header._current_tab == 2
            assert win.history_tab.chip_audio.isChecked()
            assert win.history_tab._current_filter == "audio"

            # Emitting see_all_clicked on video tab
            win.video_tab.recent_list.see_all_clicked.emit("video")
            assert win.stacked_widget.currentIndex() == 2
            assert win.header._current_tab == 2
            assert win.history_tab.chip_video.isChecked()
            assert win.history_tab._current_filter == "video"
        finally:
            if hasattr(win, "network_monitor"):
                win.network_monitor.stop()
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()


def test_tab_changed_resets_messages_on_video_and_audio():
    from app.ui.main_window import MainWindow

    with patch("app.ui.main_window.NetworkMonitor.start"), patch.object(MainWindow, "_check_for_updates"):
        win = MainWindow()
        try:
            win.video_tab.inline_msg.show_error("Video Error")
            assert win.video_tab.inline_msg.isVisibleTo(win.video_tab)

            win.header.select_tab(1)
            assert not win.video_tab.inline_msg.isVisibleTo(win.video_tab)

            win.audio_tab.inline_msg.show_error("Audio Error")
            assert win.audio_tab.inline_msg.isVisibleTo(win.audio_tab)

            win.header.select_tab(0)
            assert not win.audio_tab.inline_msg.isVisibleTo(win.audio_tab)
        finally:
            if hasattr(win, "network_monitor"):
                win.network_monitor.stop()
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()


# --- Chunk A.4 Tests: Persist Thumbnail Before Enqueueing Job ---

def _setup_tab_for_thumb_test(TabClass, module_name, monkeypatch, thumb_bytes):
    tab = TabClass()
    fake_mgr = FakeManager()
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda kind=None: fake_mgr)
    tab._wire_manager()

    call_order = []

    def mock_save_thumb(vid, data):
        call_order.append(("save_thumbnail", vid, data))
        return "thumb_path"

    def mock_enqueue(job):
        call_order.append(("enqueue", job))

    monkeypatch.setattr(f"app.ui.{module_name}.save_thumbnail", mock_save_thumb)
    fake_mgr.enqueue = mock_enqueue

    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Video",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    tab._on_info_fetched(info)
    tab.info_card.thumb_bytes = thumb_bytes
    return tab, call_order


def test_video_tab_start_download_saves_thumbnail_before_enqueue(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(VideoTab, "video_tab", monkeypatch, b"video_thumb_bytes")
    tab.start_download()

    assert len(call_order) == 2
    assert call_order[0] == ("save_thumbnail", "dQw4w9WgXcQ", b"video_thumb_bytes")
    assert call_order[1][0] == "enqueue"


def test_video_tab_add_to_queue_saves_thumbnail_before_enqueue(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(VideoTab, "video_tab", monkeypatch, b"video_queue_thumb_bytes")
    tab.add_to_queue()

    assert len(call_order) == 2
    assert call_order[0] == ("save_thumbnail", "dQw4w9WgXcQ", b"video_queue_thumb_bytes")
    assert call_order[1][0] == "enqueue"


def test_audio_tab_start_download_saves_thumbnail_before_enqueue(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(AudioTab, "audio_tab", monkeypatch, b"audio_thumb_bytes")
    tab.start_download()

    assert len(call_order) == 2
    assert call_order[0] == ("save_thumbnail", "dQw4w9WgXcQ", b"audio_thumb_bytes")
    assert call_order[1][0] == "enqueue"


def test_audio_tab_add_to_queue_saves_thumbnail_before_enqueue(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(AudioTab, "audio_tab", monkeypatch, b"audio_queue_thumb_bytes")
    tab.add_to_queue()

    assert len(call_order) == 2
    assert call_order[0] == ("save_thumbnail", "dQw4w9WgXcQ", b"audio_queue_thumb_bytes")
    assert call_order[1][0] == "enqueue"


def test_video_tab_empty_thumbnail_bytes_does_not_call_save_thumbnail(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(VideoTab, "video_tab", monkeypatch, b"")
    tab.start_download()

    assert len(call_order) == 1
    assert call_order[0][0] == "enqueue"


def test_audio_tab_empty_thumbnail_bytes_does_not_call_save_thumbnail(monkeypatch):
    tab, call_order = _setup_tab_for_thumb_test(AudioTab, "audio_tab", monkeypatch, b"")
    tab.start_download()

    assert len(call_order) == 1
    assert call_order[0][0] == "enqueue"






