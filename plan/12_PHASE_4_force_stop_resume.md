# Phase 4: S3 Resume Polling, 3s Force Stop, and 10s Failure

## Goal
Update `_resume_active_job()` in `DownloadManager`:
1. Check old worker state at a 100ms interval (instead of 500ms).
2. If the old worker has not stopped by attempt 30 (~3 seconds), explicitly call `cancel()` on the lingering worker to force it to stop.
3. If the old worker still has not stopped by attempt 100 (~10 seconds), give up: move the job to failed with exact plain-language reason `"The download could not be resumed. Press Retry."`, emit `job_failed`, clean up active state, and never leave duplicate workers running or start a second worker.
4. If network flaps or toggles rapidly (e.g. 20 consecutive online/offline cycles), maintain strict single-worker concurrency with no worker leaks.

## Why
When internet reconnects, the previous implementation waited 500ms per poll up to 20 attempts (10s total), but never attempted to force-kill or cancel the stuck old worker during those 10s. If the old worker was blocked in a socket or process wait, the user waited 10s only for it to fail with a generic message `"Download stalled and could not resume."`. By polling every 100ms and actively calling `cancel()` at 3s (attempt 30), most lingering processes are cleanly terminated within 3s, allowing resume to proceed immediately. If it still cannot stop after 10s (attempt 100), failing with the explicit D3 message informs the user and allows manual retry.

## Allowed Files
- `app/core/download_manager.py` (implementation)
- `tests/test_download_manager.py` (unit tests)
- `tests/test_download_lanes.py` (update contract of legacy 20-attempts test)
- `docs/verification/test_changes_2.md`
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 4.1: Implementation of 100ms polling, 30-attempt force stop, and 100-attempt failure
1. In `app/core/download_manager.py: _resume_active_job()`:
   - Polling timer: `QTimer.singleShot(100, self._resume_active_job)`.
   - At `self._resume_attempts == 30`:
     - Log warning: `get_logger().warning("Old %s worker did not stop after 3s (attempt 30); force cancelling", self.kind)`
     - If hasattr(old, "cancel"): `old.cancel()`
   - At `self._resume_attempts < 100`:
     - Schedule next poll: `QTimer.singleShot(100, self._resume_active_job)`
   - At `self._resume_attempts >= 100`:
     - Log warning: `get_logger().warning("Old %s worker did not stop after 10s (attempt 100); resume failed", self.kind)`
     - If hasattr(old, "cancel"): `old.cancel()`
     - `self._paused_worker = None`
     - `self._on_worker_failed(job, "The download could not be resumed. Press Retry.")`
2. Update tests:
   - In `tests/test_download_lanes.py`: update `test_resume_gives_up_after_20_attempts_without_starting_second_worker` to `test_resume_force_stops_at_30_and_fails_at_100_attempts` running 101 callbacks and asserting `cancel()` called at 30, failure message at 100, zero second workers started.
   - In `tests/test_download_manager.py`: add tests for 100ms interval, force cancel at attempt 30, failure message at attempt 100, and 20 rapid online/offline network flaps.

## Tests First
1. `test_resume_polling_interval_is_100ms`: asserts `QTimer.singleShot` receives `100` ms.
2. `test_resume_force_cancels_old_worker_at_attempt_30`: asserts `old.cancel()` is called once attempt reaches 30 while `isRunning()` remains True.
3. `test_resume_fails_job_at_attempt_100_with_exact_message`: asserts failure at attempt 100 with `"The download could not be resumed. Press Retry."` and `mgr.active_job is None`.
4. `test_rapid_flapping_network_maintains_single_worker`: toggle online/offline 20 times in rapid succession, verifying worker count never exceeds 1.

## Expected Failure
Before implementation, polling interval is 500ms, cancel is not called at attempt 30, and failure happens at attempt 20 with wrong message `"Download stalled and could not resume."`.

## Done-When
- All tests in `tests/test_download_manager.py` and `tests/test_download_lanes.py` pass.
- Full pytest suite passes (with only baseline failure `test_scope_checker_final`).
- No forbidden files touched.
- Matrix row S3 marked PASS.

## Rollback
If anything breaks, `git checkout -- app/core/download_manager.py tests/test_download_lanes.py tests/test_download_manager.py`.
