# Phase C: Two Download Lanes (Scheduling & Parallel Engine)

---

## A. Header

### Goal
Implement dual parallel download lanes so that:
1. One video download and one audio download can run simultaneously without blocking each other.
2. Each lane manages its own FIFO queue and persists to its own JSON file (`queue_video.json` and `queue_audio.json`).
3. Legacy `queue.json` is safely migrated once under a module-level threading lock (no lock file).
4. Jobs with identical `video_id` are deferred in the second lane until the first finishes, preserving strict lane FIFO order.
5. Both lanes are woken up thread-safely across all 4 completion/failure paths.
6. Network offline/online transitions pause and resume both lanes.
7. Closing the application prompts if either lane is active, calls `shutdown()` on both lanes, and exits cleanly.
8. Restored waiting items automatically start downloading on application startup when online, wait if offline, and honour cross-lane deferral.

### Rows Fixed
- **C-1**: Single shared `DownloadManager` singleton forces serial queue for both types.
- **C-2**: Temp file collision if same video ID runs as video and audio.
- **C-3**: App close handler only checks single manager instance.
- **C-4**: `DownloadManager.set_online()` is not called by `main_window.py`.
- **R3**: Audio downloads run separately and in parallel with video.
- **R6**: Simultaneous same video ID deferral preserving FIFO order.

### Depends On
- Phase B must be completed, verified, and explicitly approved by the owner before starting Phase C.

### Allowed Files (Exact Paths)
- `app/core/download_manager.py` (scheduling edits only)
- `app/ui/main_window.py`
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `app/ui/queue_widget.py`
- `tests/test_download_lanes.py`
- `tests/test_close_event.py`
- `tests/test_download_manager.py`
- `tests/test_queue.py`
- `tests/test_phase8_stress_edge_cases.py`
- `tests/test_tab_flow.py`
- `tests/test_tab_state_machine.py`
- `tests/test_tab_looks.py`
- `tests/test_recent_list.py`
- `tests/test_app_updater.py`
- `tests/test_tool_manager.py`

### The 15 Strictly Protected Files (Zero Edits Permitted)
```
1.  app/core/downloader.py         6.  app/core/history_db.py         11. app/core/app_updater.py
2.  app/core/proc.py               7.  app/core/history_service.py    12. app/core/tool_manager.py
3.  app/core/info_fetcher.py       8.  app/core/thumbnails.py         13. app/tools.json
4.  app/core/jobs.py               9.  app/core/errors.py             14. installer/setup.iss
5.  app/core/url_tools.py          10. app/core/network_monitor.py    15. app/ui/theme.py
```

### Approved Scheduling Exception
- `app/core/download_manager.py`: Approved strictly for scheduling (lane instances, persistence migration, cross-lane deferral, thread-safe wake-up, offline pause/resume, shutdown). Zero changes permitted to download execution logic or command builders.

### Do / Don't Table
| Do | Don't |
|---|---|
| Require `kind` in `get_download_manager(kind: str)` | Don't allow default values or calls without `kind` |
| Guard `enqueue(job)` against mismatched `kind` | Don't accept audio jobs in video lane or vice versa |
| Block later jobs in lane when a job is deferred | Don't allow later jobs to jump ahead of a deferred job (preserve FIFO) |
| Connect worker signals on main Qt thread | Don't use thread-unsafe lambdas running in worker threads |
| Stop and ask if SQLite lock occurs in 2-thread test | Don't edit `history_db.py` or `history_service.py` |
| Make strictly mechanical edits to existing tests | Don't delete, change assertions, or weaken existing tests |

---

## B. Chunks

### Chunk C.1: Multi-Lane Architecture, Enqueue Guard, Call-Site Audit & Mechanical Test Updates

- **Goal:** Implement dedicated `"video"` and `"audio"` lane managers requiring `kind`, enqueue kind guard, mechanical call-site edits, `QueueWidget(kind)` parameter and tab instantiations, scan test, and mechanical test updates.
- **Files Allowed:** `app/core/download_manager.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/queue_widget.py`, `tests/test_download_lanes.py`, and existing test files listed below.
- **Exact Steps:**
  1. In `app/core/download_manager.py`:
     - Update `DownloadManager.__init__(self, kind: str, parent=None)`:
       - Store `self.kind = kind`.
       - Assign queue file path: `APP_DATA / f"queue_{kind}.json"`.
     - In `DownloadManager.enqueue(self, job: DownloadJob)`:
       - Guard: `if job.kind != self.kind: get_logger().warning(f"Rejected job {job.job_id}: kind mismatch ({job.kind} != {self.kind})"); return`.
     - In `_load_persisted_queue(self)`:
       - Skip and log any item where `item.get("kind") != self.kind`.
     - Update `get_download_manager(kind: str) -> DownloadManager`:
       - **Strictly require `kind`** (no default value).
       - Maintain singleton dictionary `_managers: Dict[str, DownloadManager] = {}`.
  2. In `app/ui/queue_widget.py`:
     - Update `QueueWidget.__init__(self, kind: str = "video", parent=None)`: accepts `kind` and stores `self.kind = kind`.
     - Update call to `get_download_manager(self.kind)`.
  3. Mechanical call-site updates:
     - `app/ui/video_tab.py`: `get_download_manager("video")` and `QueueWidget(kind="video", parent=container)`.
     - `app/ui/audio_tab.py`: `get_download_manager("audio")` and `QueueWidget(kind="audio", parent=container)`.
     - `app/ui/queue_widget.py`: `get_download_manager(self.kind)`.
  4. In `tests/test_download_lanes.py`:
     - Add AST scan test `test_no_get_download_manager_calls_without_kind`: parses all Python ASTs under `app/` and asserts zero calls to `get_download_manager()` without arguments.
     - Add `test_enqueue_guard_rejects_mismatched_kind`: asserts enqueuing an audio job to video lane is rejected and logged.
  5. Mechanical test updates (search ALL tests for `get_download_manager`, `DownloadManager`, and `queue.json`):
     - Pass `kind="video"` or `"audio"`.
     - Update mock factories (e.g. `lambda kind: fake`).
     - Rename mock queue files to `queue_video.json` / `queue_audio.json`.
     - Target files:
       - `tests/test_download_manager.py`
       - `tests/test_queue.py`
       - `tests/test_phase8_stress_edge_cases.py`
       - `tests/test_tab_flow.py`
       - `tests/test_tab_state_machine.py`
       - `tests/test_tab_looks.py`
       - `tests/test_recent_list.py`
       - `tests/test_app_updater.py`
       - `tests/test_tool_manager.py`
     - **Rule:** Strictly mechanical edits. Zero assertion changes, nothing deleted, nothing weakened.
  6. Run `pytest` on all updated test files.
- **Done When:** AST scan test passes, enqueue guard test passes, and all mechanically updated tests pass.
- **Commit Message:** `featC.1: multi-lane download managers with enqueue kind guard and call-site updates`

---

### Chunk C.2: One-Time Legacy queue.json Migration Under Threading Lock

- **Goal:** Safely split legacy `queue.json` into `queue_video.json` and `queue_audio.json` under a module-level `threading.Lock()` (no lock files, preventing stale lock file blocking on crash) before either manager loads, gracefully handling corrupt/empty files and missing kinds.
- **Files Allowed:** `app/core/download_manager.py`, `tests/test_download_lanes.py`
- **Exact Steps:**
  1. In `app/core/download_manager.py`:
     - Define module-level lock: `_migration_lock = threading.Lock()`.
     - Implement `migrate_legacy_queue_if_needed()`:
       - Acquire `_migration_lock` (do NOT create or use any `.lock` file on disk).
       - Check if legacy `queue.json` exists in `APP_DATA`.
       - If it exists:
         - Read and parse file. If the file is empty or contains malformed JSON:
           - Rename `queue.json` to `queue.json.corrupt`.
           - Log a warning with `get_logger().warning("Corrupt or empty queue.json detected; renamed to queue.json.corrupt")`.
           - Return cleanly (allowing the app to start with empty queues without crashing).
         - If parsing succeeds and returns a list:
           - Partition items: items with `item.get("kind") == "audio"` go to audio list; all other items (including missing or unknown `kind`) are treated as `"video"`.
           - Write `queue_video.json` only if it does not already exist.
           - Write `queue_audio.json` only if it does not already exist.
           - Rename `queue.json` to `queue.json.bak`.
     - Call `migrate_legacy_queue_if_needed()` once in `get_download_manager()` before initializing lane managers.
  2. In `tests/test_download_lanes.py`, add migration tests:
     - `test_corrupt_or_empty_queue_migrated_to_corrupt`: a corrupt or empty `queue.json` is renamed to `queue.json.corrupt`, logged, and the app starts with empty queues (no crash).
     - `test_legacy_queue_missing_or_unknown_kind_defaults_to_video`: a legacy item with a missing or unknown "kind" is treated as "video".
     - `test_legacy_queue_migration_idempotent`: running the migration twice never overwrites existing lane files.
  3. Run `pytest tests/test_download_lanes.py`.
- **Done When:** C.2 has no file lock on disk, lists the three tests above, and all migration tests pass cleanly.
- **Commit Message:** `featC.2: one-time migration of legacy queue.json under threading lock`

---

### Chunk C.3: Cross-Lane Same Video ID Deferral, Multi-Path Wake-Up & Thread Safety

- **Goal:** Ensure identical video IDs never download concurrently in `TMP_DIR`, preserving lane FIFO order, exposing `deferred_job_ids() -> Set[str]`, binding worker slots with sender-based validation to discard stale signals, waking both lanes across all completion/cancellation paths, and ensuring thread-safe database operations.
- **Files Allowed:** `app/core/download_manager.py`, `tests/test_download_lanes.py`
- **Exact Steps:**
  1. Lazy other-lane lookup:
     - In `DownloadManager`: implement lazy helper `_get_other_manager(self) -> Optional['DownloadManager']`:
       - If other lane is already in `_managers`, return it; otherwise return `None` (prevents construction recursion).
  2. Cross-lane deferral and FIFO enforcement:
     - In `DownloadManager`:
       - Expose public method `deferred_job_ids(self) -> Set[str]`.
       - In `_process_next(self)`:
         - Inspect the head waiting job.
         - Check other lane's `active_job`: if other lane is running a job with the exact same `video_id`, mark head job as deferred.
         - **Strict FIFO Rule:** A deferred job blocks later jobs in its own lane. Do not process later jobs; return immediately.
         - If deferral state changes for any job, emit `self.queue_changed`.
  3. Sender-based worker slot binding and thread-safe multi-path wake-up:
     - Bound slots on `DownloadManager`: Worker signal connections (`finished`, `failed`, `progress`, `stage`) must be bound member slots on `DownloadManager` running on the main Qt thread.
     - **Sender Identification Rule:** In every worker slot, identify the sender worker using `sender = self.sender()`. Verify that `sender is self._worker` and `getattr(sender, "job_id", None) == (self._active_job.job_id if self._active_job else None)`. If the sender is an old, cancelled, or terminated worker, ignore the signal immediately and return without modifying active job state.
     - Note: `DownloadWorker` signals `stage`, `progress`, `finished(str)`, `failed(str)`, `paused`; it has NO `cancelled` signal.
     - **Multi-Path Wake-Up:** Trigger `_process_next()` on both lanes thread-safely across all 4 completion/cancellation paths:
       1. Active job finishes (`finished` signal from the current worker).
       2. Active job or queued item is cancelled (`cancel_active()` or `cancel_job()` path; there is no worker `cancelled` signal).
       3. Active job fails (`failed` signal from the current worker, including the auto-repair re-queue path).
       4. A deferred job is removed from the queue (`cancel_job()`).
  4. Concurrency & sender isolation testing in `tests/test_download_lanes.py`:
     - `test_stale_worker_finished_signal_ignored`: a finished signal from an old, cancelled worker does not finish the new active job.
     - `test_stale_worker_failed_signal_ignored`: a failed signal from an old worker does not fail the new active job.
     - `test_current_worker_signal_processed_once`: a normal signal from the current worker is processed exactly once.
     - `test_same_video_id_deferral`: enqueue video X and audio X simultaneously; verify video starts, audio is deferred, `deferred_job_ids()` contains audio job, and audio does not run.
     - `test_strict_fifo_preserved_when_deferred`: enqueue video X, audio X, and audio Y; verify audio Y does not jump ahead of deferred audio X.
     - `test_wake_both_lanes_on_finish`: video X finishes -> audio X immediately wakes and starts.
     - `test_wake_both_lanes_on_cancel_active`: video X cancelled via `cancel_active()` -> audio X wakes and starts.
     - `test_wake_both_lanes_on_fail`: video X fails -> audio X wakes and starts.
     - `test_wake_both_lanes_on_deferred_removal`: removing deferred job lets next job in lane start.
     - `test_two_thread_simultaneous_history_save`: simulate two threads emitting finish signals at the exact same instant -> verify two history rows are saved with zero SQLite lock errors.
  5. **Stop-and-Ask Trigger:** If the two-thread test reports a SQLite concurrency lock error, **STOP and ask the owner**. Do NOT attempt to edit `history_db.py` or `history_service.py`.
  6. Run `pytest tests/test_download_lanes.py`.
- **Done When:** C.3 lists the three stale-worker isolation tests, the sender-based rule, and all deferral, FIFO, wake-up, and thread-safety tests pass.
- **Commit Message:** `featC.3: cross-lane deferral, sender-validated slots, and multi-path thread-safe wake-up`

---

### Chunk C.4: Offline Pause/Resume, Manager Shutdown & Safe App Close Handler

- **Goal:** Add `shutdown()` method to `DownloadManager`, handle offline pausing on both lanes, and safe confirmation on app close.
- **Files Allowed:** `app/core/download_manager.py`, `app/ui/main_window.py`, `tests/test_close_event.py`, `tests/test_download_lanes.py`
- **Exact Steps:**
  1. In `app/core/download_manager.py`:
     - Implement `shutdown(self)`:
       - Stop running worker without starting next waiting job.
       - Ensure waiting jobs remain persisted in `queue_<kind>.json`.
  2. In `app/ui/main_window.py`:
     - In `_on_went_offline(self)`:
       - Call `get_download_manager("video").set_online(False)`.
       - Call `get_download_manager("audio").set_online(False)`.
     - In `_on_came_online(self)`:
       - Call `get_download_manager("video").set_online(True)`.
       - Call `get_download_manager("audio").set_online(True)`.
     - In `closeEvent(self, event)`:
       - Check `v_active = get_download_manager("video").active_job is not None`.
       - Check `a_active = get_download_manager("audio").active_job is not None`.
       - If `v_active or a_active`:
         - Show single confirmation message dialog.
         - If user cancels: `event.ignore(); return`.
       - (1) Call `shutdown()` on both lanes first (`get_download_manager("video").shutdown()` and `get_download_manager("audio").shutdown()`, non-blocking).
       - (2) Wait for both workers with ONE shared 2-second deadline in total (compute deadline once as `time.monotonic() + 2.0`; for each active worker, wait at most remaining time `max(0.0, deadline - time.monotonic())`; if a worker fails to stop within the deadline, log a warning and proceed).
       - (3) Accept the event (`event.accept()`) and close.
  3. In `tests/test_close_event.py` (with fake workers):
     - Test window close prompts when either lane is active.
     - Test window close ignores when user rejects dialog.
     - Test `shutdown()` is called on both lanes before any waiting starts.
     - Test close returns within the shared 2-second deadline when workers stop quickly.
     - Test when a worker never stops, close still completes after the deadline and logs a warning.
  4. In `tests/test_download_lanes.py`:
     - Test `set_online(False)` pauses active workers in both lanes.
     - Test `set_online(True)` resumes active workers in both lanes.
  5. Run `pytest tests/test_close_event.py tests/test_download_lanes.py`.
- **Done When:** C.4 states the shared deadline and lists these tests, and offline and close event tests pass cleanly.
- **Commit Message:** `featC.4: lane shutdown method, closeEvent handling with shared deadline, and offline propagation`

---

### Chunk C.5: Startup After Restore

- **Goal:** Ensure restored waiting items in both lanes automatically start processing after application launch when online, wait if offline, and honour same-video-id deferral.
- **Local Code Finding:** Inspection of local `download_manager.py` and `main_window.py` confirms that `_load_persisted_queue()` only loads items into `_waiting_queue`; **nothing currently starts restored items on startup**, and `_is_offline` defaults to `False`.
- **Files Allowed:** `app/core/download_manager.py`, `app/ui/main_window.py`, `tests/test_download_lanes.py`
- **Exact Steps:**
  1. In `app/core/download_manager.py`:
     - Provide a method `start_restored_jobs(self)`:
       - If not offline, not already running an active job, and waiting queue has items:
         - Calls `self._process_next()`.
  2. In `app/ui/main_window.py`:
     - After the main window is shown and the initial network state is known:
       - Give both managers the current online state via `set_online(self.network_monitor.is_online())`.
       - If online:
         - Start the first waiting job of each lane (`start_restored_jobs()` on video and audio independently, honouring same-video-id deferral).
       - If offline at startup:
         - Nothing starts; both tabs display `"Waiting for internet…"`.
         - When network monitor emits `came_online`, both managers receive `set_online(True)` and start their waiting jobs.
  3. In `tests/test_download_lanes.py`, add tests:
     - `test_restored_waiting_items_start_automatically_when_online`: restored waiting items start automatically when online.
     - `test_restored_waiting_items_do_not_start_when_offline_until_reconnect`: do not start when offline and start when the connection returns.
     - `test_restored_same_video_id_pair_starts_one_and_defers_other`: a restored same-video-id pair starts one and defers the other.
- **Done When:** All three tests pass cleanly, and restored items start automatically on startup.
- **Commit Message:** `featC.5: auto-start restored queue items on application startup`

---

## C. Verification Gate: Phase C

### Scope Proof
Run:
```bash
git diff --name-only 62c8db1
```
Must list ONLY:
- Files approved from Phase A & B
- `app/core/download_manager.py` (scheduling edits only)
- `app/ui/main_window.py`
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `app/ui/queue_widget.py`
- Test files listed in allowed files
- Plan / docs files (`gemini.md`, `docs/`, `plan/`)

### Test Command and Expected Output
```bash
pytest tests/test_download_lanes.py tests/test_close_event.py tests/test_download_manager.py tests/test_queue.py tests/test_phase8_stress_edge_cases.py
```
And crucially:
```bash
pytest
```
Expected output: **Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline**.

### Real-PC Checks
1. **Legacy Migration Check:**
   - Create a dummy `queue.json` in `%APPDATA%\YOuTUbE` with 1 video item and 1 audio item.
   - Launch application.
   - Verify Video tab displays the video item in queue, Audio tab displays the audio item.
   - Verify `queue.json` was renamed to `queue.json.bak`, and `queue_video.json` & `queue_audio.json` exist.
2. **Parallel Download Check:**
   - Start 1 video download.
   - Switch to Audio tab and start 1 audio download.
   - Verify BOTH downloads are actively running in parallel with live progress bars and active network traffic.
3. **Same Video ID Deferral Check:**
   - Paste URL X on Video tab and start download.
   - Paste the exact same URL X on Audio tab and add/download.
   - Verify Audio tab displays status `"Waiting for the same video to finish"`.
   - When Video X finishes, verify Audio X automatically starts downloading.
4. **Lane Queue Isolation Check:**
   - Queue 2 video items and 2 audio items.
   - Restart application.
   - Verify Video tab restores only the video items; Audio tab restores only the audio items.
5. **Offline Pause/Resume Check:**
   - While both video and audio downloads are running, disconnect Wi-Fi.
   - Verify both show "Waiting for internet…".
   - Reconnect Wi-Fi: verify both resume downloading from partial `.part` files.
6. **Safe Close Check:**
   - While both are downloading, click the window Close (X) button.
   - Verify single confirmation prompt appears.
   - Confirm: app closes cleanly within 2 seconds with zero hanging background processes.
7. **Restored Queue Auto-Start Check:**
   - Queue 2 video items and 2 audio items.
   - Close the application.
   - Reopen the application.
   - Verify one video and one audio download start automatically by themselves without manual intervention.

### Stop-and-Ask Triggers Specific to Phase C
- If the two-thread history concurrency test reports a SQLite lock error, **STOP and ask the owner**. Do NOT edit `history_db.py` or `history_service.py`.
- If a fix appears to require modifying `downloader.py` or `proc.py`, STOP and ask the owner.
- If any test fails after two attempts, STOP and ask the owner.
- At the verification gate, report results and wait for "approved".

---

## D. Evidence Template for docs/verification/phase_C.md

```markdown
# Phase C Verification Evidence

## Scope Proof
Command: `git diff --name-only 62c8db1`
Output:
[Paste terminal output here]

## Pytest Output
Command: `pytest` (Full Test Suite)
Output:
[Paste terminal output here - full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline]

## Real-PC Manual Checks
| Check # | Check Name | Result | Notes |
|---|---|---|---|
| 1 | Legacy Migration Check | PASS / FAIL | |
| 2 | Parallel Download Check | PASS / FAIL | |
| 3 | Same Video ID Deferral Check | PASS / FAIL | |
| 4 | Lane Queue Isolation Check | PASS / FAIL | |
| 5 | Offline Pause/Resume Check | PASS / FAIL | |
| 6 | Safe Close Check | PASS / FAIL | |
| 7 | Restored Queue Auto-Start Check | PASS / FAIL | |

## Captured Assets
- Screenshot: `screenshot_phase_c_parallel.png`

## Decision
- Status: PASS / FAIL
- Reason: Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline; zero protected files modified, real-PC parallel downloads verified.
```

---

## E. "After This Phase" Message

### Report to the Owner
When all Phase C chunks are complete and the verification gate has passed:
1. Send a concise report summarizing:
   - Full test suite results (confirming full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline).
   - Scope verification output confirming zero protected files touched.
   - Real-PC checks confirmation (parallel downloads, deferral, migration, and clean close).
2. Ask for explicit approval to proceed to Phase D.

### Exactly What Words to Wait For
Wait for the owner to reply with:
> **approved**

**DO NOT TOUCH ANY CODE IN PHASE D UNTIL THE OWNER REPLIES "approved".**

### Commit Command for the Gate
```bash
git commit --allow-empty -m "gate: phase C verified and approved"
```
*(Or commit `docs/verification/phase_C.md` if recorded on disk).*
