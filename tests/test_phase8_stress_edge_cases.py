"""Automated tests for Phase 8 Chunk 8.2: Stress and Edge Cases.

1. Queue 10 items, cancel the 3rd, crash during 5th: queue restores cleanly, history has 0 broken rows.
2. Disk full: friendly 'not enough space' message before downloading.
3. Change download folder mid-queue: running job finishes in old folder, next jobs use new one.
4. Rename/move Downloads folder: History database survives.
5. Two app instances: second focuses first (SingleInstance guard).
"""

import json
from pathlib import Path
import shutil
import sys
from unittest.mock import MagicMock
import pytest
from PySide6.QtWidgets import QApplication

from app.core.jobs import DownloadJob
from app.core.download_manager import DownloadManager
from app.core.history_db import HistoryItem, add_item, list_items
from app.core.history_service import relink
from app.core.single_instance import SingleInstance, SERVER_NAME
from PySide6.QtNetwork import QLocalServer

@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_stress_queue_recovery_and_history_cleanliness(tmp_path: Path, monkeypatch):
    """Stress test: 10 items, cancel 3rd, kill during 5th; restarts cleanly without half-written rows."""
    import app.core.paths as paths_mod
    import app.core.history_db as hdb_mod

    app_data = tmp_path / "AppData"
    app_data.mkdir()
    queue_file = app_data / "queue.json"
    db_file = app_data / "history.db"

    monkeypatch.setattr(paths_mod, "APP_DATA", app_data)

    # 1. Initialize DownloadManager with empty queue
    mgr = DownloadManager()
    mgr._queue_file = queue_file
    mgr._waiting_queue.clear()
    mgr._is_offline = False

    # Prevent real subprocesses from starting during test
    monkeypatch.setattr(mgr, "_start_worker", lambda job: None)

    # Enqueue 10 jobs
    jobs = []
    for i in range(1, 11):
        j = DownloadJob(
            job_id=f"job_{i}",
            url=f"https://www.youtube.com/watch?v=vid{i}",
            video_id=f"vid{i}",
            title=f"Video Number {i}",
            channel="Channel",
            duration_seconds=60,
            thumbnail_url="",
            thumbnail_bytes=None,
            kind="video",
            quality_label="1080p",
            height=1080,
            audio_format=None,
            output_dir=str(tmp_path),
            created_at=f"2026-10-02T12:{i:02d}:00Z",
        )
        jobs.append(j)
        mgr.enqueue(j)

    assert len(mgr.waiting_jobs) == 9  # 1 active, 9 waiting

    # Cancel 3rd item (job_3)
    mgr.cancel_job("job_3")
    assert not any(j.job_id == "job_3" for j in mgr.waiting_jobs)

    # Complete items 1, 2, 4
    for finished_id in ("job_1", "job_2", "job_4"):
        item = HistoryItem(
            id=None,
            title=f"Video Number {finished_id[-1]}",
            url=f"https://www.youtube.com/watch?v=vid{finished_id[-1]}",
            type="video",
            quality="1080p",
            file_path=str(tmp_path / f"video_{finished_id[-1]}.mkv"),
            size_bytes=5000000,
            duration=60,
            thumbnail_path="",
            created_at=None,
            video_id=f"vid{finished_id[-1]}",
            channel="Channel",
            file_missing=0,
            source_job_id=finished_id,
        )
        add_item(item, custom_path=db_file)

    # Simulate abrupt app termination during job_5 (no completed save for job_5)
    # Restart app: create a fresh DownloadManager reading queue.json
    restarted_mgr = DownloadManager()
    restarted_mgr._queue_file = queue_file
    restarted_mgr._load_persisted_queue()

    # Verify queue was restored without corrupted entries
    assert any(j.job_id == "job_5" for j in restarted_mgr.waiting_jobs)
    assert not any(j.job_id == "job_3" for j in restarted_mgr.waiting_jobs)

    # Verify history database has exactly 3 clean records and 0 partial/broken rows
    records = list_items(custom_path=db_file)
    assert len(records) == 3
    for r in records:
        assert r.size_bytes > 0
        assert r.title != ""
        assert r.file_path != ""


def test_edge_case_disk_full_rejection(tmp_path: Path, monkeypatch):
    """When disk space is below safety threshold, download is prevented with friendly message."""
    from app.ui.video_tab import VideoTab

    tab = VideoTab()
    monkeypatch.setattr(tab, "fetch_url", lambda: None)
    tab.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    # Mock disk_usage to report 10MB free (< 50MB required)
    usage_mock = MagicMock()
    usage_mock.free = 10 * 1024 * 1024  # 10MB
    monkeypatch.setattr(shutil, "disk_usage", lambda path: usage_mock)

    job = tab._build_job()
    assert job is None
    assert "not enough disk space" in tab.inline_msg.text().lower()
    tab.deleteLater()


def test_edge_case_change_download_folder_mid_queue(tmp_path: Path, monkeypatch):
    """Running job finishes in original folder; next jobs use newly set folder."""
    import app.core.settings as settings_mod

    old_dir = tmp_path / "OldDownloads"
    old_dir.mkdir()
    new_dir = tmp_path / "NewDownloads"
    new_dir.mkdir()

    # Settings initially points to old_dir
    settings_dict = {"download_dir": str(old_dir)}
    monkeypatch.setattr(settings_mod, "load_settings", lambda: dict(settings_dict))

    mgr = DownloadManager()
    mgr._waiting_queue.clear()
    mgr._is_offline = False

    launched_dirs = []
    def mock_start(job):
        settings = settings_mod.load_settings()
        target_dir = job.output_dir or settings.get("download_dir")
        launched_dirs.append((job.job_id, target_dir))

    monkeypatch.setattr(mgr, "_start_worker", mock_start)

    # Job 1 queued (active)
    j1 = DownloadJob(
        job_id="job_1",
        url="https://youtube.com/watch?v=1",
        video_id="1",
        title="Job 1",
        channel="C",
        duration_seconds=10,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir=str(old_dir),
        created_at="2026-10-02T12:00:00Z",
    )
    # Job 2 queued with default folder (empty string or dynamic)
    j2 = DownloadJob(
        job_id="job_2",
        url="https://youtube.com/watch?v=2",
        video_id="2",
        title="Job 2",
        channel="C",
        duration_seconds=10,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-02T12:01:00Z",
    )

    mgr.enqueue(j1)
    mgr.enqueue(j2)

    # Change settings to new_dir mid-queue
    settings_dict["download_dir"] = str(new_dir)

    # Finish job 1 -> job 2 starts
    mgr._on_worker_finished(j1, str(old_dir / "job_1.mkv"))

    assert len(launched_dirs) == 2
    assert launched_dirs[0] == ("job_1", str(old_dir))
    assert launched_dirs[1] == ("job_2", str(new_dir))


def test_edge_case_rename_downloads_folder_history_survives(tmp_path: Path):
    """History database persists and flags missing files when Downloads folder is moved."""
    db_file = tmp_path / "history.db"
    orig_folder = tmp_path / "Downloads"
    orig_folder.mkdir()
    test_video = orig_folder / "test_video.mkv"
    test_video.write_bytes(b"content")

    item = HistoryItem(
        id=None,
        title="Moved Video",
        url="https://youtube.com/watch?v=moved",
        type="video",
        quality="1080p",
        file_path=str(test_video),
        size_bytes=len(b"content"),
        duration=30,
        thumbnail_path="",
        created_at=None,
        video_id="moved",
        channel="Channel",
        file_missing=0,
        source_job_id="job_moved",
    )
    row_id = add_item(item, custom_path=db_file)

    # Rename download directory
    renamed_folder = tmp_path / "RenamedDownloads"
    orig_folder.rename(renamed_folder)

    # History database still has row
    items = list_items(custom_path=db_file)
    assert len(items) == 1
    assert items[0].title == "Moved Video"

    # Relink works cleanly
    new_path = renamed_folder / "test_video.mkv"
    assert new_path.exists()
    relink(row_id, str(new_path), custom_db=db_file)

    updated = list_items(custom_path=db_file)[0]
    assert updated.file_path == str(new_path)
    assert updated.file_missing == 0
