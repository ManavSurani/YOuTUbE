"""Tests for VideoTab and AudioTab state machines, widget enablement, and RecentList."""

from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
import pytest

from app.core.download_manager import get_download_manager
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


# --- Chunk A.1 Tests: Sticky Downloading Look & Enablement Table (Video Tab) ---

@pytest.mark.parametrize(
    "state_case,expected_queue_vis,expected_queue_en,expected_cancel_vis,expected_dl_vis",
    [
        ("running_empty", True, True, True, False),
        ("running_fetching", True, False, True, False),
        ("running_ready", True, True, True, False),
        ("running_offline", True, False, True, False),
        ("no_job", False, False, False, True),
    ],
)
def test_video_tab_queue_btn_enablement_by_state(
    state_case, expected_queue_vis, expected_queue_en, expected_cancel_vis, expected_dl_vis, monkeypatch
):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()

    if state_case == "running_empty":
        job = MagicMock(kind="video", job_id="j1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab._current_info = None
        tab.url_input.setText("")
        tab.set_state(TabState.DOWNLOADING)
    elif state_case == "running_fetching":
        job = MagicMock(kind="video", job_id="j1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab.set_state(TabState.FETCHING)
    elif state_case == "running_ready":
        job = MagicMock(kind="video", job_id="j1")
        monkeypatch.setattr(mgr, "_active_job", job)
        info = VideoInfo(
            url="https://youtube.com/watch?v=1",
            title="Test",
            channel="Chan",
            duration=60,
            duration_str="1:00",
            thumbnail_url="",
            qualities=[("1080p", 1080)],
            filesize_approx=1024,
        )
        tab._current_info = info
        tab.set_state(TabState.READY)
    elif state_case == "running_offline":
        job = MagicMock(kind="video", job_id="j1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab.set_online(False)
    elif state_case == "no_job":
        monkeypatch.setattr(mgr, "_active_job", None)
        info = VideoInfo(
            url="https://youtube.com/watch?v=1",
            title="Test",
            channel="Chan",
            duration=60,
            duration_str="1:00",
            thumbnail_url="",
            qualities=[("1080p", 1080)],
            filesize_approx=1024,
        )
        tab._current_info = info
        tab.set_state(TabState.READY)

    assert tab.queue_btn.isVisibleTo(tab) == expected_queue_vis
    if expected_queue_vis:
        assert tab.queue_btn.isEnabled() == expected_queue_en
    assert tab.cancel_btn.isVisibleTo(tab) == expected_cancel_vis
    assert tab.download_btn.isVisibleTo(tab) == expected_dl_vis


def test_video_tab_queue_btn_enabled_when_downloading_empty_box(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="j1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab._current_info = None
    tab.url_input.setText("")
    tab.set_state(TabState.DOWNLOADING)

    assert tab.queue_btn.isVisibleTo(tab)
    assert tab.queue_btn.isEnabled()


def test_video_tab_pasting_link_during_download_keeps_cancel(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="j1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)
    assert tab.cancel_btn.isVisibleTo(tab)

    tab.set_state(TabState.FETCHING)
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


def test_video_tab_info_fetched_during_download_keeps_cancel(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="j1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)

    info = VideoInfo(
        url="https://youtube.com/watch?v=new",
        title="New Video",
        channel="Chan",
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=2048,
    )
    tab._on_info_fetched(info)

    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)
    assert tab.queue_btn.isVisibleTo(tab)
    assert tab.queue_btn.isEnabled()


def test_video_tab_clearing_link_during_download_keeps_cancel(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="j1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)
    assert tab.cancel_btn.isVisibleTo(tab)

    tab.url_input.setText("")
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


def test_video_tab_job_running_kind_isolation(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    if hasattr(tab, "_job_running"):
        assert tab._job_running() is False

    info = VideoInfo(
        url="https://youtube.com/watch?v=vid",
        title="Video",
        channel="Chan",
        duration=60,
        duration_str="1:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=1024,
    )
    tab._current_info = info
    tab.set_state(TabState.READY)

    assert tab.download_btn.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)


def test_video_tab_cancel_download_restores_correct_state(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="j1")
    monkeypatch.setattr(mgr, "_active_job", job)

    info = VideoInfo(
        url="https://youtube.com/watch?v=fetch",
        title="Fetched",
        channel="Chan",
        duration=60,
        duration_str="1:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=1024,
    )
    tab._current_info = info
    tab.cancel_download()
    assert tab._state == TabState.READY

    tab._current_info = None
    tab.cancel_download()
    assert tab._state == TabState.IDLE


# --- Chunk A.3 Tests: Sticky Downloading Look & Enablement Table (Audio Tab) ---

@pytest.mark.parametrize(
    "state_case,expected_queue_vis,expected_queue_en,expected_cancel_vis,expected_dl_vis",
    [
        ("running_empty", True, True, True, False),
        ("running_fetching", True, False, True, False),
        ("running_ready", True, True, True, False),
        ("running_offline", True, False, True, False),
        ("no_job", False, False, False, True),
    ],
)
def test_audio_tab_queue_btn_enablement_by_state(
    state_case, expected_queue_vis, expected_queue_en, expected_cancel_vis, expected_dl_vis, monkeypatch
):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()

    if state_case == "running_empty":
        job = MagicMock(kind="audio", job_id="a1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab._current_info = None
        tab.url_input.setText("")
        tab.set_state(TabState.DOWNLOADING)
    elif state_case == "running_fetching":
        job = MagicMock(kind="audio", job_id="a1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab.set_state(TabState.FETCHING)
    elif state_case == "running_ready":
        job = MagicMock(kind="audio", job_id="a1")
        monkeypatch.setattr(mgr, "_active_job", job)
        info = VideoInfo(
            url="https://youtube.com/watch?v=1",
            title="Test",
            channel="Chan",
            duration=60,
            duration_str="1:00",
            thumbnail_url="",
            qualities=[("1080p", 1080)],
            filesize_approx=1024,
        )
        tab._current_info = info
        tab.set_state(TabState.READY)
    elif state_case == "running_offline":
        job = MagicMock(kind="audio", job_id="a1")
        monkeypatch.setattr(mgr, "_active_job", job)
        tab.set_online(False)
    elif state_case == "no_job":
        monkeypatch.setattr(mgr, "_active_job", None)
        info = VideoInfo(
            url="https://youtube.com/watch?v=1",
            title="Test",
            channel="Chan",
            duration=60,
            duration_str="1:00",
            thumbnail_url="",
            qualities=[("1080p", 1080)],
            filesize_approx=1024,
        )
        tab._current_info = info
        tab.set_state(TabState.READY)

    assert tab.queue_btn.isVisibleTo(tab) == expected_queue_vis
    if expected_queue_vis:
        assert tab.queue_btn.isEnabled() == expected_queue_en
    assert tab.cancel_btn.isVisibleTo(tab) == expected_cancel_vis
    assert tab.download_btn.isVisibleTo(tab) == expected_dl_vis


def test_audio_tab_queue_btn_enabled_when_downloading_empty_box(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab._current_info = None
    tab.url_input.setText("")
    tab.set_state(TabState.DOWNLOADING)

    assert tab.queue_btn.isVisibleTo(tab)
    assert tab.queue_btn.isEnabled()


def test_audio_tab_pasting_link_during_download_keeps_cancel(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)
    assert tab.cancel_btn.isVisibleTo(tab)

    tab.set_state(TabState.FETCHING)
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


def test_audio_tab_info_fetched_during_download_keeps_cancel(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)

    info = VideoInfo(
        url="https://youtube.com/watch?v=new",
        title="New Audio",
        channel="Chan",
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=2048,
    )
    tab._on_info_fetched(info)

    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)
    assert tab.queue_btn.isVisibleTo(tab)
    assert tab.queue_btn.isEnabled()


def test_audio_tab_clearing_link_during_download_keeps_cancel(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    tab.set_state(TabState.DOWNLOADING)
    assert tab.cancel_btn.isVisibleTo(tab)

    tab.url_input.setText("")
    assert tab.cancel_btn.isVisibleTo(tab)
    assert not tab.download_btn.isVisibleTo(tab)


def test_audio_tab_job_running_kind_isolation(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="video", job_id="v1")
    monkeypatch.setattr(mgr, "_active_job", job)

    if hasattr(tab, "_job_running"):
        assert tab._job_running() is False

    info = VideoInfo(
        url="https://youtube.com/watch?v=vid",
        title="Audio",
        channel="Chan",
        duration=60,
        duration_str="1:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=1024,
    )
    tab._current_info = info
    tab.set_state(TabState.READY)

    assert tab.download_btn.isVisibleTo(tab)
    assert not tab.cancel_btn.isVisibleTo(tab)


def test_audio_tab_cancel_download_restores_correct_state(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager()
    job = MagicMock(kind="audio", job_id="a1")
    monkeypatch.setattr(mgr, "_active_job", job)

    info = VideoInfo(
        url="https://youtube.com/watch?v=fetch",
        title="Fetched",
        channel="Chan",
        duration=60,
        duration_str="1:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=1024,
    )
    tab._current_info = info
    tab.cancel_download()
    assert tab._state == TabState.READY

    tab._current_info = None
    tab.cancel_download()
    assert tab._state == TabState.IDLE


