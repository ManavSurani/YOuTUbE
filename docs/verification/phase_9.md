# Phase 9 Verification: Startup and Close

## Summary
- **Date:** 2026-10-05
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Tests Run:** 238 passed in 15.52s (100% passing across 34 test modules)
- **Rows Addressed:** U3, E10, E12

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Tests Added / Passing |
|---|---|---|---|---|
| U3 | Fixed | Offloaded startup history repair from the UI main thread to a background `HistoryRepairWorker(QThread)` in `app/main.py`. Passes configured `download_dir` from settings, runs once per version via `history_repair_version` guard, signals History tab to refresh on completion, and logs row count. | `app/main.py` | `test_startup_repair_worker_calls_configured_folder_and_not_ui_thread`, `test_startup_repair_skipped_when_version_matches`, `test_history_refresh_happens_after_worker_signals` |
| E10 | Fixed | Added exit confirmation check in `MainWindow.closeEvent()` in `app/ui/main_window.py`. If a download is active, prompts the user ("A download is running. Quit and cancel it?" with "Keep downloading" as default button). If confirmed, cancels active download via `manager.cancel_active()` and waits up to 2 seconds for worker termination before closing. | `app/ui/main_window.py` | `test_close_event_prompts_when_downloading`, `test_close_event_cancels_and_waits_when_user_accepts`, `test_close_event_ignores_when_user_rejects` |
| E12 | Fixed | In `handle_secondary_instance_message()` in `app/main.py`, validated incoming secondary instance payloads using `is_youtube_url()`. Brings main window to foreground and populates the video tab link input only if the link is a valid YouTube URL, ignoring non-YouTube messages and plain activations. | `app/main.py` | `test_secondary_instance_message_ignores_junk_and_accepts_valid_url` |

---

## Chunks Executed

1. **Chunk 9.1: Startup history repair off the UI thread (U3)**
   - Created `HistoryRepairWorker(QThread)` in `app/main.py` to run `repair_existing_rows(download_dir=...)` in the background.
   - Pinned once-per-version execution using `history_repair_version` in `settings.json`.
   - Connected `worker.repaired` signal to update settings and trigger UI refresh (`win.history_tab.refresh_items()`).
   - Verified via `tests/test_startup_repair.py`.
   - Commit: `4de6f18` (`phase9.1: run startup history repair in background worker once per version`).

2. **Chunk 9.2: Window close while downloading (E10)**
   - Overrode `closeEvent` in `MainWindow` (`app/ui/main_window.py`).
   - Intercepted close event if `manager.active_job` is present and `confirm_exit_on_download` is enabled.
   - Displayed confirmation dialog with "Quit" and default "Keep downloading" button.
   - Called `manager.cancel_active()` and `worker.wait(2000)` on acceptance.
   - Verified via `tests/test_close_event.py`.
   - Commit: `29b5fa1` (`phase9.2: prompt to cancel active download on window close`).

3. **Chunk 9.3: Secondary instance link insertion (E12)**
   - Updated `handle_secondary_instance_message` in `app/main.py`.
   - Filtered message payload through `is_youtube_url()` before setting text on `win.video_tab.url_input`.
   - Preserved window activation behavior (`win.raise_()`, `win.activateWindow()`).
   - Verified via `tests/test_single_instance.py:test_secondary_instance_message_ignores_junk_and_accepts_valid_url`.
   - Commit: `d1c099e` (`phase9.3: validate secondary instance message url with is_youtube_url`).

---

## Verification Gate: Phase 9 Checklist

### Automated Checks
- [x] All Phase 9 tests pass:
  - `tests/test_startup_repair.py` (3 passed)
  - `tests/test_close_event.py` (3 passed)
  - `tests/test_single_instance.py` (2 passed)
- [x] Full test suite: **238/238 passed in 15.52s** across 34 test modules (`pytest`).

### Manual Checks
- [x] App startup is instant without UI freezing or lag during database scan.
- [x] Closing the window during an active download presents the confirmation prompt; clicking "Keep downloading" leaves the app and download running; clicking "Quit" cancels the download and closes cleanly within 2s.
- [x] Launching a secondary instance with a valid YouTube link activates the main window and fills the input; launching with arbitrary text or empty args activates the main window without corrupting the link input.

### Scope and No-Terminal Checks
- [x] `python tools/check_scope.py --phase 9`: PASS.
- [x] `python tools/check_scope.py --final`: PASS (Zero protected files modified).
- [x] `git grep -n "print(" app/`: 0 hits.
- [x] Zero terminal windows or console popups.

---

## Sign-off
Phase 9 complete. Awaiting user approval to proceed to Phase 10 (Testing and Release).
