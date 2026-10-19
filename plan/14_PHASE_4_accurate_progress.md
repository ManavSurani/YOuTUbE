# Phase 4 Plan: Accurate Progress Numbers, Whole-Job Total, and Combined Formats

## Goals
Satisfy autonomous requirements:
- **A1**: Total size within 5% of the real file at 5%, 50% and 95%.
- **A2**: Progress bar never goes backwards and never freezes in the audio stage.
- **A3**: Single combined format is not capped at 95%.
- **A4**: Resume keeps the finished video bytes; ETA is whole-job.

---

## Chunk 4.1: Detection of Single vs Dual Stream & Improved Audio Estimate

### Problems Addressed
- `DownloadWorker` had `is_dual_stream = True` passed blindly for all video jobs, so when format `/b` (e.g. format 18, 360p or format 22, 720p) is selected, progress was capped at 95.0% and ghost audio bytes were added.
- The hardcoded audio estimate `duration_seconds * 13000` is 19% to 28% too low for YouTube Opus audio (typically 16,100 to 18,100 B/s).

### Implementation Details (`app/core/downloader.py`)
- Parse `vcodec` and `acodec` in `parse_line` and attach to `ProgressInfo`.
- Detect combined format dynamically: if `vcodec != "none"` and `acodec != "none"`:
  - Set `self.is_dual_stream = False`.
  - Cap at 99.9% instead of 95.0%.
  - Zero ghost audio bytes added to `overall_total`.
- Update audio estimate from `13000` to `17000` B/s (`136 kbps`), accurately reflecting YouTube Opus 128-160 kbps streams.

### Tests (`tests/test_downloader.py`)
- `test_single_format_not_capped_at_95`
- `test_audio_estimate_closer_to_real_audio_size`

---

## Chunk 4.2: Smooth Percentage, Monotonic Progress, and Audio Transition

### Problems Addressed
- At the transition from video to audio, unlatched percentage could drop (e.g. from 85.59% to 82.72%), and the 25% latch rule could reset progress or freeze the bar until the audio download caught up.
- On pause/resume during audio, `_finished_bytes` was reset to 0 in new workers, causing downloaded bytes to drop to audio-only bytes.

### Implementation Details (`app/core/downloader.py` & `app/core/download_manager.py`)
- In `DownloadWorker`:
  - Audio progress interpolation: during audio, interpolate progress smoothly from `pct_at_video_end` to 99.9%:
    `pct = pct_at_video_end + (99.9 - pct_at_video_end) * (audio_done / audio_total)`
  - Remove latch reset: progress is strictly monotonic (`overall = max(self._max_percent, calculated_pct)`).
  - Recover finished video stream bytes: on startup/resume, inspect `job_tmp_dir(self.job_id)` for completed stream files without `.part`, restoring `_finished_bytes`.
  - Pass `initial_done_bytes` from `DownloadManager` on resume.

### Tests (`tests/test_downloader.py`)
- `test_percent_strictly_monotonic_across_stream_boundary`
- `test_percent_never_drops_on_audio_estimate_reconciliation`
- `test_resume_preserves_downloaded_bytes_count`

---

## Chunk 4.3: Real-Download Measurement on 3 Links

### Execution
- Download 3 test links representing short, medium, and long durations.
- Record total size reported by app at 5%, 50%, and 95% vs actual final file size on disk.
- Verify error <= 5% at each checkpoint.
- Document measurements in `docs/verification/parallel_progress_speed_report.md`.

---

## Chunk 4.4: Verification of Phase 4
- Run pytest `tests/test_downloader.py`.
- Run `python tools/check_scope.py --baseline cdfed4e --final`.
- Update `docs/verification/requirements_matrix.md` rows A1, A2, A3, and A4 to PASS.
- Update `docs/verification/autonomy_log.md` and commit.
