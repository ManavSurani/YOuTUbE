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
