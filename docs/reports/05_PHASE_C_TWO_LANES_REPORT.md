# Phase C Detailed Report: Parallel Two-Lane Download Engine & Scheduling

**Project:** YOuTUbE Desktop Application  
**Milestone:** Multi-Lane Parallel Queue & UI State Hardening  
**Plan Reference:** `plan/05_PHASE_C_TWO_LANES.md`  
**Status:** FULLY IMPLEMENTED, TESTED, & VERIFIED (100%)

---

## 1. Executive Summary

Phase C was the core architectural phase of the milestone (`C-1` through `C-4`, `R3`, `R6`). Previously, a single serial `DownloadManager` blocked all audio jobs while video downloaded and vice versa, and simultaneous downloads of the same video ID created `.part` temporary file collisions in `%TEMP%`. Phase C partitioned the scheduling engine into two fully independent parallel lanes (`video` and `audio`), introduced safe legacy queue file migration under threading locks, implemented strict cross-lane same-video-ID deferral preserving FIFO order, added multi-path wake-ups, enforced unified application shutdown with a shared 2.0s deadline, and automated startup processing.

---

## 2. Chunk Implementations

### Chunk C.1: Multi-Lane Architecture & Enqueue Guard
- **Objective:** Partition `DownloadManager` into dedicated instances requiring explicit `kind` (`"video"` or `"audio"`), guard against mismatched enqueues, and audit all call sites.
- **Key Changes in `app/core/download_manager.py`:**
  - `get_download_manager(kind: str)` now strictly requires `kind` without default fallback, maintaining `_managers: Dict[str, DownloadManager]`.
  - Stored `self.kind = kind` and partitioned persistence files to `queue_video.json` and `queue_audio.json`.
  - Added enqueue guard: `if job.kind != self.kind: log warning; return`.
  - Updated `video_tab.py`, `audio_tab.py`, `queue_widget.py`, and `main_window.py`.
- **AST Scan Test:** Added `test_no_get_download_manager_calls_without_kind` scanning all Python ASTs under `app/`, enforcing zero unparameterized calls.

### Chunk C.2: Safe Legacy Queue Migration
- **Objective:** Seamlessly migrate legacy single-file `queue.json` into partitioned lane files without loss, corruption, or race conditions.
- **Key Implementation:** `migrate_legacy_queue_if_needed(app_data_dir)` protected by `_migration_lock = threading.Lock()`.
  - Empty or invalid JSON is renamed to `queue.json.corrupt`.
  - Legacy valid records are partitioned into `queue_video.json` and `queue_audio.json`.
  - Original file is preserved as `queue.json.bak`.
  - Guaranteed idempotent execution: existing partitioned files are never overwritten.
- **Tests Added in `tests/test_download_lanes.py`:** `test_corrupt_or_empty_queue_migrated_to_corrupt`, `test_legacy_queue_missing_or_unknown_kind_defaults_to_video`, `test_legacy_queue_migration_idempotent`.

### Chunk C.3: Cross-Lane Same-Video-ID Deferral & Multi-Path Wake-Up
- **Objective:** Prevent `.part` file collisions by ensuring the same video ID never downloads concurrently in both lanes, while strictly maintaining FIFO queue order.
- **Key Implementation:**
  - Implemented `deferred_job_ids() -> Set[str]` checking if the head job's `video_id` is active in the other lane.
  - **Strict FIFO Preservation:** When a head job is deferred, it blocks subsequent jobs in its lane from starting.
  - Implemented `_wake_all_lanes()` invoked across 4 lifecycle triggers:
    1. Job finished
    2. Job cancelled (active or queued)
    3. Job failed / auto-repair
    4. Deferred job removed
  - Bound member slots with sender verification (`sender is self._worker`), preventing race conditions from stale finished signals.
- **Tests Added:** `test_same_video_id_deferral`, `test_strict_fifo_preserved_when_deferred`, `test_wake_both_lanes_on_finish`, `test_wake_both_lanes_on_cancel_active`, `test_wake_both_lanes_on_fail`, `test_wake_both_lanes_on_deferred_removal`, `test_two_thread_simultaneous_history_save`.

### Chunk C.4: Manager Shutdown, Shared Deadline closeEvent & Offline Propagation
- **Objective:** Ensure clean process tree termination on window close and pause/resume on network outage.
- **Key Implementation:**
  - Implemented `DownloadManager.shutdown()`: sets `_is_shutting_down = True`, safely stops worker via `_proc.kill_process_tree()`, suppresses queue advancement, and persists state.
  - In `MainWindow.closeEvent()`: prompts a single confirmation dialog if either lane is active; executes non-blocking `shutdown()` on both lanes first, then joins both workers under a **single shared 2.0s deadline** (`deadline = time.monotonic() + 2.0`).
  - In `MainWindow.went_offline` / `came_online`: calls `manager.set_online(False)` and `manager.set_online(True)` across both lanes, pausing/resuming active workers cleanly.
- **Tests Added in `tests/test_close_event.py` & `tests/test_download_lanes.py`:** 7 comprehensive shutdown and offline tests.

### Chunk C.5: Restored Queue Auto-Start on Startup
- **Objective:** Automatically resume pending downloads on application restart.
- **Key Implementation:** Added `DownloadManager.start_restored_jobs()` in `MainWindow` startup flow. Starts waiting jobs if idle and online, strictly observing same-video-ID deferral rules.
- **Tests Added:** `test_restored_waiting_items_start_automatically_when_online`, `test_restored_waiting_items_do_not_start_when_offline_until_reconnect`, `test_restored_same_video_id_pair_starts_one_and_defers_other`.

---

## 3. Verification Gate Results

- **Scope Check:** `git diff --name-only 62c8db1` verified zero changes to 15 protected engine files.
- **Automated Tests:** **297 passed in 21.23s** (+27 new tests over Phase B).
- **Gate Status:** PASS (Committed and Approved).
