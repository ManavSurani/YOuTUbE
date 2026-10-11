"""
Phase 1 tests for downloader.py — command builders and progress parser.

These tests cover:
- Exact command-string assertions (Chunk 1.5)
- Parser with real-format YTPROG lines (Chunk 1.2)
- Safe temp cleanup only inside TMP_DIR (Chunk 1.4)
- Contract test proving no subprocess import outside proc.py (R1)
"""

import os
import subprocess
from pathlib import Path

import pytest

from app.core.downloader import (
    DownloadWorker,
    ParsedOutput,
    ProgressInfo,
    build_audio_cmd,
    build_video_cmd,
    parse_line,
    resolve_final_path,
)
from app.core.paths import BIN_DIR, TMP_DIR


# ---------------------------------------------------------------------------
# Command builder tests — Chunk 1.5
# ---------------------------------------------------------------------------

class TestBuildVideoCmd:
    def test_best_quality_includes_mkv(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--merge-output-format" in cmd
        idx = cmd.index("--merge-output-format")
        assert cmd[idx + 1] == "mkv"

    def test_best_quality_format_selector(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "bv*+ba/b"

    def test_height_format_selector(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", height=1080, job_id="j1")
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "bv*[height<=1080]+ba/b[height<=1080]"

    def test_no_print_flag(self):
        """B1 fix: --print must NOT be in the video command."""
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--print" not in cmd

    def test_has_print_to_file(self):
        """B3 fix: path must be written to a UTF-8 file, not stdout."""
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--print-to-file" in cmd

    def test_uses_tmp_dir(self):
        """B4 fix: temp dir must be app-owned TMP_DIR, not user Downloads."""
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        tmp_flag = f"temp:{TMP_DIR}"
        assert any(tmp_flag in arg for arg in cmd)

    def test_has_progress_template_with_marker(self):
        """B2 fix: template must contain YTPROG marker, not bare 'download:'."""
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        combined = " ".join(cmd)
        assert "YTPROG" in combined
        # The old broken prefix must NOT appear standalone
        assert "download:%(progress" not in combined

    def test_windows_filenames_flag(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--windows-filenames" in cmd

    def test_no_playlist(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--no-playlist" in cmd

    def test_output_template_has_id(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        idx = cmd.index("-o")
        assert "%(id)s" in cmd[idx + 1]

    def test_embed_metadata(self):
        cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", job_id="j1")
        assert "--embed-metadata" in cmd


class TestBuildAudioCmd:
    def test_best_original_uses_ba_x(self):
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="best", job_id="j2")
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "ba"
        assert "-x" in cmd

    def test_mp3_has_format_and_quality(self):
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="mp3", job_id="j2")
        assert "--audio-format" in cmd
        idx = cmd.index("--audio-format")
        assert cmd[idx + 1] == "mp3"
        assert "--audio-quality" in cmd

    def test_mp3_has_embed_thumbnail(self):
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="mp3", job_id="j2")
        assert "--embed-thumbnail" in cmd

    def test_opus_has_embed_thumbnail(self):
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="opus", job_id="j2")
        assert "--embed-thumbnail" in cmd

    def test_flac_has_format(self):
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="flac", job_id="j2")
        idx = cmd.index("--audio-format")
        assert cmd[idx + 1] == "flac"

    def test_no_print_flag(self):
        """B1 fix."""
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="mp3", job_id="j2")
        assert "--print" not in cmd

    def test_has_print_to_file(self):
        """B3 fix."""
        cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="mp3", job_id="j2")
        assert "--print-to-file" in cmd

    def test_embed_metadata_always_present(self):
        for fmt in ("best", "mp3", "opus", "flac", "m4a"):
            cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt=fmt, job_id="j2")
            assert "--embed-metadata" in cmd, f"--embed-metadata missing for fmt={fmt}"


# ---------------------------------------------------------------------------
# Parser tests — Chunk 1.2
# ---------------------------------------------------------------------------

class TestParseLineProgress:
    def _make_line(self, status="downloading", dl=52428800, tot=100663296,
                   est=0, speed=12582912, eta=88,
                   vcodec="avc1.640028", acodec="mp4a.40.2"):
        """Build a realistic YTPROG line (what yt-dlp actually emits)."""
        return (
            f"[download] YTPROG|{status}|{dl}|{tot}|{est}|{speed}|{eta}"
            f"|{vcodec}|{acodec}"
        )

    def test_percent_calculation(self):
        line = self._make_line(dl=52428800, tot=104857600)
        res = parse_line(line)
        assert res.kind == "progress"
        assert res.progress is not None
        assert abs(res.progress.percent - 50.0) < 0.1

    def test_speed_formatted(self):
        line = self._make_line(speed=12582912)  # 12 MB/s
        res = parse_line(line)
        assert "MB/s" in res.progress.speed

    def test_eta_formatted(self):
        line = self._make_line(eta=88)  # 01:28
        res = parse_line(line)
        assert ":" in res.progress.eta
        assert res.progress.eta == "01:28"

    def test_stage_video_from_vcodec(self):
        line = self._make_line(vcodec="avc1.640028", acodec="none")
        res = parse_line(line)
        assert res.progress.stage == "Downloading video"

    def test_stage_audio_from_acodec(self):
        line = self._make_line(vcodec="none", acodec="mp4a.40.2")
        res = parse_line(line)
        assert res.progress.stage == "Downloading audio"

    def test_na_speed_returns_empty(self):
        line = "[download] YTPROG|downloading|1000|10000|0|NA|NA|avc1|mp4a"
        res = parse_line(line)
        assert res.kind == "progress"
        assert res.progress.speed == ""
        assert res.progress.eta == ""

    def test_percent_never_above_100(self):
        line = self._make_line(dl=100663296, tot=100663296)
        res = parse_line(line)
        assert res.progress.percent <= 100.0

    def test_zero_total_does_not_crash(self):
        line = "[download] YTPROG|downloading|0|0|0|1024|10|avc1|none"
        res = parse_line(line)
        assert res.kind == "progress"
        assert res.progress.percent == 0.0

    def test_uses_estimate_when_total_zero(self):
        line = "[download] YTPROG|downloading|50000|0|100000|1024|10|avc1|none"
        res = parse_line(line)
        assert res.kind == "progress"
        assert abs(res.progress.percent - 50.0) < 1.0


class TestParseLineStage:
    def test_merger_tag(self):
        res = parse_line("[Merger] Merging formats into 'video.mkv'")
        assert res.kind == "stage"
        assert res.stage == "Merging"

    def test_extract_audio_tag(self):
        res = parse_line("[ExtractAudio] Destination: song.mp3")
        assert res.kind == "stage"
        assert res.stage == "Converting audio"

    def test_ytpost_merger(self):
        res = parse_line("[postprocess] YTPOST|started|Merger")
        assert res.kind == "stage"
        assert res.stage == "Merging"

    def test_ytpost_extract_audio(self):
        res = parse_line("[postprocess] YTPOST|started|ExtractAudio")
        assert res.kind == "stage"
        assert res.stage == "Converting audio"

    def test_garbage_returns_other(self):
        res = parse_line("[info] some random informational line")
        assert res.kind == "other"

    def test_old_broken_download_prefix_not_parsed_as_progress(self):
        """B2 regression: old 'download:' prefix lines must NOT be parsed as progress."""
        line = "download: 52.4%|4.82MiB/s|00:08|15.20MiB|29.01MiB"
        res = parse_line(line)
        # Should be 'other' since there's no YTPROG marker
        assert res.kind == "other"


# ---------------------------------------------------------------------------
# Path resolver tests — Chunk 1.3
# ---------------------------------------------------------------------------

class TestResolvePathFile:
    def test_reads_path_file(self, tmp_path):
        target = tmp_path / "clip [abc123].mkv"
        target.write_bytes(b"fake")
        path_file = tmp_path / "job.path"
        path_file.write_text(str(target) + "\n", encoding="utf-8")

        result = resolve_final_path(path_file, "abc123", tmp_path)
        assert result == str(target)

    def test_fallback_by_video_id(self, tmp_path):
        """If path file is absent, search by [video_id] in filename."""
        target = tmp_path / "My Video [abc123].mkv"
        target.write_bytes(b"fake")
        path_file = tmp_path / "job.path"  # does not exist

        result = resolve_final_path(path_file, "abc123", tmp_path)
        assert result == str(target)

    def test_ignores_part_files(self, tmp_path):
        part = tmp_path / "My Video [abc123].mkv.part"
        part.write_bytes(b"partial")
        path_file = tmp_path / "job.path"

        result = resolve_final_path(path_file, "abc123", tmp_path)
        # Should not return the .part file
        assert result == "" or ".part" not in result

    def test_missing_everything_returns_empty(self, tmp_path):
        path_file = tmp_path / "job.path"
        result = resolve_final_path(path_file, "xyz999", tmp_path)
        assert result == ""

    def test_unicode_path(self, tmp_path):
        """B3: Unicode filenames (emoji, Japanese) must resolve correctly."""
        target = tmp_path / "日本語タイトル [abc123].mkv"
        target.write_bytes(b"fake")
        path_file = tmp_path / "job.path"
        path_file.write_text(str(target) + "\n", encoding="utf-8")

        result = resolve_final_path(path_file, "abc123", tmp_path)
        assert result == str(target)


# ---------------------------------------------------------------------------
# Temp-cleanup tests — Chunk 1.4
# ---------------------------------------------------------------------------

class TestSafeCancel:
    def test_cancel_only_removes_job_files_in_tmp(self, tmp_path, monkeypatch):
        """B4 fix: cancelling must never touch files in the user's Downloads folder."""
        import app.core.paths as paths_mod
        import app.core.downloader as dl_mod

        fake_tmp = tmp_path / "app_tmp"
        fake_tmp.mkdir()
        monkeypatch.setattr(paths_mod, "TMP_DIR", fake_tmp)
        monkeypatch.setattr(dl_mod, "TMP_DIR", fake_tmp)

        # Simulate a .part file in the app tmp
        job_id = "test-job-001"
        app_part = fake_tmp / f"{job_id}_clip.mkv.part"
        app_part.write_text("partial")

        # Simulate an unrelated .part file in user Downloads (different tmp_path subfolder)
        user_downloads = tmp_path / "Downloads"
        user_downloads.mkdir()
        user_part = user_downloads / "firefox_download.part"
        user_part.write_text("browser partial")

        worker = DownloadWorker(
            cmd=["echo", "test"],
            out_dir=user_downloads,
            job_id=job_id,
        )
        worker._cleanup_job_tmp()

        # App tmp file should be gone
        assert not app_part.exists()
        # User downloads file must be untouched
        assert user_part.exists(), "B4: cancel must NOT delete files outside TMP_DIR"


# ---------------------------------------------------------------------------
# No-subprocess-outside-proc scan — Rule R1
# ---------------------------------------------------------------------------

def test_no_subprocess_outside_proc(tmp_path):
    """R1: only app/core/proc.py may import subprocess."""
    import ast
    app_dir = Path(__file__).parent.parent / "app"
    violations = []
    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "proc.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        violations.append(str(py_file))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "subprocess":
                    violations.append(str(py_file))
    assert violations == [], f"subprocess imported outside proc.py: {violations}"


# ---------------------------------------------------------------------------
# Worker signal presence
# ---------------------------------------------------------------------------

def test_download_worker_signals():
    worker = DownloadWorker(["dummy"], job_id="sig-test")
    assert hasattr(worker, "stage")
    assert hasattr(worker, "progress")
    assert hasattr(worker, "finished")
    assert hasattr(worker, "failed")
    assert hasattr(worker, "paused")
    assert hasattr(worker, "pause")
    assert hasattr(worker, "cancel")


# ---------------------------------------------------------------------------
# Chunk 3 Tests: Self-correcting progress latch & real log sequence
# ---------------------------------------------------------------------------

def test_parse_line_first_fragment_equal_gives_zero_percent():
    line = "[download] YTPROG|downloading|712|NA|712|526.1|NA|vp09.00.40.08|none"
    res = parse_line(line)
    assert res.kind == "progress"
    assert res.progress is not None
    assert res.progress.percent == 0.0
    assert res.progress.total_bytes == 0
    assert res.progress.is_exact is False


def test_download_worker_fluctuating_estimates_sequence(monkeypatch):
    """Test user sequence: 712 B, 1.1 MB, 276 KB, 1.39 GB, 463 MB, 2.04 GB."""
    lines = [
        # 1. Fragment 1: 712 B / 712 B estimate -> must be 0%
        "[download] YTPROG|downloading|712|NA|712|526|NA|vp09.00.40.08|none\n",
        # 2. 1.1 MB estimate (1,107,872 B) with 1 MB downloaded -> 94.6% video (80.4% scaled)
        "[download] YTPROG|downloading|1048576|NA|1107872|526|NA|vp09.00.40.08|none\n",
        # 3. Estimate drops to 276 KB (276,968 B) -> shift > 25%, dl = 1736 B -> 0.63% video (0.53% scaled)
        "[download] YTPROG|downloading|1736|NA|276968|526|NA|vp09.00.40.08|none\n",
        # 4. Estimate expands to 1.39 GB (1,390,810,372 B) -> shift > 25%, dl = 1.78 MB -> 0.13% video (0.11% scaled)
        "[download] YTPROG|downloading|1788030|NA|1390810372|1145527|NA|vp09.00.40.08|none\n",
        # 5. Estimate shifts to 463 MB (463,695,780 B) -> shift > 25%, dl = 1.78 MB -> 0.38% video (0.33% scaled)
        "[download] YTPROG|downloading|1789054|NA|463695780|1236809|318|vp09.00.40.08|none\n",
        # 6. Estimate shifts to 2.04 GB (2,040,000,000 B) -> shift > 25%, dl = 10 MB -> 0.49% video (0.42% scaled)
        "[download] YTPROG|downloading|10000000|NA|2040000000|2000000|1000|vp09.00.40.08|none\n",
        # 7. Video finishes: 2.04 GB downloaded, finished -> must reach video stage end 85.0%
        "[download] YTPROG|finished|2040000000|NA|2040000000|2000000|0|vp09.00.40.08|none\n",
    ]

    class FakeProc:
        def __init__(self, output_lines):
            self.stdout = output_lines
            self.returncode = 0
        def wait(self): pass

    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: FakeProc(lines))

    worker = DownloadWorker(["dummy"], is_dual_stream=True, job_id="test-fluct")
    emitted = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted.append(pct))
    worker.run()

    # Reading 1: 0.0%
    assert emitted[0] == 0.0

    # Reading 2: early spike to 80.4%
    assert abs(emitted[1] - 80.4) < 1.0

    # Reading 3: estimate dropped by >25% (1.1MB -> 276KB), bar adjusts to 0.53% (does not stay at 80.4%)
    assert emitted[2] < 1.0

    # Reading 4: estimate expanded by >25% (276KB -> 1.39GB), bar adjusts to 0.11%
    assert emitted[3] < 1.0

    # Floor never violated (all values >= 0.0)
    assert all(val >= 0.0 for val in emitted)

    # Ends at video stage end (85.0%) before final completion (100.0%)
    assert emitted[-2] == 85.0
    assert emitted[-1] == 100.0


def test_download_worker_video_to_audio_transition(monkeypatch):
    """Test video-to-audio transition: bar stays at or above 85, no false downward correction."""
    lines = [
        # Video stream ends at 85.0%
        "[download] YTPROG|finished|1000000|1000000|NA|1000|0|avc1|none\n",
        # Audio stream starts: dl = 1 KB, tot = 86.8 MB (86,800,000 B) -> 85.0%
        "[download] YTPROG|downloading|1000|86800000|NA|500|100|none|mp4a\n",
        # Audio stream fluctuating estimate: tot = NA, est = 120 MB (120,000,000 B), dl = 10 MB
        "[download] YTPROG|downloading|10000000|NA|120000000|500|100|none|mp4a\n",
        # Audio stream finished
        "[download] YTPROG|finished|86800000|86800000|NA|500|0|none|mp4a\n",
        # Merger stage
        "[Merger] Merging formats into 'video.mkv'\n",
    ]

    class FakeProc:
        def __init__(self, output_lines):
            self.stdout = output_lines
            self.returncode = 0
        def wait(self): pass

    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: FakeProc(lines))

    worker = DownloadWorker(["dummy"], is_dual_stream=True, job_id="test-trans")
    emitted = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted.append(pct))
    worker.run()

    # Audio stream readings must all be >= 85.0
    audio_readings = emitted[1:]
    assert all(val >= 85.0 for val in audio_readings)

    # Merger reading must be at least 95.0
    assert emitted[-1] >= 95.0


def test_early_garbage_sub_100k_estimate_gives_zero_percent():
    line = "[download] YTPROG|downloading|400|NA|712|526|NA|vp09.00.40.08|none"
    res = parse_line(line)
    assert res.kind == "progress"
    assert res.progress is not None
    assert res.progress.percent == 0.0
    assert res.progress.total_bytes == 0
    assert res.progress.is_exact is False


def test_normal_estimate_above_100k_is_used():
    line = "[download] YTPROG|downloading|500000|NA|1100000|1000000|10|avc1|none"
    res = parse_line(line)
    assert res.kind == "progress"
    assert res.progress is not None
    assert abs(res.progress.percent - (500000 / 1100000 * 100.0)) < 0.1
    assert res.progress.total_bytes == 1100000
    assert res.progress.is_exact is False


def test_small_real_file_finishes_at_stage_end(monkeypatch):
    """Small real file: estimate stays under 100 KB, then finished reaches stage end."""
    lines = [
        # Sub-100KB estimate noise -> 0.0%
        "[download] YTPROG|downloading|10000|NA|50000|1000|10|avc1|none\n",
        # Finished line -> exact total used even if under 100 KB
        "[download] YTPROG|finished|50000|NA|50000|1000|0|avc1|none\n",
    ]

    class FakeProc:
        def __init__(self, output_lines):
            self.stdout = output_lines
            self.returncode = 0
        def wait(self): pass

    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: FakeProc(lines))

    worker = DownloadWorker(["dummy"], is_dual_stream=True, job_id="test-small")
    emitted = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted.append(pct))
    worker.run()

    # Reading 1 was sub-100KB estimate -> 0.0%
    assert emitted[0] == 0.0
    # Reading 2 was finished -> reaches 85.0%
    assert emitted[-2] == 85.0
    # Process exit -> 100.0%
    assert emitted[-1] == 100.0


