from pathlib import Path
from unittest.mock import MagicMock
import pytest
from app.core.tool_manager import (
    missing_tools,
    verify_tool,
    update_ytdlp,
    REQUIRED_TOOLS,
)
from app.core.jobs import DownloadJob


def test_missing_tools_empty_dir(tmp_path: Path):
    missing = missing_tools(tmp_path)
    assert len(missing) == len(REQUIRED_TOOLS)
    assert "yt-dlp.exe" in missing
    assert "ffmpeg.exe" in missing
    assert "ffprobe.exe" in missing
    assert "deno.exe" in missing


def test_missing_tools_partial(tmp_path: Path):
    (tmp_path / "yt-dlp.exe").write_text("dummy", encoding="utf-8")
    missing = missing_tools(tmp_path)
    assert len(missing) == 3
    assert "yt-dlp.exe" not in missing


def test_verify_tool_corrupt(tmp_path: Path):
    corrupt_exe = tmp_path / "yt-dlp.exe"
    corrupt_exe.write_text("corrupt_binary", encoding="utf-8")
    assert verify_tool("yt-dlp.exe", tmp_path) is False


def test_update_ytdlp_validation_failure_rolls_back(tmp_path: Path, monkeypatch):
    """When new download fails validation, it must be removed and original left intact."""
    import urllib.request
    import io
    import app.core.tool_manager as tm

    current_exe = tmp_path / "yt-dlp.exe"
    current_exe.write_text("original_version", encoding="utf-8")

    # Mock download response
    fake_download = io.BytesIO(b"corrupt_new_version")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=30: fake_download)

    # Mock run_hidden to fail on the new binary
    monkeypatch.setattr(tm, "run_hidden", lambda cmd, timeout=5: (-1, ""))

    success = update_ytdlp(bin_dir=tmp_path)
    assert success is False
    assert current_exe.exists()
    assert current_exe.read_text(encoding="utf-8") == "original_version"
    assert not (tmp_path / "yt-dlp.exe.new").exists()


def test_update_ytdlp_swap_failure_rolls_back(tmp_path: Path, monkeypatch):
    """When swapped binary fails verify_tool, rollback restores .bak to original."""
    import urllib.request
    import io
    import app.core.tool_manager as tm

    current_exe = tmp_path / "yt-dlp.exe"
    current_exe.write_text("original_working_version", encoding="utf-8")

    fake_download = io.BytesIO(b"new_candidate")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=30: fake_download)

    # First call for validation succeeds, but final verify_tool fails
    monkeypatch.setattr(tm, "run_hidden", lambda cmd, timeout=5: (0, "2026.09.01"))
    monkeypatch.setattr(tm, "verify_tool", lambda tool, bin_dir: False)

    success = update_ytdlp(bin_dir=tmp_path)
    assert success is False
    # Original should have been rolled back from .bak
    assert current_exe.exists()
    assert current_exe.read_text(encoding="utf-8") == "original_working_version"


def test_update_ytdlp_success(tmp_path: Path, monkeypatch):
    """Successful update backs up old binary and puts new binary into place."""
    import urllib.request
    import io
    import app.core.tool_manager as tm

    current_exe = tmp_path / "yt-dlp.exe"
    current_exe.write_text("v1", encoding="utf-8")

    fake_download = io.BytesIO(b"v2_binary")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=30: fake_download)
    monkeypatch.setattr(tm, "run_hidden", lambda cmd, timeout=5: (0, "2026.10.01"))
    monkeypatch.setattr(tm, "verify_tool", lambda tool, bin_dir: True)

    success = update_ytdlp(bin_dir=tmp_path)
    assert success is True
    assert current_exe.read_text(encoding="utf-8") == "v2_binary"
    bak_exe = tmp_path / "yt-dlp.exe.bak"
    assert bak_exe.exists()
    assert bak_exe.read_text(encoding="utf-8") == "v1"


def test_auto_repair_on_extraction_error(tmp_path: Path, monkeypatch):
    """Extraction error should trigger auto-repair update and retry the job once."""
    from app.core.download_manager import DownloadManager
    import app.core.download_manager as dm_mod

    # Setup isolated download manager
    mgr = DownloadManager()
    mgr._waiting_queue.clear()
    mgr._repaired_jobs.clear()
    mgr._is_offline = False

    job = DownloadJob(
        job_id="job_extraction_fail",
        url="https://www.youtube.com/watch?v=fail123",
        video_id="fail123",
        title="Test Video",
        channel="Test Channel",
        duration_seconds=120,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir=str(tmp_path),
        created_at="2026-10-02T12:00:00Z",
    )
    mgr._active_job = job

    update_called = []
    def mock_update():
        update_called.append(True)
        return True

    # Monkeypatch tool update
    monkeypatch.setattr("app.core.tool_manager.update_ytdlp", mock_update)

    # Mock _process_next so it doesn't launch real worker
    process_called = []
    monkeypatch.setattr(mgr, "_process_next", lambda: process_called.append(True))

    raw_err = "ERROR: [youtube] fail123: unable to extract signature and n challenge"
    mgr._on_worker_failed(job, raw_err)

    assert len(update_called) == 1, "update_ytdlp was not called on extraction failure"
    assert len(process_called) == 1, "_process_next was not called to retry"
    assert job in mgr._waiting_queue, "Job was not re-queued for retry"
    assert "job_extraction_fail" in mgr._repaired_jobs
