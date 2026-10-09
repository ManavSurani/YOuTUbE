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
