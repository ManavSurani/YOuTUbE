# Phase 5: S4 Watchdog Default 90s

## Goal
1. Update `stall_timeout_seconds` default in `DownloadWorker` from 60.0s to 90.0s.
2. Ensure the watchdog stall detection never triggers during merging or post-processing operations (e.g. `merging`, `converting`, `embedding`, `metadata`, `processing`).
3. Ensure at most 3 stall restarts per job before moving to failure.

## Why
On high-latency connections or during YouTube throttle dips, a 60-second stall timeout proved too aggressive, causing premature aborts on large fragments or slow initial socket handshakes. Increasing the default stall timeout to 90 seconds (Decision D4) provides sufficient headroom while still protecting users from permanently frozen downloads. Additionally, CPU-heavy post-processing tasks like ffmpeg audio conversion or video merging can take tens of seconds with minimal stdout; the watchdog must never mistake these operations for network stalls.

## Allowed Files
- `app/core/downloader.py` (implementation)
- `tests/test_downloader.py` (unit tests)
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 5.1: Default Timeout and Post-Processing Safety
1. In `app/core/downloader.py`:
   - In `DownloadWorker.__init__`: change `stall_timeout_seconds: float = 90.0` (both signature and `max(0.05, float(stall_timeout_seconds or 90.0))`).
   - In `_watchdog_loop()`: broaden `is_merging` to `is_post_processing` checking for `"merg"`, `"convert"`, `"embed"`, `"metadata"`, `"post"`, or `"process"` in `self._current_stage.lower()`.
   - Ensure `stall_count >= 3` logic remains intact.
2. In `tests/test_downloader.py`:
   - Add unit test checking default `stall_timeout_seconds == 90.0`.
   - Add unit test checking that converting audio and embedding metadata do not trigger watchdog.
   - Add unit test checking that elapsed time under 90s does not trigger watchdog.

## Tests First
1. `test_watchdog_default_stall_timeout_is_90_seconds`
2. `test_stall_watchdog_skips_during_converting_audio_and_postprocessing`
3. `test_watchdog_boundary_does_not_fire_at_65s_fires_at_91s`

## Expected Failure
Before change:
- `DownloadWorker(["dummy"]).stall_timeout_seconds` is `60.0`, failing the 90.0s default test.
- Post-processing stages like `Converting audio` do not match `"merg" in self._current_stage.lower()` and get killed by watchdog.

## Done-When
- All watchdog unit tests pass.
- Full test suite passes (with only baseline failure `test_scope_checker_final`).
- No forbidden files touched.
- Matrix row S4 marked PASS.

## Rollback
`git checkout -- app/core/downloader.py tests/test_downloader.py`.
