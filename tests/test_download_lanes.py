import ast
from pathlib import Path
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
