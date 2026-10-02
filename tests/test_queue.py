"""Tests for sequential queue execution and notifications."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob
from app.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication(sys.argv)


def test_video_queue_sequential_and_remove(tmp_path, monkeypatch):
    manager = get_download_manager()
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue.json"

    # Mock DownloadWorker to avoid spawning external processes
    mock_worker = MagicMock()
    monkeypatch.setattr("app.core.download_manager.DownloadWorker", lambda **kwargs: mock_worker)

    jobs = [
        DownloadJob.create(
            VideoInfo(url=f"https://www.youtube.com/watch?v=queue{i}12345", title=f"Item {i}", channel="C", duration=60, duration_str="1:00", thumbnail_url="", qualities=[], filesize_approx=0),
            kind="video", quality_label="1080p",
        )
        for i in range(1, 4)
    ]

    for j in jobs:
        manager.enqueue(j)

    assert manager.active_job is not None
    assert manager.active_job.title == "Item 1"
    assert len(manager.waiting_jobs) == 2

    # Remove item 2
    manager.cancel_job(jobs[1].job_id)
    assert len(manager.waiting_jobs) == 1
    assert manager.waiting_jobs[0].title == "Item 3"

    # Finish item 1 -> item 3 starts
    manager._on_worker_finished(manager.active_job, str(tmp_path / "item1.mkv"))
    assert manager.active_job is not None
    assert manager.active_job.title == "Item 3"

    # Finish item 3 -> queue completes
    manager._on_worker_finished(manager.active_job, str(tmp_path / "item3.mkv"))
    assert manager.active_job is None


def test_video_queue_error_in_middle_moves_on(tmp_path, monkeypatch):
    manager = get_download_manager()
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._failed_jobs.clear()
    manager._queue_file = tmp_path / "queue.json"

    mock_worker = MagicMock()
    monkeypatch.setattr("app.core.download_manager.DownloadWorker", lambda **kwargs: mock_worker)

    jobs = [
        DownloadJob.create(
            VideoInfo(url=f"https://www.youtube.com/watch?v=miderr{i}1234", title=f"Mid {i}", channel="C", duration=60, duration_str="1:00", thumbnail_url="", qualities=[], filesize_approx=0),
            kind="video", quality_label="1080p",
        )
        for i in range(1, 4)
    ]

    for j in jobs:
        manager.enqueue(j)

    # Item 1 finishes
    manager._on_worker_finished(manager.active_job, str(tmp_path / "mid1.mkv"))
    assert manager.active_job.title == "Mid 2"

    # Item 2 fails with private video error
    manager._on_worker_failed(manager.active_job, "ERROR: Private video. Sign in to view.")
    assert len(manager.failed_jobs) == 1
    assert "private" in manager.failed_jobs[0][1].lower()

    # Queue automatically moved on to item 3!
    assert manager.active_job is not None
    assert manager.active_job.title == "Mid 3"

    # Item 3 finishes
    manager._on_worker_finished(manager.active_job, str(tmp_path / "mid3.mkv"))
    assert manager.active_job is None


def test_queue_cancel_stops_and_waits(tmp_path, monkeypatch):
    manager = get_download_manager()
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue.json"

    mock_worker = MagicMock()
    monkeypatch.setattr("app.core.download_manager.DownloadWorker", lambda **kwargs: mock_worker)

    jobs = [
        DownloadJob.create(
            VideoInfo(url=f"https://www.youtube.com/watch?v=canc{i}123456", title=f"Cancel {i}", channel="C", duration=60, duration_str="1:00", thumbnail_url="", qualities=[], filesize_approx=0),
            kind="video", quality_label="1080p",
        )
        for i in range(1, 3)
    ]

    for j in jobs:
        manager.enqueue(j)

    assert manager.active_job.title == "Cancel 1"
    assert len(manager.waiting_jobs) == 1

    # Cancel while item 1 is downloading
    manager.cancel_active()
    assert manager.active_job is not None
    assert manager.active_job.title == "Cancel 2"


def test_finish_notification_on_inactive_window(monkeypatch):
    monkeypatch.setattr("app.ui.main_window.NetworkMonitor.start", lambda self: None)
    monkeypatch.setattr("app.ui.main_window.UpdateCheckWorker.start", lambda self: None)
    win = MainWindow()
    win.show()
    try:
        mock_show_message = MagicMock()
        monkeypatch.setattr(win.tray_icon, "showMessage", mock_show_message)

        # 1. When window is inactive -> toast shown
        monkeypatch.setattr(win, "isActiveWindow", lambda: False)
        win._on_download_finished_notification("My Video")
        mock_show_message.assert_called_once()
        assert "Download finished" in mock_show_message.call_args[0][1]

        # 2. When window is active -> no toast
        mock_show_message.reset_mock()
        monkeypatch.setattr(win, "isActiveWindow", lambda: True)
        win._on_download_finished_notification("My Video")
        mock_show_message.assert_not_called()
    finally:
        win.tray_icon.hide()
        win.close()
        _app.processEvents()
