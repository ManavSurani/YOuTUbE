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
