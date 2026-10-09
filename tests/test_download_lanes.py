import ast
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.jobs import DownloadJob


def test_no_get_download_manager_calls_without_kind():
    """Parse all Python files in app/ and verify no calls to get_download_manager() lack arguments."""
    app_dir = Path(__file__).resolve().parent.parent / "app"
    violations = []

    for py_file in app_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                func_name = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr

                if func_name == "get_download_manager":
                    if len(node.args) == 0 and len(node.keywords) == 0:
                        violations.append(f"{py_file.name}:{node.lineno}")

    assert not violations, f"Found get_download_manager() called without arguments: {violations}"


def test_enqueue_guard_rejects_mismatched_kind(tmp_path, caplog):
    """Enqueuing an audio job into the video lane must be rejected and logged."""
    manager = DownloadManager(kind="video")
    manager._queue_file = tmp_path / "queue_video.json"

    audio_job = DownloadJob(
        job_id="job_audio_1",
        url="https://youtube.com/watch?v=test12345",
        video_id="test12345",
        title="Test Audio",
        channel="Test Channel",
        duration_seconds=120,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="audio",
        quality_label="Best audio",
        height=None,
        audio_format="mp3",
        output_dir=str(tmp_path),
        created_at="2026-01-01T00:00:00",
    )

    from app.core.logger import get_logger
    logger = get_logger()
    logger.propagate = True
    try:
        with caplog.at_level("WARNING", logger="youtube_app"):
            manager.enqueue(audio_job)
    finally:
        logger.propagate = False

    # Job must not be added to waiting queue
    assert audio_job not in manager.waiting_jobs
    assert manager.active_job is None
    # Must log a warning about kind mismatch
    assert any("kind mismatch" in record.message for record in caplog.records)


def test_corrupt_or_empty_queue_migrated_to_corrupt(tmp_path, caplog, monkeypatch):
    """Corrupt or empty queue.json is renamed to queue.json.corrupt, logged, and app starts without crash."""
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)
    corrupt_file = tmp_path / "queue.json"
    corrupt_file.write_text("{malformed json", encoding="utf-8")

    from app.core.logger import get_logger
    logger = get_logger()
    logger.propagate = True
    try:
        with caplog.at_level("WARNING", logger="youtube_app"):
            dm_mod.migrate_legacy_queue_if_needed(tmp_path)
    finally:
        logger.propagate = False

    assert not corrupt_file.exists()
    assert (tmp_path / "queue.json.corrupt").exists()
    assert any("Corrupt or empty queue.json detected" in r.message for r in caplog.records)


def test_legacy_queue_missing_or_unknown_kind_defaults_to_video(tmp_path, monkeypatch):
    """Legacy items with missing or unknown 'kind' default to 'video'."""
    import json
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)
    legacy_file = tmp_path / "queue.json"
    items = [
        {"job_id": "1", "title": "No kind", "url": "https://youtube.com/watch?v=1"},
        {"job_id": "2", "title": "Unknown kind", "url": "https://youtube.com/watch?v=2", "kind": "unknown"},
        {"job_id": "3", "title": "Audio", "url": "https://youtube.com/watch?v=3", "kind": "audio"},
    ]
    legacy_file.write_text(json.dumps(items), encoding="utf-8")

    dm_mod.migrate_legacy_queue_if_needed(tmp_path)

    assert not legacy_file.exists()
    assert (tmp_path / "queue.json.bak").exists()
    v_items = json.loads((tmp_path / "queue_video.json").read_text(encoding="utf-8"))
    a_items = json.loads((tmp_path / "queue_audio.json").read_text(encoding="utf-8"))

    assert len(v_items) == 2
    assert v_items[0]["job_id"] == "1"
    assert v_items[1]["job_id"] == "2"
    assert len(a_items) == 1
    assert a_items[0]["job_id"] == "3"


def test_legacy_queue_migration_idempotent(tmp_path, monkeypatch):
    """Running migration twice never overwrites existing lane files."""
    import json
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)
    legacy_file = tmp_path / "queue.json"
    items = [{"job_id": "1", "title": "Video 1", "kind": "video"}]
    legacy_file.write_text(json.dumps(items), encoding="utf-8")

    dm_mod.migrate_legacy_queue_if_needed(tmp_path)

    v_content_before = (tmp_path / "queue_video.json").read_text(encoding="utf-8")

    # Run again - should be idempotent and not alter queue_video.json
    dm_mod.migrate_legacy_queue_if_needed(tmp_path)
    assert (tmp_path / "queue_video.json").read_text(encoding="utf-8") == v_content_before

    # Even if a new queue.json is created, existing queue_video.json must not be overwritten
    new_legacy = tmp_path / "queue.json"
    new_legacy.write_text(json.dumps([{"job_id": "999", "kind": "video"}]), encoding="utf-8")
    dm_mod.migrate_legacy_queue_if_needed(tmp_path)
    assert (tmp_path / "queue_video.json").read_text(encoding="utf-8") == v_content_before


from PySide6.QtCore import QObject, Signal


class FakeWorker(QObject):
    stage = Signal(str)
    progress = Signal(float, str, str, int, int)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, job_id="job_default", parent=None):
        super().__init__(parent)
        self.job_id = job_id


def _make_job(job_id: str, kind: str, video_id: str, title: str = "Test") -> DownloadJob:
    return DownloadJob(
        job_id=job_id,
        url=f"https://youtube.com/watch?v={video_id}",
        video_id=video_id,
        title=title,
        channel="Chan",
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind=kind,
        quality_label="1080p" if kind == "video" else "mp3",
        height=1080 if kind == "video" else None,
        audio_format=None if kind == "video" else "mp3",
        output_dir="",
        created_at="2026-01-01T00:00:00",
    )


def test_stale_worker_finished_signal_ignored(tmp_path):
    """A finished signal from an old, cancelled worker does not finish the new active job."""
    manager = DownloadManager(kind="video")
    manager._queue_file = tmp_path / "queue_video.json"
    job_active = _make_job("job_active", "video", "vid_active")
    manager._active_job = job_active
    current_worker = FakeWorker("job_active")
    manager._worker = current_worker

    old_worker = FakeWorker("job_old")
    old_worker.finished.connect(manager._on_worker_finished)
    old_worker.finished.emit(str(tmp_path / "stale.mkv"))

    assert manager.active_job is job_active
    assert len(manager.completed_jobs) == 0


def test_stale_worker_failed_signal_ignored(tmp_path):
    """A failed signal from an old worker does not fail the new active job."""
    manager = DownloadManager(kind="video")
    manager._queue_file = tmp_path / "queue_video.json"
    job_active = _make_job("job_active", "video", "vid_active")
    manager._active_job = job_active
    current_worker = FakeWorker("job_active")
    manager._worker = current_worker

    old_worker = FakeWorker("job_old")
    old_worker.failed.connect(manager._on_worker_failed)
    old_worker.failed.emit("Stale error")

    assert manager.active_job is job_active
    assert len(manager.failed_jobs) == 0


def test_current_worker_signal_processed_once(tmp_path):
    """A normal signal from the current worker is processed exactly once."""
    manager = DownloadManager(kind="video")
    manager._queue_file = tmp_path / "queue_video.json"
    job = _make_job("job_cur", "video", "vid_cur")
    manager._active_job = job
    worker = FakeWorker("job_cur")
    manager._worker = worker

    file_out = tmp_path / "cur.mkv"
    file_out.write_bytes(b"content")
    worker.finished.connect(manager._on_worker_finished)
    worker.finished.emit(str(file_out))

    assert manager.active_job is None
    assert len(manager.completed_jobs) == 1
    assert manager.completed_jobs[0][0].job_id == "job_cur"


def _setup_lanes(tmp_path, monkeypatch):
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "_managers", {})
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)
    v_mgr = get_download_manager("video")
    a_mgr = get_download_manager("audio")
    v_mgr._waiting_queue.clear()
    a_mgr._waiting_queue.clear()
    v_mgr._active_job = None
    a_mgr._active_job = None
    v_mgr._deferred_job_ids.clear()
    a_mgr._deferred_job_ids.clear()
    v_mgr._queue_file = tmp_path / "queue_video.json"
    a_mgr._queue_file = tmp_path / "queue_audio.json"
    monkeypatch.setattr(v_mgr, "_start_worker", lambda j: None)
    monkeypatch.setattr(a_mgr, "_start_worker", lambda j: None)
    return v_mgr, a_mgr


def test_same_video_id_deferral(tmp_path, monkeypatch):
    """Enqueueing video X and audio X simultaneously defers audio X and keeps video X active."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a = _make_job("a1", "audio", "same_vid")

    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    assert v_mgr.active_job is not None
    assert v_mgr.active_job.job_id == "v1"
    assert a_mgr.active_job is None
    assert "a1" in a_mgr.deferred_job_ids()
    assert len(a_mgr.waiting_jobs) == 1


def test_strict_fifo_preserved_when_deferred(tmp_path, monkeypatch):
    """Later jobs in the same lane must not jump ahead of a deferred job."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a1 = _make_job("a1", "audio", "same_vid")
    job_a2 = _make_job("a2", "audio", "other_vid")

    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a1)
    a_mgr.enqueue(job_a2)

    assert a_mgr.active_job is None
    assert "a1" in a_mgr.deferred_job_ids()
    assert len(a_mgr.waiting_jobs) == 2
    assert a_mgr.waiting_jobs[0].job_id == "a1"
    assert a_mgr.waiting_jobs[1].job_id == "a2"


def test_wake_both_lanes_on_finish(tmp_path, monkeypatch):
    """When video X finishes, deferred audio X wakes up and starts immediately."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a = _make_job("a1", "audio", "same_vid")
    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    assert a_mgr.active_job is None
    file_v = tmp_path / "v1.mkv"
    file_v.write_bytes(b"content")
    v_mgr._on_worker_finished(job_v, str(file_v))

    assert v_mgr.active_job is None
    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a1"
    assert "a1" not in a_mgr.deferred_job_ids()


def test_wake_both_lanes_on_cancel_active(tmp_path, monkeypatch):
    """Cancelling active video X immediately wakes up deferred audio X."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a = _make_job("a1", "audio", "same_vid")
    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    assert a_mgr.active_job is None
    v_mgr.cancel_active()

    assert v_mgr.active_job is None
    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a1"
    assert "a1" not in a_mgr.deferred_job_ids()


def test_wake_both_lanes_on_fail(tmp_path, monkeypatch):
    """Failing active video X immediately wakes up deferred audio X."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a = _make_job("a1", "audio", "same_vid")
    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    assert a_mgr.active_job is None
    v_mgr._on_worker_failed(job_v, "ERROR: Private video")

    assert v_mgr.active_job is None
    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a1"
    assert "a1" not in a_mgr.deferred_job_ids()


def test_wake_both_lanes_on_deferred_removal(tmp_path, monkeypatch):
    """Removing deferred job allows next waiting job in the lane to start."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "same_vid")
    job_a1 = _make_job("a1", "audio", "same_vid")
    job_a2 = _make_job("a2", "audio", "diff_vid")
    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a1)
    a_mgr.enqueue(job_a2)

    assert a_mgr.active_job is None
    a_mgr.cancel_job("a1")

    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a2"


def test_two_thread_simultaneous_history_save(tmp_path, monkeypatch):
    """Simulate two threads saving history simultaneously; assert zero SQLite lock errors."""
    import threading
    db_file = tmp_path / "history.db"
    monkeypatch.setattr("app.core.history_db.HISTORY_DB", db_file)
    from app.core.history_db import list_items
    from app.core.history_service import save_from_job

    job_v = _make_job("v_hist", "video", "vid_h", "Thread Video")
    job_a = _make_job("a_hist", "audio", "aud_h", "Thread Audio")

    file_v = tmp_path / "v_hist.mkv"
    file_v.write_bytes(b"video data")
    file_a = tmp_path / "a_hist.mp3"
    file_a.write_bytes(b"audio data")

    errors = []

    def save_job(job, path):
        try:
            save_from_job(job, str(path), custom_db=db_file)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=save_job, args=(job_v, file_v))
    t2 = threading.Thread(target=save_job, args=(job_a, file_a))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Concurrent save encountered errors: {errors}"
    items = list_items(custom_path=db_file)
    assert len(items) == 2


def test_set_online_false_pauses_active_workers_in_both_lanes(tmp_path, monkeypatch):
    """set_online(False) pauses running workers in both lanes."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "vid1")
    job_a = _make_job("a1", "audio", "vid2")

    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    v_worker = MagicMock()
    a_worker = MagicMock()
    v_mgr._worker = v_worker
    a_mgr._worker = a_worker

    v_mgr.set_online(False)
    a_mgr.set_online(False)

    v_worker.pause.assert_called_once()
    a_worker.pause.assert_called_once()
    assert v_mgr._is_offline is True
    assert a_mgr._is_offline is True


def test_set_online_true_resumes_active_workers_in_both_lanes(tmp_path, monkeypatch):
    """set_online(True) restarts workers for active jobs in both lanes."""
    v_mgr, a_mgr = _setup_lanes(tmp_path, monkeypatch)

    job_v = _make_job("v1", "video", "vid1")
    job_a = _make_job("a1", "audio", "vid2")

    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    v_mgr.set_online(False)
    a_mgr.set_online(False)

    started_workers = []
    def mock_start(job):
        started_workers.append(job.job_id)

    monkeypatch.setattr(v_mgr, "_start_worker", mock_start)
    monkeypatch.setattr(a_mgr, "_start_worker", mock_start)

    # Worker reference exists from previous run
    v_mgr._worker = MagicMock()
    a_mgr._worker = MagicMock()

    v_mgr.set_online(True)
    a_mgr.set_online(True)

    assert v_mgr._is_offline is False
    assert a_mgr._is_offline is False
    assert "v1" in started_workers
    assert "a1" in started_workers


def test_restored_waiting_items_start_automatically_when_online(tmp_path, monkeypatch):
    """Restored waiting items in both lanes automatically start when online."""
    from dataclasses import asdict
    import json
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "_managers", {})
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)

    job_v = _make_job("v_restored", "video", "vid1")
    job_a = _make_job("a_restored", "audio", "vid2")
    (tmp_path / "queue_video.json").write_text(json.dumps([asdict(job_v)]), encoding="utf-8")
    (tmp_path / "queue_audio.json").write_text(json.dumps([asdict(job_a)]), encoding="utf-8")

    v_mgr = get_download_manager("video")
    a_mgr = get_download_manager("audio")

    v_started = []
    a_started = []
    monkeypatch.setattr(v_mgr, "_start_worker", lambda j: v_started.append(j.job_id))
    monkeypatch.setattr(a_mgr, "_start_worker", lambda j: a_started.append(j.job_id))

    v_mgr.set_online(True)
    a_mgr.set_online(True)

    v_mgr.start_restored_jobs()
    a_mgr.start_restored_jobs()

    assert v_mgr.active_job is not None
    assert v_mgr.active_job.job_id == "v_restored"
    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a_restored"
    assert v_started == ["v_restored"]
    assert a_started == ["a_restored"]


def test_restored_waiting_items_do_not_start_when_offline_until_reconnect(tmp_path, monkeypatch):
    """Restored waiting items do not start when offline and start when connection returns."""
    from dataclasses import asdict
    import json
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "_managers", {})
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)

    job_v = _make_job("v_restored", "video", "vid1")
    job_a = _make_job("a_restored", "audio", "vid2")
    (tmp_path / "queue_video.json").write_text(json.dumps([asdict(job_v)]), encoding="utf-8")
    (tmp_path / "queue_audio.json").write_text(json.dumps([asdict(job_a)]), encoding="utf-8")

    v_mgr = get_download_manager("video")
    a_mgr = get_download_manager("audio")

    v_started = []
    a_started = []
    monkeypatch.setattr(v_mgr, "_start_worker", lambda j: v_started.append(j.job_id))
    monkeypatch.setattr(a_mgr, "_start_worker", lambda j: a_started.append(j.job_id))

    # Offline at startup
    v_mgr.set_online(False)
    a_mgr.set_online(False)

    v_mgr.start_restored_jobs()
    a_mgr.start_restored_jobs()

    # Nothing starts while offline
    assert v_mgr.active_job is None
    assert a_mgr.active_job is None
    assert len(v_mgr.waiting_jobs) == 1
    assert len(a_mgr.waiting_jobs) == 1
    assert v_started == []
    assert a_started == []

    # Network restored -> both lanes start their waiting items
    v_mgr.set_online(True)
    a_mgr.set_online(True)

    assert v_mgr.active_job is not None
    assert v_mgr.active_job.job_id == "v_restored"
    assert a_mgr.active_job is not None
    assert a_mgr.active_job.job_id == "a_restored"
    assert v_started == ["v_restored"]
    assert a_started == ["a_restored"]


def test_restored_same_video_id_pair_starts_one_and_defers_other(tmp_path, monkeypatch):
    """A restored same-video-id pair starts one and defers the other."""
    from dataclasses import asdict
    import json
    import app.core.download_manager as dm_mod
    monkeypatch.setattr(dm_mod, "_managers", {})
    monkeypatch.setattr(dm_mod, "APP_DATA", tmp_path)

    job_v = _make_job("v_shared", "video", "same_vid_123")
    job_a = _make_job("a_shared", "audio", "same_vid_123")
    (tmp_path / "queue_video.json").write_text(json.dumps([asdict(job_v)]), encoding="utf-8")
    (tmp_path / "queue_audio.json").write_text(json.dumps([asdict(job_a)]), encoding="utf-8")

    v_mgr = get_download_manager("video")
    a_mgr = get_download_manager("audio")

    monkeypatch.setattr(v_mgr, "_start_worker", lambda j: None)
    monkeypatch.setattr(a_mgr, "_start_worker", lambda j: None)

    v_mgr.set_online(True)
    a_mgr.set_online(True)

    v_mgr.start_restored_jobs()
    a_mgr.start_restored_jobs()

    # Video started first, audio was deferred
    assert v_mgr.active_job is not None
    assert v_mgr.active_job.job_id == "v_shared"
    assert a_mgr.active_job is None
    assert "a_shared" in a_mgr.deferred_job_ids()


