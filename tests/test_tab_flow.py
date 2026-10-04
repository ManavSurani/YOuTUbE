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
    monkeypatch.setattr("app.ui.video_tab.get_download_manager", lambda: fake_mgr)
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
    monkeypatch.setattr("app.ui.audio_tab.get_download_manager", lambda: fake_mgr)
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
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda: fake_mgr)
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
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda: fake_mgr)
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



