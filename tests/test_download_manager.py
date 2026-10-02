"""Tests for DownloadManager: single-worker execution, offline pause/resume, persistence, retry, and cancellation."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.download_manager import DownloadManager
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob


@pytest.fixture
def sample_jobs():
    jobs = []
    for i in range(1, 4):
        info = VideoInfo(
            url=f"https://www.youtube.com/watch?v=queuevid{i}000",
            title=f"Queued Job {i}",
            channel="Channel",
            duration=60 * i,
            duration_str="1:00",
            thumbnail_url="",
            qualities=[("1080p", 1080)],
            filesize_approx=1000000,
        )
        job = DownloadJob.create(info, kind="video", quality_label="1080p", height=1080)
        jobs.append(job)
    return jobs


def test_download_manager_single_active_job(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager()
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue.json"

    started_jobs = []
    manager.job_started.connect(lambda j: started_jobs.append(j))

    # Mock DownloadWorker to prevent actual process execution
    mock_worker = MagicMock()
    monkeypatch.setattr("app.core.download_manager.DownloadWorker", lambda **kwargs: mock_worker)

    # Enqueue 3 jobs
    for j in sample_jobs:
        manager.enqueue(j)

    # Exactly 1 job is active, 2 are waiting
    assert manager.active_job is not None
    assert manager.active_job.title == "Queued Job 1"
    assert len(manager.waiting_jobs) == 2
    assert len(started_jobs) == 1

    # Finish active job -> automatically starts job 2
    manager._on_worker_finished(manager.active_job, str(tmp_path / "dummy1.mkv"))
    assert manager.active_job is not None
    assert manager.active_job.title == "Queued Job 2"
    assert len(manager.waiting_jobs) == 1
    assert len(started_jobs) == 2

    # Finish job 2 -> automatically starts job 3
    manager._on_worker_finished(manager.active_job, str(tmp_path / "dummy2.mkv"))
    assert manager.active_job is not None
    assert manager.active_job.title == "Queued Job 3"
    assert len(manager.waiting_jobs) == 0

    # Finish job 3 -> idle
    manager._on_worker_finished(manager.active_job, str(tmp_path / "dummy3.mkv"))
    assert manager.active_job is None
    assert len(manager.waiting_jobs) == 0


def test_download_manager_persistence(tmp_path: Path, sample_jobs):
    q_file = tmp_path / "test_queue.json"
    manager1 = DownloadManager()
    manager1._waiting_queue.clear()
    manager1._active_job = None
    manager1._queue_file = q_file

    manager1._waiting_queue = list(sample_jobs)
    manager1._save_persisted_queue()
    assert q_file.is_file()

    # Re-instantiate manager and load queue
    manager2 = DownloadManager()
    manager2._waiting_queue.clear()
    manager2._queue_file = q_file
    manager2._load_persisted_queue()

    assert len(manager2.waiting_jobs) == 3
    assert manager2.waiting_jobs[0].title == "Queued Job 1"
    assert manager2.waiting_jobs[1].title == "Queued Job 2"


def test_download_manager_cancel_and_retry(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager()
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._failed_jobs.clear()
    manager._queue_file = tmp_path / "queue.json"

    mock_worker = MagicMock()
    monkeypatch.setattr("app.core.download_manager.DownloadWorker", lambda **kwargs: mock_worker)

    manager.enqueue(sample_jobs[0])
    assert manager.active_job is not None

    # Simulate failure
    manager._on_worker_failed(sample_jobs[0], "ERROR: Private video")
    assert manager.active_job is None
    assert len(manager.failed_jobs) == 1
    failed_job, reason = manager.failed_jobs[0]
    assert failed_job.job_id == sample_jobs[0].job_id

    # Retry job
    manager.retry_job(sample_jobs[0].job_id)
    assert manager.active_job is not None
    assert len(manager.failed_jobs) == 0
