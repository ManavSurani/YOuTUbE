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
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue_video.json"

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
    manager1 = DownloadManager(kind="video")
    manager1._waiting_queue.clear()
    manager1._active_job = None
    manager1._queue_file = q_file

    manager1._waiting_queue = list(sample_jobs)
    manager1._save_persisted_queue()
    assert q_file.is_file()

    # Re-instantiate manager and load queue
    manager2 = DownloadManager(kind="video")
    manager2._waiting_queue.clear()
    manager2._queue_file = q_file
    manager2._load_persisted_queue()

    assert len(manager2.waiting_jobs) == 3
    assert manager2.waiting_jobs[0].title == "Queued Job 1"
    assert manager2.waiting_jobs[1].title == "Queued Job 2"


def test_download_manager_cancel_and_retry(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._failed_jobs.clear()
    manager._queue_file = tmp_path / "queue_video.json"

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


def test_force_overwrite_lifecycle(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._failed_jobs.clear()
    manager._queue_file = tmp_path / "queue_video.json"

    captured_cmds = []

    def mock_worker_factory(**kwargs):
        mock = MagicMock()
        mock.cmd = kwargs.get("cmd", [])
        mock.isRunning.return_value = False
        captured_cmds.append(mock.cmd)
        return mock

    monkeypatch.setattr("app.core.download_manager.DownloadWorker", mock_worker_factory)

    job = sample_jobs[0]

    # 1. First start with force_overwrite=True receives --force-overwrites
    manager.enqueue(job, force_overwrite=True)
    assert len(captured_cmds) == 1
    assert "--force-overwrites" in captured_cmds[0]
    # Set must be consumed immediately on start
    assert job.job_id not in manager._force_overwrite_job_ids

    # 2. Offline pause and resume does NOT pass --force-overwrites
    manager._paused_worker = manager._worker
    manager._resume_active_job()
    assert len(captured_cmds) == 2
    assert "--force-overwrites" not in captured_cmds[1]

    # 3. Cleanup on finish
    manager._on_worker_finished(job, str(tmp_path / "finished.mkv"))
    assert job.job_id not in manager._force_overwrite_job_ids


def test_force_overwrite_cleanup_on_cancel_and_retry(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue_video.json"

    captured_cmds = []
    monkeypatch.setattr(
        "app.core.download_manager.DownloadWorker",
        lambda **kwargs: captured_cmds.append(kwargs.get("cmd", [])) or MagicMock(),
    )

    job1 = sample_jobs[0]
    job2 = sample_jobs[1]

    # Start job1 normal, queue job2 with force_overwrite
    manager.enqueue(job1, force_overwrite=False)
    manager.enqueue(job2, force_overwrite=True)
    assert job2.job_id in manager._force_overwrite_job_ids

    # Cancel job2 while in queue -> set is cleaned
    manager.cancel_job(job2.job_id)
    assert job2.job_id not in manager._force_overwrite_job_ids

    # Simulate job1 failure and retry -> retry must NOT have force_overwrite
    manager._on_worker_failed(job1, "Network error")
    assert job1.job_id not in manager._force_overwrite_job_ids
    manager.retry_job(job1.job_id)
    assert "--force-overwrites" not in captured_cmds[-1]


def test_audio_force_overwrite_first_start(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager(kind="audio")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue_audio.json"

    captured_cmds = []
    monkeypatch.setattr(
        "app.core.download_manager.DownloadWorker",
        lambda **kwargs: captured_cmds.append(kwargs.get("cmd", [])) or MagicMock(),
    )

    info = VideoInfo(
        url="https://www.youtube.com/watch?v=queuevid9999",
        title="Queued Audio Job",
        channel="Channel",
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[],
        filesize_approx=1000000,
    )
    audio_job = DownloadJob.create(
        info,
        kind="audio",
        quality_label="MP3",
        audio_format="mp3",
    )

    manager.enqueue(audio_job, force_overwrite=True)
    assert len(captured_cmds) == 1
    assert "--force-overwrites" in captured_cmds[0]
    assert audio_job.job_id not in manager._force_overwrite_job_ids


def test_forced_job_failure_retry_and_set_cleanup(tmp_path: Path, sample_jobs, monkeypatch):
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._failed_jobs.clear()
    manager._queue_file = tmp_path / "queue_video.json"

    captured_cmds = []

    def mock_worker_factory(**kwargs):
        mock = MagicMock()
        mock.cmd = kwargs.get("cmd", [])
        mock.isRunning.return_value = False
        captured_cmds.append(mock.cmd)
        return mock

    monkeypatch.setattr("app.core.download_manager.DownloadWorker", mock_worker_factory)

    job_forced = sample_jobs[0]
    job_normal = sample_jobs[1]

    # 1. Forced job starts -> has flag, consumed from _force_overwrite_job_ids, added to _running_forced_job_ids
    manager.enqueue(job_forced, force_overwrite=True)
    assert len(captured_cmds) == 1
    assert "--force-overwrites" in captured_cmds[0]
    assert job_forced.job_id not in manager._force_overwrite_job_ids
    assert job_forced.job_id in manager._running_forced_job_ids

    # 2. Forced job fails -> moved to _failed_forced_job_ids, discarded from _running_forced_job_ids
    manager._on_worker_failed(job_forced, "Network error")
    assert job_forced.job_id not in manager._running_forced_job_ids
    assert job_forced.job_id in manager._failed_forced_job_ids

    # 3. Retry of forced job passes the flag once
    manager.retry_job(job_forced.job_id)
    assert len(captured_cmds) == 2
    assert "--force-overwrites" in captured_cmds[1]
    assert job_forced.job_id not in manager._failed_forced_job_ids
    assert job_forced.job_id not in manager._force_overwrite_job_ids
    assert job_forced.job_id in manager._running_forced_job_ids

    # Finish the forced job -> cleans all sets
    manager._on_worker_finished(job_forced, str(tmp_path / "finished.mkv"))
    assert job_forced.job_id not in manager._running_forced_job_ids
    assert job_forced.job_id not in manager._failed_forced_job_ids

    # 4. Normal job fails -> retry has NO flag
    manager.enqueue(job_normal, force_overwrite=False)
    assert len(captured_cmds) == 3
    assert "--force-overwrites" not in captured_cmds[2]
    assert job_normal.job_id not in manager._running_forced_job_ids

    manager._on_worker_failed(job_normal, "Network error")
    assert job_normal.job_id not in manager._failed_forced_job_ids

    manager.retry_job(job_normal.job_id)
    assert len(captured_cmds) == 4
    assert "--force-overwrites" not in captured_cmds[3]
    manager._on_worker_finished(job_normal, str(tmp_path / "normal.mkv"))

    # 5. Cancel clears the sets
    manager.enqueue(job_forced, force_overwrite=True)
    assert job_forced.job_id in manager._running_forced_job_ids
    manager.cancel_active()
    assert job_forced.job_id not in manager._force_overwrite_job_ids
    assert job_forced.job_id not in manager._running_forced_job_ids
    assert job_forced.job_id not in manager._failed_forced_job_ids

    # Cancel a failed job also clears _failed_forced_job_ids
    manager.enqueue(job_forced, force_overwrite=True)
    manager._on_worker_failed(job_forced, "Network error")
    assert job_forced.job_id in manager._failed_forced_job_ids
    manager.cancel_job(job_forced.job_id)
    assert job_forced.job_id not in manager._failed_forced_job_ids

    # 6. Shutdown clears the sets
    manager.enqueue(job_forced, force_overwrite=True)
    assert job_forced.job_id in manager._running_forced_job_ids
    manager.shutdown()
    assert len(manager._force_overwrite_job_ids) == 0
    assert len(manager._running_forced_job_ids) == 0
    assert len(manager._failed_forced_job_ids) == 0


def test_resume_passes_last_percent_floor(tmp_path: Path, sample_jobs, monkeypatch):
    """Resume passes job's last percent as floor_percent only in _resume_active_job."""
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue_video.json"

    captured_floors = []
    def fake_worker(**kwargs):
        captured_floors.append(kwargs.get("floor_percent", 0.0))
        mock = MagicMock()
        mock.isRunning.return_value = False
        return mock

    monkeypatch.setattr("app.core.download_manager.DownloadWorker", fake_worker)

    job = sample_jobs[0]
    # 1. First start: floor must be 0.0
    manager.enqueue(job)
    assert captured_floors[-1] == 0.0

    # 2. Worker emits progress at 85.0%
    manager._on_worker_progress(job, 85.0, "5 MB/s", "00:10", 425000000, 500000000)

    # 3. Network goes offline -> pauses
    manager.set_online(False)
    assert manager._paused_worker is not None

    # 4. Network comes online -> _resume_active_job resumes with floor 85.0
    manager.set_online(True)
    assert len(captured_floors) == 2
    assert captured_floors[-1] == 85.0


def test_first_start_and_retry_have_floor_zero(tmp_path: Path, sample_jobs, monkeypatch):
    """First start and retry after failure both get floor_percent=0.0."""
    manager = DownloadManager(kind="video")
    manager._waiting_queue.clear()
    manager._active_job = None
    manager._queue_file = tmp_path / "queue_video.json"

    captured_floors = []
    def fake_worker(**kwargs):
        captured_floors.append(kwargs.get("floor_percent", 0.0))
        mock = MagicMock()
        mock.isRunning.return_value = False
        return mock

    monkeypatch.setattr("app.core.download_manager.DownloadWorker", fake_worker)

    job = sample_jobs[0]
    # 1. First start gets 0.0
    manager.enqueue(job)
    assert captured_floors[-1] == 0.0

    # Progress emitted at 50%
    manager._on_worker_progress(job, 50.0, "5 MB/s", "00:10", 250000000, 500000000)

    # 2. Job fails
    manager._on_worker_failed(job, "HTTP 403 Forbidden")

    # 3. Retry gets 0.0
    manager.retry_job(job.job_id)
    assert captured_floors[-1] == 0.0


def test_atomic_write_json_clean_replace(tmp_path):
    from app.core.download_manager import _atomic_write_json
    import json

    target = tmp_path / "queue.json"
    data = [{"job_id": "j1", "title": "Job 1"}]
    _atomic_write_json(target, data)
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == data
    # Assert no leftover temp files
    temp_files = list(tmp_path.glob("*.tmp.*"))
    assert len(temp_files) == 0


def test_atomic_write_json_concurrent_threads(tmp_path):
    import json
    import threading
    from app.core.download_manager import _atomic_write_json

    target = tmp_path / "queue.json"
    errors = []

    def writer(i):
        try:
            for j in range(10):
                payload = [{"job_id": f"job_{i}_{j}", "iter": j}]
                _atomic_write_json(target, payload)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert len(loaded) == 1


def test_atomic_write_json_failure_preserves_original(tmp_path, monkeypatch):
    import json
    import os
    from app.core.download_manager import _atomic_write_json

    target = tmp_path / "queue.json"
    original = [{"job_id": "orig"}]
    _atomic_write_json(target, original)

    def faulty_replace(src, dst):
        raise OSError("Disk write error")

    monkeypatch.setattr(os, "replace", faulty_replace)

    with pytest.raises(OSError):
        _atomic_write_json(target, [{"job_id": "corrupt_attempt"}])

    # Original file must be completely untouched
    assert json.loads(target.read_text(encoding="utf-8")) == original
    # Temp files must be cleaned up
    temp_files = list(tmp_path.glob("*.tmp.*"))
    assert len(temp_files) == 0


def test_active_job_persisted_and_restored_on_crash_or_exit(tmp_path, sample_jobs, monkeypatch):
    import json
    qfile = tmp_path / "queue_video.json"

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = qfile
    monkeypatch.setattr(mgr, "_start_worker", lambda j: None)

    job = sample_jobs[0]
    mgr.enqueue(job)
    assert mgr.active_job is not None
    assert mgr.active_job.job_id == job.job_id

    # Check that queue_video.json persisted active_job
    raw = json.loads(qfile.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert raw["active_job"] is not None
    assert raw["active_job"]["job_id"] == job.job_id

    # Simulate app crash/restart by instantiating new manager from same file
    mgr2 = DownloadManager(kind="video")
    mgr2._waiting_queue.clear()
    mgr2._active_job = None
    mgr2._queue_file = qfile
    monkeypatch.setattr(mgr2, "_start_worker", lambda j: None)

    mgr2._load_persisted_queue()
    # Active job restored to waiting queue at index 0
    assert len(mgr2.waiting_jobs) == 1
    assert mgr2.waiting_jobs[0].job_id == job.job_id
    assert mgr2._restart_counts.get(job.job_id) == 1

    # start_restored_jobs resumes it
    mgr2.set_online(True)
    mgr2.start_restored_jobs()
    assert mgr2.active_job is not None
    assert mgr2.active_job.job_id == job.job_id


def test_active_job_restart_limit_moves_to_failed(tmp_path, sample_jobs, monkeypatch):
    import json
    qfile = tmp_path / "queue_video.json"

    job = sample_jobs[0]
    job_dict = {
        "job_id": job.job_id,
        "url": job.url,
        "video_id": job.video_id,
        "title": job.title,
        "kind": "video",
        "restart_count": 3,
    }
    qfile.write_text(json.dumps({"active_job": job_dict, "waiting_queue": []}), encoding="utf-8")

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = qfile
    monkeypatch.setattr(mgr, "_start_worker", lambda j: None)

    mgr._load_persisted_queue()
    assert len(mgr.waiting_jobs) == 0
    assert job.job_id in mgr._failed_jobs
    failed_job, reason = mgr._failed_jobs[job.job_id]
    assert "interrupted repeatedly" in reason.lower()


def test_user_cancel_active_job_cleared_from_persistence(tmp_path, sample_jobs, monkeypatch):
    import json
    qfile = tmp_path / "queue_video.json"

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = qfile
    monkeypatch.setattr(mgr, "_start_worker", lambda j: None)

    job = sample_jobs[0]
    mgr.enqueue(job)
    assert mgr.active_job is not None

    mgr.cancel_active()
    assert mgr.active_job is None

    raw = json.loads(qfile.read_text(encoding="utf-8"))
    assert raw["active_job"] is None

    # Restart app
    mgr2 = DownloadManager(kind="video")
    mgr2._waiting_queue.clear()
    mgr2._active_job = None
    mgr2._queue_file = qfile
    mgr2._load_persisted_queue()

    assert mgr2.active_job is None
    assert len(mgr2.waiting_jobs) == 0


def test_normal_shutdown_preserves_active_job(tmp_path, sample_jobs, monkeypatch):
    import json
    qfile = tmp_path / "queue_video.json"

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = qfile
    monkeypatch.setattr(mgr, "_start_worker", lambda j: None)

    job = sample_jobs[0]
    mgr.enqueue(job)
    assert mgr.active_job is not None

    mgr.shutdown()

    raw = json.loads(qfile.read_text(encoding="utf-8"))
    assert raw["active_job"] is not None
    assert raw["active_job"]["job_id"] == job.job_id

    # Restart
    mgr2 = DownloadManager(kind="video")
    mgr2._waiting_queue.clear()
    mgr2._active_job = None
    mgr2._queue_file = qfile
    monkeypatch.setattr(mgr2, "_start_worker", lambda j: None)

    mgr2._load_persisted_queue()
    assert len(mgr2.waiting_jobs) == 1
    assert mgr2.waiting_jobs[0].job_id == job.job_id


def test_flapping_network_does_not_spawn_multiple_workers(tmp_path, sample_jobs, monkeypatch):
    """Rapid online/offline toggling must never start multiple workers simultaneously."""
    from unittest.mock import MagicMock

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = tmp_path / "queue_video.json"

    started = []

    def mock_start(job, floor_percent=0.0):
        worker = MagicMock()
        worker.isRunning.return_value = True
        started.append((job, worker))
        mgr._worker = worker

    monkeypatch.setattr(mgr, "_start_worker", mock_start)

    job = sample_jobs[0]
    mgr.enqueue(job)
    assert len(started) == 1

    # Simulate flapping network
    for _ in range(5):
        mgr.set_online(False)
        mgr.set_online(True)

    # Since the worker is still marked as isRunning() == True, no second worker should be started
    assert len(started) == 1, f"Expected 1 worker, but started {len(started)}"


def test_resume_waits_for_old_worker_to_exit(tmp_path, sample_jobs, monkeypatch):
    """When network returns, resume waits until old worker stops running before starting a new worker."""
    from unittest.mock import MagicMock
    from PySide6.QtCore import QTimer

    mgr = DownloadManager(kind="video")
    mgr._waiting_queue.clear()
    mgr._active_job = None
    mgr._queue_file = tmp_path / "queue_video.json"

    callbacks = []
    monkeypatch.setattr(QTimer, "singleShot", lambda ms, cb: callbacks.append(cb))

    old_worker = MagicMock()
    old_worker.isRunning.return_value = True

    started = []
    monkeypatch.setattr(mgr, "_start_worker", lambda j, *a, **kw: started.append(j))

    job = sample_jobs[0]
    mgr._active_job = job
    mgr._worker = old_worker
    mgr._is_offline = False

    mgr.set_online(False)
    assert old_worker.pause.called

    mgr.set_online(True)
    # Old worker is still running -> must NOT start new worker immediately
    assert started == []
    assert len(callbacks) == 1

    # Once old worker reports isRunning() == False, running the callback resumes the job
    old_worker.isRunning.return_value = False
    callbacks[0]()
    assert started == [job]


