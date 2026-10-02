"""Tests for VideoTab and AudioTab state machines, widget enablement, and RecentList."""

from PySide6.QtWidgets import QApplication
import pytest

from app.core.info_fetcher import VideoInfo
from app.ui.audio_tab import AudioTab
from app.ui.recent_list import RecentList
from app.ui.video_tab import TabState, VideoTab


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_video_tab_state_transitions():
    tab = VideoTab()
    tab.show()

    # 1. Initial IDLE state
    assert tab._state == TabState.IDLE
    assert tab.url_input.isEnabled()
    assert not tab.quality_combo.isEnabled()
    assert not tab.download_btn.isEnabled()
    assert tab.cancel_btn.isHidden()

    # 2. Transition to FETCHING
    tab.set_state(TabState.FETCHING)
    assert not tab.url_input.isEnabled()
    assert not tab.download_btn.isEnabled()

    # 3. Transition to READY
    tab.set_state(TabState.READY)
    assert tab.url_input.isEnabled()
    assert tab.quality_combo.isEnabled()
    assert tab.download_btn.isEnabled()
    assert tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isHidden()

    # 4. Transition to DOWNLOADING
    tab.set_state(TabState.DOWNLOADING)
    assert tab.url_input.isEnabled()
    assert tab.download_btn.isHidden()
    assert not tab.queue_btn.isHidden()
    assert not tab.cancel_btn.isHidden()

    # 5. Transition to OFFLINE and restore
    tab.set_online(False)
    assert tab._state == TabState.OFFLINE
    assert not tab.url_input.isEnabled()
    assert not tab.download_btn.isEnabled()

    # Reconnecting restores DOWNLOADING
    tab.set_online(True)
    assert tab._state == TabState.DOWNLOADING
    assert not tab.cancel_btn.isHidden()


def test_audio_tab_state_transitions():
    tab = AudioTab()
    tab.show()

    # 1. Initial IDLE state
    assert tab._state == TabState.IDLE
    assert not tab.format_combo.isEnabled()
    assert not tab.download_btn.isEnabled()

    # 2. Transition to READY
    tab.set_state(TabState.READY)
    assert tab.format_combo.isEnabled()
    assert tab.download_btn.isEnabled()

    # 3. Transition to OFFLINE and restore
    tab.set_online(False)
    assert not tab.format_combo.isEnabled()
    assert not tab.download_btn.isEnabled()

    tab.set_online(True)
    assert tab.format_combo.isEnabled()
    assert tab.download_btn.isEnabled()


def test_empty_download_shows_inline_error():
    tab = VideoTab()
    tab.show()
    tab.url_input.setText("")
    tab.start_download()

    assert not tab.inline_msg.isHidden()
    assert "valid YouTube link" in tab.inline_msg.text()


def test_recent_list_filter(tmp_path):
    recent_video = RecentList(kind="video")
    recent_audio = RecentList(kind="audio")
    assert recent_video.kind == "video"
    assert recent_audio.kind == "audio"
