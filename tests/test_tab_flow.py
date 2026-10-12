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


@pytest.fixture(autouse=True)
def no_duplicate_dialog(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.find_duplicate", lambda *a, **kw: None)
    monkeypatch.setattr("app.ui.audio_tab.find_duplicate", lambda *a, **kw: None)


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
        self.waiting_jobs = []

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
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


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
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


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


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_fetch_url_shows_getting_info_message_and_clears_on_fetched(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    tab = TabClass()
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker.start", lambda self: None)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker.start", lambda self: None)

    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.fetch_url()

    assert tab.inline_msg.isVisibleTo(tab)
    assert "Getting video info…" in tab.inline_msg.text()

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Title",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    tab._on_info_fetched(info)
    assert not tab.inline_msg.isVisibleTo(tab)
    assert tab.inline_msg.text() == ""


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_stale_fetch_worker_is_ignored(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    tab = TabClass()
    created_workers = []

    class FakeWorker:
        def __init__(self, url, parent=None):
            self.url = url
            self.fetched_cb = None
            self.failed_cb = None
            created_workers.append(self)

        class _Signal:
            def __init__(self, owner, name):
                self.owner = owner
                self.name = name
            def connect(self, slot):
                if self.name == "fetched":
                    self.owner.fetched_cb = slot
                else:
                    self.owner.failed_cb = slot
            def disconnect(self):
                if self.name == "fetched":
                    self.owner.fetched_cb = None
                else:
                    self.owner.failed_cb = None

        @property
        def fetched(self):
            return self._Signal(self, "fetched")

        @property
        def failed(self):
            return self._Signal(self, "failed")

        def start(self):
            pass

    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", FakeWorker)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", FakeWorker)

    # First fetch for URL 1
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=video111111")
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert len(created_workers) == 1
    worker1 = created_workers[0]

    # Second fetch for URL 2
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=video222222")
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert len(created_workers) == 2
    worker2 = created_workers[1]

    # Worker 1 finishes late with URL 1 info
    info1 = VideoInfo(
        url="https://www.youtube.com/watch?v=video111111",
        title="Video 1",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    if worker1.fetched_cb:
        worker1.fetched_cb(info1)

    # Worker 1 was stale, current info must NOT be Video 1
    assert tab._current_info is None

    # Worker 2 finishes with URL 2 info
    info2 = VideoInfo(
        url="https://www.youtube.com/watch?v=video222222",
        title="Video 2",
        channel="Channel",
        duration=200,
        duration_str="3:20",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    if worker2.fetched_cb:
        worker2.fetched_cb(info2)

    assert tab._current_info is not None
    assert tab._current_info.title == "Video 2"


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_fetch_cache_hit_skips_worker_creation(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    cached_url = "https://www.youtube.com/watch?v=cached12345"
    info = VideoInfo(
        url=cached_url,
        title="Cached Video",
        channel="Channel",
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    _FETCH_CACHE[cached_url] = info

    tab = TabClass()
    worker_started = False
    def mock_worker_init(*args, **kwargs):
        nonlocal worker_started
        worker_started = True
    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker.__init__", mock_worker_init)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker.__init__", mock_worker_init)

    tab.url_input.blockSignals(True)
    tab.url_input.setText(cached_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()

    assert worker_started is False
    assert tab._fetch_worker is None
    assert tab._state == TabState.READY
    assert tab._current_info == info
    assert not tab.inline_msg.isVisibleTo(tab)


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_failed_fetch_is_not_cached(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    fail_url = "https://www.youtube.com/watch?v=fail1234567"
    tab = TabClass()

    class FailingWorker:
        def __init__(self, url, parent=None):
            self.failed_cb = None
        class _Sig:
            def __init__(self, owner): self.owner = owner
            def connect(self, slot): self.owner.failed_cb = slot
            def disconnect(self): pass
        @property
        def fetched(self): return self._Sig(self)
        @property
        def failed(self): return self._Sig(self)
        def start(self):
            if self.failed_cb:
                self.failed_cb("Video unavailable")

    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", FailingWorker)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", FailingWorker)

    tab.url_input.blockSignals(True)
    tab.url_input.setText(fail_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()

    assert fail_url not in _FETCH_CACHE
    assert tab.inline_msg.isVisibleTo(tab)
    assert "Video unavailable" in tab.inline_msg.text()


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_repasted_link_after_fetch_is_instant_from_cache(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    test_url = "https://www.youtube.com/watch?v=repaste1234"
    tab = TabClass()
    worker_count = 0

    class CountingWorker:
        def __init__(self, url, parent=None):
            nonlocal worker_count
            worker_count += 1
            self.fetched_cb = None
            self.failed_cb = None
        class _Sig:
            def __init__(self, owner, name):
                self.owner = owner
                self.name = name
            def connect(self, slot):
                if self.name == "fetched":
                    self.owner.fetched_cb = slot
                else:
                    self.owner.failed_cb = slot
            def disconnect(self): pass
        @property
        def fetched(self): return self._Sig(self, "fetched")
        @property
        def failed(self): return self._Sig(self, "failed")
        def start(self):
            if self.fetched_cb:
                self.fetched_cb(VideoInfo(
                    url=test_url,
                    title="Repasted Video",
                    channel="Channel",
                    duration=60,
                    duration_str="1:00",
                    thumbnail_url="",
                    qualities=[("1080p", 1000)],
                    filesize_approx=1000,
                ))

    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", CountingWorker)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", CountingWorker)

    # First fetch -> worker runs and populates cache
    tab.url_input.blockSignals(True)
    tab.url_input.setText(test_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert worker_count == 1
    assert tab._state == TabState.READY
    assert tab._current_info is not None

    # Clear inputs (like user cleared or previous download finished)
    tab._clear_inputs()
    tab.set_state(TabState.IDLE)
    assert tab._current_info is None

    # Second fetch with same link -> instant cache hit, worker_count must stay 1
    tab.url_input.blockSignals(True)
    tab.url_input.setText(test_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert worker_count == 1
    assert tab._state == TabState.READY
    assert tab._current_info is not None
    assert tab._current_info.title == "Repasted Video"


@pytest.mark.parametrize("TabClass", [VideoTab, AudioTab])
def test_cache_key_is_requested_url_even_when_info_url_differs(TabClass, monkeypatch):
    from app.ui.video_tab import _FETCH_CACHE
    _FETCH_CACHE.clear()

    # Requested URL cleans to https://www.youtube.com/watch?v=diffid12345
    requested_url = "https://youtu.be/diffid12345"
    cleaned_requested = "https://www.youtube.com/watch?v=diffid12345"
    canonical_info_url = "https://www.youtube.com/watch?v=canonical_something_else"

    tab = TabClass()
    worker_count = 0

    class DiffUrlWorker:
        def __init__(self, url, parent=None):
            nonlocal worker_count
            worker_count += 1
            self.fetched_cb = None
            self.failed_cb = None
        class _Sig:
            def __init__(self, owner, name):
                self.owner = owner
                self.name = name
            def connect(self, slot):
                if self.name == "fetched":
                    self.owner.fetched_cb = slot
                else:
                    self.owner.failed_cb = slot
            def disconnect(self): pass
        @property
        def fetched(self): return self._Sig(self, "fetched")
        @property
        def failed(self): return self._Sig(self, "failed")
        def start(self):
            if self.fetched_cb:
                self.fetched_cb(VideoInfo(
                    url=canonical_info_url,  # info.url is different!
                    title="Different Canonical URL",
                    channel="Channel",
                    duration=60,
                    duration_str="1:00",
                    thumbnail_url="",
                    qualities=[("1080p", 1000)],
                    filesize_approx=1000,
                ))

    monkeypatch.setattr("app.ui.video_tab.InfoFetchWorker", DiffUrlWorker)
    monkeypatch.setattr("app.ui.audio_tab.InfoFetchWorker", DiffUrlWorker)

    tab.url_input.blockSignals(True)
    tab.url_input.setText(requested_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert worker_count == 1

    # Assert cache is keyed by the requested cleaned URL
    assert cleaned_requested in _FETCH_CACHE
    assert canonical_info_url not in _FETCH_CACHE

    # Clear and re-fetch using requested URL -> hits cache
    tab._clear_inputs()
    tab.url_input.blockSignals(True)
    tab.url_input.setText(requested_url)
    tab.url_input.blockSignals(False)
    tab.fetch_url()

    assert worker_count == 1
    assert tab._current_info is not None
    assert tab._current_info.title == "Different Canonical URL"


@pytest.mark.parametrize("TabClass,module_name", [(VideoTab, "video_tab"), (AudioTab, "audio_tab")])
def test_already_downloaded_dialog_flow(TabClass, module_name, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    tab, _ = _setup_tab_for_thumb_test(TabClass, module_name, monkeypatch, b"")
    fake_mgr = FakeManager()
    enqueued_calls = []

    def tracking_enqueue(*args, **kwargs):
        enqueued_calls.append((args, kwargs))

    fake_mgr.enqueue = tracking_enqueue
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda kind=None: fake_mgr)

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

    # 1. Normal download (no duplicate): calls enqueue(job) without force_overwrite
    monkeypatch.setattr(f"app.ui.{module_name}.find_duplicate", lambda *a, **kw: None)
    tab.start_download()
    assert len(enqueued_calls) == 1
    args, kwargs = enqueued_calls[0]
    assert len(args) == 1
    assert "force_overwrite" not in kwargs

    # 2. Duplicate confirmed with "No" (Cancel): enqueues nothing
    enqueued_calls.clear()
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    tab._on_info_fetched(info)
    fake_dup = MagicMock()
    monkeypatch.setattr(f"app.ui.{module_name}.find_duplicate", lambda *a, **kw: fake_dup)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Cancel)

    tab.start_download()
    assert len(enqueued_calls) == 0

    # 3. Duplicate confirmed with "Yes": calls enqueue(job, force_overwrite=True)
    enqueued_calls.clear()
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    tab._on_info_fetched(info)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    tab.start_download()
    assert len(enqueued_calls) == 1
    args, kwargs = enqueued_calls[0]
    assert len(args) == 1
    assert kwargs.get("force_overwrite") is True


@pytest.mark.parametrize("TabClass,module_name,kind", [
    (VideoTab, "video_tab", "video"),
    (AudioTab, "audio_tab", "audio"),
])
def test_in_flight_duplicate_detection(TabClass, module_name, kind, monkeypatch):
    tab, _ = _setup_tab_for_thumb_test(TabClass, module_name, monkeypatch, b"")
    fake_mgr = FakeManager()
    enqueued_calls = []

    def tracking_enqueue(*args, **kwargs):
        enqueued_calls.append((args, kwargs))

    fake_mgr.enqueue = tracking_enqueue
    monkeypatch.setattr(f"app.ui.{module_name}.get_download_manager", lambda k=None: fake_mgr)

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Video",
        channel="Channel",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[("1080p", 1000), ("720p", 720)],
        filesize_approx=1000,
    )

    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    tab._on_info_fetched(info)

    job_to_test = tab._build_job()
    assert job_to_test is not None
    quality_label = job_to_test.quality_label

    active_job = MagicMock()
    active_job.video_id = "dQw4w9WgXcQ"
    active_job.kind = kind
    active_job.quality_label = quality_label

    # 1. Same video and quality already active -> start_download and add_to_queue blocked
    fake_mgr.active_job = active_job
    fake_mgr.waiting_jobs = []

    tab.start_download()
    assert len(enqueued_calls) == 0
    assert f"'{info.title}' ({quality_label}) is already downloading." in tab.inline_msg.text()
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert tab._current_info is not None

    tab.inline_msg.clear()
    tab.add_to_queue()
    assert len(enqueued_calls) == 0
    assert f"'{info.title}' ({quality_label}) is already downloading." in tab.inline_msg.text()
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert tab._current_info is not None

    # 2. Same video and quality already waiting in queue -> start_download and add_to_queue blocked
    fake_mgr.active_job = None
    waiting_job = MagicMock()
    waiting_job.video_id = "dQw4w9WgXcQ"
    waiting_job.kind = kind
    waiting_job.quality_label = quality_label
    fake_mgr.waiting_jobs = [waiting_job]

    tab.inline_msg.clear()
    tab.start_download()
    assert len(enqueued_calls) == 0
    assert f"'{info.title}' ({quality_label}) is already in the queue." in tab.inline_msg.text()
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert tab._current_info is not None

    tab.inline_msg.clear()
    tab.add_to_queue()
    assert len(enqueued_calls) == 0
    assert f"'{info.title}' ({quality_label}) is already in the queue." in tab.inline_msg.text()
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert tab._current_info is not None

    # 3. Different quality of the same video -> enqueue happens
    diff_waiting = MagicMock()
    diff_waiting.video_id = "dQw4w9WgXcQ"
    diff_waiting.kind = kind
    diff_waiting.quality_label = "Different Quality 360p"
    fake_mgr.waiting_jobs = [diff_waiting]
    fake_mgr.active_job = None

    monkeypatch.setattr(f"app.ui.{module_name}.find_duplicate", lambda *a, **kw: None)
    tab.start_download()
    assert len(enqueued_calls) == 1

    # 4. No duplicate -> normal enqueue happens
    enqueued_calls.clear()
    fake_mgr.waiting_jobs = []
    fake_mgr.active_job = None
    tab.url_input.blockSignals(True)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    tab.url_input.blockSignals(False)
    tab._on_info_fetched(info)
    tab.start_download()
    assert len(enqueued_calls) == 1



