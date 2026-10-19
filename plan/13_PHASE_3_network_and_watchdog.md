# Phase 3 Plan: Network Flapping Debounce and Download Stall Watchdog

## Goals
Satisfy autonomous requirements:
- **S3**: Rapid online/offline toggling never leaves a stuck or double worker.
- **S4**: Stall watchdog restarts a silent download and never during merging.

---

## Chunk 3.1: Network Flapping Debouncer in `download_manager.py`

### Motivation & Problems Addressed
- Rapid online/offline transitions can fire while an existing `DownloadWorker` is shutting down or being paused.
- Redundant calls to `set_online(True)` when already online must be no-ops.
- If an old worker is still alive when coming online, `_resume_active_job` must poll up to 20 times (every 500ms) and never spawn a second worker.
- If the old worker does not terminate within the 20 attempts (10s total), log a warning, cancel the stale worker, and transition the active job to failed state rather than leaving it permanently stuck.

### Test Specification (`tests/test_download_manager.py`)
1. `test_flapping_network_does_not_spawn_multiple_workers`:
   Simulate repeated toggles (`set_online(False)`, `set_online(True)`, `set_online(False)`, `set_online(True)`). Verify only one worker is created/running.
2. `test_resume_waits_for_old_worker_to_exit`:
   Simulate old worker running (`isRunning() == True`). Call `set_online(True)`. Verify new worker is not started until old worker stops.

### Implementation Details (`app/core/download_manager.py`)
- Guard `set_online(online)`:
  If `online == (not self._is_offline)`: return immediately (no-op on duplicate state).
- In `_resume_active_job`:
  - Check `isRunning()` on both `self._paused_worker` and `self._worker`.
  - Re-check with `QTimer.singleShot(500, self._resume_active_job)`.
  - On attempt > 20: log warning, cancel old worker, and fail job via `self._on_worker_failed(job, "Download stalled and could not resume.")` to prevent zombie state.

---

## Chunk 3.2: Download Stall Watchdog in `downloader.py`

### Motivation & Problems Addressed
- Network hangs, dropped packets, or CDN stalls can cause `yt-dlp` to block silently with zero output indefinitely.
- The user is left looking at a frozen progress bar with no error or recovery.
- A watchdog timer must detect lack of output for 60 seconds during active download stages, kill the stalled process, and restart via `--continue`.
- Safety constraints:
  - Watchdog MUST NOT fire during merging stages (`"Merging"`, `"Merging formats"`).
  - Watchdog MUST NOT fire when paused or cancelled.
  - Watchdog allows at most 3 stall restarts per job; exceeding 3 emits `failed("Download stalled repeatedly. Please check your internet connection.")`.

### Test Specification (`tests/test_downloader.py`)
1. `test_stall_watchdog_triggers_after_timeout`:
   With a short timeout (e.g. 0.2s), mock a silent process that outputs no lines. Verify watchdog terminates process and triggers restart / stall notification.
2. `test_stall_watchdog_does_not_trigger_during_merging`:
   With `_current_stage = "Merging formats"`, simulate 0.3s of silence beyond timeout. Verify watchdog does not trigger.
3. `test_stall_watchdog_max_retries`:
   Simulate 3 repeated stalls. Verify on the 4th stall, worker terminates and emits `failed("Download stalled repeatedly. Please check your internet connection.")`.

### Implementation Details (`app/core/downloader.py`)
- Add `stall_timeout_seconds: float = 60.0` parameter to `DownloadWorker.__init__`.
- Maintain `self._last_output_time = time.time()`, `self._current_stage = ""`, `self._stalled = False`, and `self._watchdog_stop_event = threading.Event()`.
- Run background watchdog thread during `run()`:
  - Checks elapsed time every 0.1s - 0.5s.
  - If `time.time() - self._last_output_time > self.stall_timeout_seconds`:
    - Check stage: if `"merg"` in `self._current_stage.lower()`: do not fire.
    - Check state: if `self._is_paused` or `self._is_cancelled`: do not fire.
    - Trigger stall: set `self._stalled = True`, kill `self._proc`.
- In `run()`:
  - Enclose process execution in `while not self._is_cancelled and not self._is_paused:` loop.
  - If `self._stalled`:
    - Increment `stall_count`.
    - If `stall_count > 3`: cleanup and emit `failed(...)`.
    - Else: emit `stage("Download stalled. Reconnecting…")` and continue loop to re-execute `start_hidden(self.cmd)`.

---

## Chunk 3.3: Verification of Phase 3
- Run pytest `tests/test_download_manager.py` and `tests/test_downloader.py`.
- Run `python tools/check_scope.py --baseline cdfed4e --final`.
- Update `docs/verification/requirements_matrix.md` rows S3 and S4 to PASS.
- Update `docs/verification/autonomy_log.md` and commit.
