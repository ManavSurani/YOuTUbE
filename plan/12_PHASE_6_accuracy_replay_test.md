# Phase 6: A1 Automated Accuracy Replay Test

## Goal
Implement a comprehensive automated replay fixture test in `tests/test_accuracy_replay.py` using deterministic real-world yt-dlp lines in `tests/fixtures/progress_dual.txt`.
Assert:
1. Total size is within 5% of the documented true final size at 5%, 50%, and 95% of job progress.
2. Emitted percentage is strictly monotonic throughout the entire job (never decreases across stream boundaries or estimate reconciliations).
3. Audio stage progress rises smoothly from video completion up to 99.9% without freezing at 85% or stalling on latch checks.
4. Single combined format jobs uncap cleanly and reach >= 99% before merge.
5. Mid-job resumes preserve `initial_done_bytes` and `floor_percent`, maintaining seamless continuity.

## Why
Row A1 in the status report was marked PARTIAL because earlier tests only examined fragmented components in isolation. An automated end-to-end replay fixture guarantees that all progress metrics (bytes, totals, speeds, ETAs, percentages, stage transitions) work harmoniously under realistic conditions and adhere to the strict 5% total tolerance and monotonicity contracts.

## Allowed Files
- `tests/fixtures/progress_dual.txt` (fixture)
- `tests/test_accuracy_replay.py` (unit tests)
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 6.1: Fixture Creation and Replay Test Suite
1. Create `tests/fixtures/progress_dual.txt`:
   - Realistic 120s 1080p download: video stream (AV1, 18 MB, status downloading -> finished), audio stream (Opus, 2.04 MB, status downloading -> finished), merger output.
   - True documented final size: 20,040,000 bytes.
2. Create `tests/test_accuracy_replay.py`:
   - `test_dual_stream_fixture_replay_total_accuracy_and_monotonicity`:
     - Reads `progress_dual.txt` through `DownloadWorker`.
     - Validates total size within 5% at 5%, 50%, 95%.
     - Validates monotonicity of percentage (`pct[i] >= pct[i-1]`).
     - Validates audio stage progress advances smoothly.
   - `test_single_stream_fixture_replay_uncaps_above_95`:
     - Replays combined stream lines; validates `pct >= 99.0` before finish.
   - `test_mid_stream_resume_preserves_bytes_and_floor`:
     - Replays resume scenario; validates `done_bytes >= initial_done_bytes` and `pct >= floor_percent`.

## Tests First
All tests in `test_accuracy_replay.py` will be executed against the existing engine and verified.

## Done-When
- All tests in `tests/test_accuracy_replay.py` pass.
- Full pytest suite passes without failures.
- Matrix row A1 marked PASS.

## Rollback
`rm tests/fixtures/progress_dual.txt tests/test_accuracy_replay.py`.
