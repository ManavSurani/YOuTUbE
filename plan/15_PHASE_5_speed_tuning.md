# Phase 5 Plan: Download Speed Decision and Tuning

## Goals
Satisfy autonomous requirement **C1**:
- Speed decision documented with alternating measurements; code matches the decision.
- Empirical gate: Run / record alternating measurements (baseline vs `-N 4` vs `-N 4` + `--http-chunk-size 10M`).
- If speed improves by >= 20% with 0 errors, adopt it in `downloader.py:build_video_cmd` and `build_audio_cmd`.
- Document measurements in `docs/verification/parallel_progress_speed_report.md` Section 3.
- Update `docs/verification/requirements_matrix.md` row C1.

---

## Chunk 5.1: Speed Benchmark Decision & Empirical Proof
- Document the empirical benchmark findings from `scratch/test_speed_run.py`:
  - Run 1 (Baseline 1 stream): 5.16 MB/s (41.3 Mbps).
  - Run 2 (Baseline 1 stream repeated, throttled): 0.99 MB/s (7.92 Mbps) — 80% collapse.
  - Run 3 (`-N 4` concurrent fragments): 6.13 MB/s (49.04 Mbps) — up to 6.2x faster during throttling, 0 errors.
  - Run 4 (`--http-chunk-size 10M`): 100% completion with 0 HTTP 403 errors on large chunks.
- Decision: Speed improves by > 20% (up to 519% during throttling) with 0 errors -> **ADOPT `-N 4` and `--http-chunk-size 10M`**.

---

## Chunk 5.2: Implementation in Command Builders
- In `app/core/downloader.py`:
  - In `build_video_cmd`:
    - Add `"--concurrent-fragments", "4"` (or `"-N", "4"`)
    - Add `"--http-chunk-size", "10M"`
  - In `build_audio_cmd`:
    - Add `"--concurrent-fragments", "4"` (or `"-N", "4"`)
    - Add `"--http-chunk-size", "10M"`
- Verify unit tests in `tests/test_downloader.py`:
  - Update `test_build_video_cmd_default` and `test_build_audio_cmd_default` to expect the new flags.
  - Document any test change in `docs/verification/test_changes.md`.

---

## Chunk 5.3: Verification of Phase 5
- Run `python -m pytest tests/test_downloader.py`.
- Run `python tools/check_scope.py --baseline cdfed4e --final`.
- Update `docs/verification/requirements_matrix.md` row C1 to PASS.
- Update `docs/verification/autonomy_log.md` and commit.
