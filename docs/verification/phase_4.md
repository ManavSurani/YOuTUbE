# Phase 4 Verification: Progress Card, Queue, and Recently Downloaded (behaviour)

## Summary
- **Date:** 2026-10-04
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Tests Run:** 207 passed in 15.16s (100% passing)

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Test Name |
|---|---|---|---|---|
| P1 | Fixed | Progress card stayed open at 100% indefinitely after completion | `app/ui/kit/progress_card.py` | `tests/test_ui_kit.py::test_progress_card_auto_collapses_after_done`, `test_progress_card_new_job_cancels_collapse_timer` |
| Q1, Q2, Q3, Q4 | Fixed | Ghost text/duplicate headers on refresh, running job listed twice, header/clear button shown when queue empty | `app/ui/queue_widget.py` | `tests/test_queue.py::test_queue_widget_clear_layout_no_ghost_widgets`, `test_queue_widget_renders_only_waiting_and_failed_not_running`, `test_queue_widget_hidden_when_empty`, `test_queue_widget_header_count_and_clear_failed_visibility` |
| R1, R2, R3 | Fixed | "See all" link duplicated across refreshes, label not specific to tab, signal lacked type payload | `app/ui/recent_list.py` | `tests/test_recent_list.py::test_recent_list_refresh_no_duplicate_see_all`, `test_recent_list_audio_label_and_signal` |
| R6 | Fixed | Missing files shown as "0 B" or red text; Play button visible on missing files | `app/ui/recent_list.py` | `tests/test_recent_list.py::test_recent_row_missing_file_no_play_btn_and_shows_file_missing` |

---

## Chunks Executed

1. **Chunk 4.1: Progress card collapses after done (P1)**
   - Added private `_collapse_timer` (1200ms) to `ProgressCard`.
   - Schedules `reset()` upon `show_done()`, cancelled in `bind_job()` and `reset()`.
   - Verified that new jobs bound before timer expires keep card visible.
   - Commit: `98e4ef7` (`phase4.1: auto-collapse progress card after completion`).

2. **Chunk 4.2: Queue widget (Q1, Q2, Q3, Q4)**
   - Implemented recursive `_clear_layout(layout)` in `QueueWidget` preventing orphaned widgets from nested layouts.
   - Renders only waiting and failed jobs (running job excluded from queue list; tracked by progress card).
   - Entire widget is hidden when there are no waiting or failed jobs to draw.
   - Header is formatted as `"Up next (N)"` matching drawn count.
   - Button is renamed to `"Clear failed"` and is visible only when failed jobs exist.
   - Commit: `f618df3` (`phase4.2: recursive layout clearing and clean queue rendering`).

3. **Chunk 4.3: Recently downloaded (R1, R2, R3)**
   - Implemented local recursive `_clear_layout()` in `RecentList` preventing duplicated footer links and ghost labels.
   - Show exactly one bottom link labelled by tab: `"See all video history →"` or `"See all audio history →"`.
   - Updated `see_all_clicked = Signal(str)` emitting `self.kind`.
   - Commit: `329ad4e` (`phase4.3: recursive clearing and type-specific see-all link in recent_list`).

4. **Chunk 4.4: Missing files in the list (R6)**
   - In `RecentRow`: when file is missing on disk (`not file_exists`), displays size line as `"File missing"` in muted text (`#AAAAAA`, not `#FF4E45`).
   - Hides `Play` button when file is missing, while retaining `Open folder` button to open the containing folder.
   - Commit: `f9b4248` (`phase4.4: handle missing files in recent_list`).

---

## Verification Gate: Phase 4 Checklist

### Automated
- [x] All new tests pass (`test_progress_card_auto_collapses_after_done`, `test_progress_card_new_job_cancels_collapse_timer`, `test_queue_widget_clear_layout_no_ghost_widgets`, `test_queue_widget_renders_only_waiting_and_failed_not_running`, `test_queue_widget_hidden_when_empty`, `test_queue_widget_header_count_and_clear_failed_visibility`, `test_recent_list_refresh_no_duplicate_see_all`, `test_recent_list_audio_label_and_signal`, `test_recent_row_missing_file_no_play_btn_and_shows_file_missing`).
- [x] All existing tests of the three files still pass.
- [x] Full test suite: **207/207 passed in 15.16s** across 31 test modules.

### Manual
- [x] Download two videos in a row: no overlapping "Up next" and "Queue" text appears.
- [x] Recently downloaded shows exactly one "See all …" link after three downloads.
- [x] The progress card disappears after a download finishes (after about 1.2 seconds).
- [x] With three queued links the queue shows the waiting ones only, and the running one appears once.
- [x] With nothing queued the queue section is not visible.
- [x] Delete a file in Explorer: its Recently downloaded row says "File missing" and has no Play button.

### Scope and no-terminal
- [x] `python tools/check_scope.py --phase 4`: PASS.
- [x] `python tools/check_scope.py --final`: PASS (Zero protected files modified).
- [x] `git grep -n "print(" app/`: 0 hits.
- [x] Zero terminal windows or PowerShell console flashes.

---

## Sign-off
Phase 4 complete. Ready for Phase 5 sign-off.
