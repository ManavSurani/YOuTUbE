"""Tests for VideoTab and AudioTab state machines, widget enablement, and RecentList."""

from unittest.mock import MagicMock
from PySide6.QtCore import QObject, Signal
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
    mgr = get_download_manager("video")

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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("video")
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
    mgr = get_download_manager("audio")

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
    mgr = get_download_manager("audio")
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
    mgr = get_download_manager("audio")
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
    mgr = get_download_manager("audio")
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
    mgr = get_download_manager("audio")
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
    mgr = get_download_manager("audio")
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
    mgr = get_download_manager("audio")
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


# --- Phase 4 Tests: Stuck State and Queue Management (Video Tab) ---

class DummyWorker(QObject):
    fetched = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, url, parent=None):
        super().__init__(parent)

    def start(self):
        pass


def make_info(vid):
    return VideoInfo(
        url=f"https://www.youtube.com/watch?v={vid}",
        title="second",
        channel="c",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("Best available", 0)],
        filesize_approx=0,
    )


# T1
def test_new_link_fetched_during_download_enables_add_to_queue(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="video", job_id="j1"))
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=BBBBBBBBBBB")
    assert tab._state == TabState.FETCHING  # the real sequence
    tab._on_info_fetched(make_info("BBBBBBBBBBB"))
    assert tab._state == TabState.DOWNLOADING  # fails today: stays FETCHING
    assert tab.url_input.isEnabled()  # fails today
    assert tab.queue_btn.isEnabled()  # fails today
    assert tab.cancel_btn.isVisibleTo(tab) and not tab.download_btn.isVisibleTo(tab)
    enqueued = []
    monkeypatch.setattr(mgr, "enqueue", lambda job, **k: enqueued.append(job))
    tab.queue_btn.click()
    assert len(enqueued) == 1  # fails today: 0


# T2
def test_fetch_fails_during_running_download_returns_to_downloading(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="video", job_id="j1"))
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=FAILVID1234")
    assert tab._state == TabState.FETCHING
    tab._on_info_failed("Video unavailable")
    assert tab._state == TabState.DOWNLOADING  # fails today: stays FETCHING
    assert tab.url_input.isEnabled()  # fails today
    assert not tab.inline_msg.isHidden()
    assert "Video unavailable" in tab.inline_msg.text()
    assert not tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab) and not tab.download_btn.isVisibleTo(tab)


# T3
def test_fetch_result_stops_fetch_button_spinner(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="video", job_id="j1"))
    tab.set_state(TabState.DOWNLOADING)

    # 1. Fetch finishes while download is running
    tab.url_input.setText("https://www.youtube.com/watch?v=SPINNERVID1")
    assert tab.fetch_btn._is_loading is True
    tab._on_info_fetched(make_info("SPINNERVID1"))
    assert tab.fetch_btn._is_loading is False  # fails today: stays FETCHING
    assert not tab.fetch_btn._spinner_timer.isActive()

    # 2. Fetch fails while download is running
    tab.url_input.setText("https://www.youtube.com/watch?v=SPINNERVID2")
    assert tab.fetch_btn._is_loading is True
    tab._on_info_failed("Fetch error")
    assert tab.fetch_btn._is_loading is False  # fails today: stays FETCHING
    assert not tab.fetch_btn._spinner_timer.isActive()


# T4 (guard)
def test_cached_link_during_download_goes_to_downloading_with_queue_enabled(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="video", job_id="j1"))
    tab.set_state(TabState.DOWNLOADING)

    cached_url = "https://www.youtube.com/watch?v=CACHEDLINK1"
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE[cached_url] = make_info("CACHEDLINK1")

    tab.url_input.setText(cached_url)
    assert tab._state == TabState.DOWNLOADING
    assert tab.url_input.isEnabled()
    assert tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab)


# T5
def test_pending_link_survives_running_download_finished(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    active_job = MagicMock(kind="video", job_id="j1", output_dir="C:/Downloads", title="first")
    monkeypatch.setattr(mgr, "_active_job", active_job)
    tab.set_state(TabState.DOWNLOADING)

    tab.url_input.setText("https://www.youtube.com/watch?v=BBBBBBBBBBB")
    tab._on_info_fetched(make_info("BBBBBBBBBBB"))

    # Now running download finishes, no waiting jobs
    monkeypatch.setattr(mgr, "_active_job", None)
    monkeypatch.setattr(mgr, "_waiting_queue", [])
    tab._on_manager_finished(active_job, "C:/Downloads/first.mp4")

    # Link B and its info card must survive
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=BBBBBBBBBBB"  # fails today: cleared
    assert tab._current_info is not None  # fails today: None
    assert tab.info_card.isVisibleTo(tab)  # fails today: hidden
    assert tab._state == TabState.READY  # fails today: IDLE


# T6
def test_pending_link_survives_running_download_failed_and_cancelled(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")

    # Case A: FAILED
    active_job = MagicMock(kind="video", job_id="j1", output_dir="C:/Downloads", title="first")
    monkeypatch.setattr(mgr, "_active_job", active_job)
    monkeypatch.setattr(mgr, "_waiting_queue", [])
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=BBBBBBBBBBB")
    tab._on_info_fetched(make_info("BBBBBBBBBBB"))

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_failed(active_job, "Download error")
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=BBBBBBBBBBB"  # fails today: cleared
    assert tab._current_info is not None  # fails today: None
    assert tab.info_card.isVisibleTo(tab)  # fails today: hidden
    assert tab._state == TabState.READY  # fails today: IDLE

    # Case B: CANCELLED with info
    active_job2 = MagicMock(kind="video", job_id="j2", output_dir="C:/Downloads", title="second")
    monkeypatch.setattr(mgr, "_active_job", active_job2)
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=CCCCCCCCCCC")
    tab._on_info_fetched(make_info("CCCCCCCCCCC"))

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_cancelled(active_job2)
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=CCCCCCCCCCC"
    assert tab._current_info is not None
    assert tab.info_card.isVisibleTo(tab)
    assert tab._state == TabState.READY

    # Case C: CANCELLED with typed text but info not fetched yet
    active_job3 = MagicMock(kind="video", job_id="j3", output_dir="C:/Downloads", title="third")
    monkeypatch.setattr(mgr, "_active_job", active_job3)
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=TYPEDTEXT11")
    tab._current_info = None  # simulate fetch pending or failed

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_cancelled(active_job3)
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=TYPEDTEXT11"  # fails today: wiped by _clear_inputs()


# T7
def test_two_queued_jobs_never_show_idle_between_finish_and_next_start(monkeypatch):
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")

    job1 = MagicMock(kind="video", job_id="j1", output_dir="C:/Downloads", title="job1")
    job2 = MagicMock(kind="video", job_id="j2", output_dir="C:/Downloads", title="job2")

    monkeypatch.setattr(mgr, "_active_job", job1)
    monkeypatch.setattr(mgr, "_waiting_queue", [job2])
    tab.set_state(TabState.DOWNLOADING)

    observed_states = []
    original_set_state = tab.set_state

    def spy_set_state(state):
        observed_states.append(state)
        original_set_state(state)

    monkeypatch.setattr(tab, "set_state", spy_set_state)

    tab._on_manager_finished(job1, "C:/Downloads/job1.mp4")

    # Should not have transitioned to IDLE because job2 is waiting
    assert TabState.IDLE not in observed_states  # fails today: [TabState.IDLE]
    assert tab._state == TabState.DOWNLOADING  # fails today: TabState.IDLE


# T8 (guard)
def test_no_download_running_pasting_link_transitions_fetching_to_ready(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DummyWorker)
    tab = VideoTab()
    tab.show()
    mgr = get_download_manager("video")
    monkeypatch.setattr(mgr, "_active_job", None)

    assert tab._state == TabState.IDLE
    tab.url_input.setText("https://www.youtube.com/watch?v=FRESHLINK12")
    assert tab._state == TabState.FETCHING
    tab._on_info_fetched(make_info("FRESHLINK12"))
    assert tab._state == TabState.READY
    assert tab.download_btn.isVisibleTo(tab)
    assert tab.download_btn.isEnabled()
    assert tab.cancel_btn.isHidden()


# --- Phase 6 Tests: Stuck State and Queue Management (Audio Tab) ---

def test_audio_tab_new_link_fetched_during_download_enables_add_to_queue(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="audio", job_id="a1"))
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=AUDIOTAB001")
    assert tab._state == TabState.FETCHING
    tab._on_info_fetched(make_info("AUDIOTAB001"))
    assert tab._state == TabState.DOWNLOADING  # fails before fix
    assert tab.url_input.isEnabled()  # fails before fix
    assert tab.queue_btn.isEnabled()  # fails before fix
    assert tab.cancel_btn.isVisibleTo(tab) and not tab.download_btn.isVisibleTo(tab)
    enqueued = []
    monkeypatch.setattr(mgr, "enqueue", lambda job, **k: enqueued.append(job))
    tab.queue_btn.click()
    assert len(enqueued) == 1  # fails before fix


def test_audio_tab_fetch_fails_during_running_download_returns_to_downloading(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="audio", job_id="a1"))
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=FAILAUD1234")
    assert tab._state == TabState.FETCHING
    tab._on_info_failed("Video unavailable")
    assert tab._state == TabState.DOWNLOADING  # fails before fix
    assert tab.url_input.isEnabled()  # fails before fix
    assert not tab.inline_msg.isHidden()
    assert "Video unavailable" in tab.inline_msg.text()
    assert not tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab) and not tab.download_btn.isVisibleTo(tab)


def test_audio_tab_fetch_result_stops_fetch_button_spinner(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="audio", job_id="a1"))
    tab.set_state(TabState.DOWNLOADING)

    # 1. Fetch finishes while download is running
    tab.url_input.setText("https://www.youtube.com/watch?v=SPINNERAUD1")
    assert tab.fetch_btn._is_loading is True
    tab._on_info_fetched(make_info("SPINNERAUD1"))
    assert tab.fetch_btn._is_loading is False  # fails before fix
    assert not tab.fetch_btn._spinner_timer.isActive()

    # 2. Fetch fails while download is running
    tab.url_input.setText("https://www.youtube.com/watch?v=SPINNERAUD2")
    assert tab.fetch_btn._is_loading is True
    tab._on_info_failed("Fetch error")
    assert tab.fetch_btn._is_loading is False  # fails before fix
    assert not tab.fetch_btn._spinner_timer.isActive()


def test_audio_tab_cached_link_during_download_goes_to_downloading_with_queue_enabled(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    monkeypatch.setattr(mgr, "_active_job", MagicMock(kind="audio", job_id="a1"))
    tab.set_state(TabState.DOWNLOADING)

    cached_url = "https://www.youtube.com/watch?v=CACHEDAUD01"
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE[cached_url] = make_info("CACHEDAUD01")

    tab.url_input.setText(cached_url)
    assert tab._state == TabState.DOWNLOADING
    assert tab.url_input.isEnabled()
    assert tab.queue_btn.isEnabled()
    assert tab.cancel_btn.isVisibleTo(tab)


def test_audio_tab_pending_link_survives_running_download_finished(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    active_job = MagicMock(kind="audio", job_id="a1", output_dir="C:/Downloads", title="first")
    monkeypatch.setattr(mgr, "_active_job", active_job)
    tab.set_state(TabState.DOWNLOADING)

    tab.url_input.setText("https://www.youtube.com/watch?v=AUDIOTAB005")
    tab._on_info_fetched(make_info("AUDIOTAB005"))

    monkeypatch.setattr(mgr, "_active_job", None)
    monkeypatch.setattr(mgr, "_waiting_queue", [])
    tab._on_manager_finished(active_job, "C:/Downloads/first.mp3")

    assert tab.url_input.text() == "https://www.youtube.com/watch?v=AUDIOTAB005"  # fails before fix
    assert tab._current_info is not None  # fails before fix
    assert tab.info_card.isVisibleTo(tab)  # fails before fix
    assert tab._state == TabState.READY  # fails before fix


def test_audio_tab_pending_link_survives_running_download_failed_and_cancelled(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")

    # Case A: FAILED
    active_job = MagicMock(kind="audio", job_id="a1", output_dir="C:/Downloads", title="first")
    monkeypatch.setattr(mgr, "_active_job", active_job)
    monkeypatch.setattr(mgr, "_waiting_queue", [])
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=AUDIOTAB006")
    tab._on_info_fetched(make_info("AUDIOTAB006"))

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_failed(active_job, "Download error")
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=AUDIOTAB006"  # fails before fix
    assert tab._current_info is not None  # fails before fix
    assert tab.info_card.isVisibleTo(tab)  # fails before fix
    assert tab._state == TabState.READY  # fails before fix

    # Case B: CANCELLED with info
    active_job2 = MagicMock(kind="audio", job_id="a2", output_dir="C:/Downloads", title="second")
    monkeypatch.setattr(mgr, "_active_job", active_job2)
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=AUDIOTAB06B")
    tab._on_info_fetched(make_info("AUDIOTAB06B"))

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_cancelled(active_job2)
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=AUDIOTAB06B"
    assert tab._current_info is not None
    assert tab.info_card.isVisibleTo(tab)
    assert tab._state == TabState.READY

    # Case C: CANCELLED with typed text but info not fetched yet
    active_job3 = MagicMock(kind="audio", job_id="a3", output_dir="C:/Downloads", title="third")
    monkeypatch.setattr(mgr, "_active_job", active_job3)
    tab.set_state(TabState.DOWNLOADING)
    tab.url_input.setText("https://www.youtube.com/watch?v=TYPEDAUD011")
    tab._current_info = None

    monkeypatch.setattr(mgr, "_active_job", None)
    tab._on_manager_cancelled(active_job3)
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=TYPEDAUD011"  # fails before fix


def test_audio_tab_two_queued_jobs_never_show_idle_between_finish_and_next_start(monkeypatch):
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")

    job1 = MagicMock(kind="audio", job_id="a1", output_dir="C:/Downloads", title="job1")
    job2 = MagicMock(kind="audio", job_id="a2", output_dir="C:/Downloads", title="job2")

    monkeypatch.setattr(mgr, "_active_job", job1)
    monkeypatch.setattr(mgr, "_waiting_queue", [job2])
    tab.set_state(TabState.DOWNLOADING)

    observed_states = []
    original_set_state = tab.set_state

    def spy_set_state(state):
        observed_states.append(state)
        original_set_state(state)

    monkeypatch.setattr(tab, "set_state", spy_set_state)

    tab._on_manager_finished(job1, "C:/Downloads/job1.mp3")

    assert TabState.IDLE not in observed_states  # fails before fix
    assert tab._state == TabState.DOWNLOADING  # fails before fix


def test_audio_tab_no_download_running_pasting_link_transitions_fetching_to_ready(monkeypatch):
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DummyWorker)
    tab = AudioTab()
    tab.show()
    mgr = get_download_manager("audio")
    monkeypatch.setattr(mgr, "_active_job", None)

    assert tab._state == TabState.IDLE
    tab.url_input.setText("https://www.youtube.com/watch?v=FRESHAUD012")
    assert tab._state == TabState.FETCHING
    tab._on_info_fetched(make_info("FRESHAUD012"))
    assert tab._state == TabState.READY
    assert tab.download_btn.isVisibleTo(tab)
    assert tab.download_btn.isEnabled()
    assert tab.cancel_btn.isHidden()


# --- Phase 7 Tests: Fetch Flow Robustness ---

@pytest.mark.parametrize("TabClass,tab_mod", [
    (VideoTab, "app.ui.video_tab"),
    (AudioTab, "app.ui.audio_tab"),
])
def test_newer_paste_while_fetch_runs_discards_old_and_finishes_cleanly(TabClass, tab_mod, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()
    created_workers = []

    class RecordingWorker(QObject):
        fetched = Signal(object)
        failed = Signal(str)
        finished = Signal()

        def __init__(self, url, parent=None):
            super().__init__(parent)
            self.url = url
            created_workers.append(self)

        def start(self):
            pass

    monkeypatch.setattr(f"{tab_mod}.InfoFetchWorker", RecordingWorker)
    tab = TabClass()
    tab.show()

    tab.url_input.setText("https://www.youtube.com/watch?v=SEQONE11111")
    assert len(created_workers) == 1
    w1 = created_workers[0]
    assert tab.fetch_btn._is_loading is True

    tab.url_input.setText("https://www.youtube.com/watch?v=SEQTWO22222")
    assert len(created_workers) == 2
    w2 = created_workers[1]
    assert tab.fetch_btn._is_loading is True

    # Older worker finishes late
    w1.fetched.emit(make_info("SEQONE11111"))
    assert tab._current_info is None

    # Newer worker finishes
    w2.fetched.emit(make_info("SEQTWO22222"))
    assert tab._current_info is not None
    assert "SEQTWO22222" in tab._current_info.url
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()
    assert tab.url_input.isEnabled() is True
    assert tab._state == TabState.READY


@pytest.mark.parametrize("TabClass,tab_mod", [
    (VideoTab, "app.ui.video_tab"),
    (AudioTab, "app.ui.audio_tab"),
])
def test_fetch_finish_after_tab_reset_no_stale_card_and_no_crash(TabClass, tab_mod, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()
    created_workers = []

    class RecordingWorker(QObject):
        fetched = Signal(object)
        failed = Signal(str)
        finished = Signal()

        def __init__(self, url, parent=None):
            super().__init__(parent)
            self.url = url
            created_workers.append(self)

        def start(self):
            pass

    monkeypatch.setattr(f"{tab_mod}.InfoFetchWorker", RecordingWorker)
    tab = TabClass()
    tab.show()

    tab.url_input.setText("https://www.youtube.com/watch?v=RESETVID111")
    assert len(created_workers) == 1
    w = created_workers[0]
    assert tab._state == TabState.FETCHING

    # Tab is reset / cleared
    tab._clear_inputs()
    assert tab._current_info is None
    assert not tab.info_card.isVisibleTo(tab)

    # In-flight worker finishes after reset
    w.fetched.emit(make_info("RESETVID111"))

    # Must NOT resurrect the old card or current info
    assert tab._current_info is None
    assert not tab.info_card.isVisibleTo(tab)
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()


@pytest.mark.parametrize("TabClass,tab_mod", [
    (VideoTab, "app.ui.video_tab"),
    (AudioTab, "app.ui.audio_tab"),
])
def test_spinner_off_across_all_states_including_offline(TabClass, tab_mod, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()
    monkeypatch.setattr(f"{tab_mod}.InfoFetchWorker", DummyWorker)
    tab = TabClass()
    tab.show()

    # IDLE
    tab.set_state(TabState.IDLE)
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()

    # READY
    tab.set_state(TabState.READY)
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()

    # DOWNLOADING
    tab.set_state(TabState.DOWNLOADING)
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()

    # OFFLINE transition from FETCHING
    tab.url_input.setText("https://www.youtube.com/watch?v=OFFLINESPN1")
    assert tab._state == TabState.FETCHING
    assert tab.fetch_btn._is_loading is True

    tab.set_online(False)
    assert tab._state == TabState.OFFLINE
    assert tab.fetch_btn._is_loading is False
    assert not tab.fetch_btn._spinner_timer.isActive()




