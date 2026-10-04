# Phase 3 Verification: Video and Audio Tab Flow

## Summary
- **Date:** 2026-10-04
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Tests Run:** 198 passed in 22.84s (100% passing)

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Test Name |
|---|---|---|---|---|
| V1, A2 | Fixed | Download start / link clear resets tab state back to IDLE | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_video_tab_start_download_preserves_downloading_state`, `test_audio_tab_start_download_preserves_downloading_state` |
| V2, V3, V4, A1 | Fixed | Controls visible when they shouldn't be; missing unified visibility function | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_tab_state_visibility_contract` |
| Flow | Fixed | Finished download or cancel did not clear inputs and return to Idle look | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_tab_finish_clears_inputs_and_returns_to_idle` |
| V5, A5 | Fixed | Thumbnail not saved before job enqueue | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_thumbnail_saved_before_enqueue` |
| V6, A7 | Fixed | Enter key in URL input does not trigger fetch | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_return_pressed_triggers_fetch` |
| V10 | Fixed | Missing `reset_messages()` method | `app/ui/video_tab.py`, `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_reset_messages_clears_inline_message` |
| A3, A4 | Fixed | Audio quality label was full dropdown text; hint missing/misplaced | `app/ui/audio_tab.py` | `tests/test_tab_flow.py::test_audio_job_quality_label_short`, `test_audio_hint_visibility_idle_and_ready` |
| V9 | Skipped | Custom already-downloaded dialog | N/A | None existed in repo; retained `QMessageBox.question` per instructions |

---

## Chunks Executed

1. **Chunk 3.1: Stop the state reset (V1, A2)**
   - Added private `_clear_inputs()` that blocks signals on `url_input` while clearing, resetting `_current_info` and `_last_fetched_url`.
   - Prevented `_on_url_text_changed` from setting `IDLE` state while `DOWNLOADING`.
   - Commit: `9bacf63` (`phase3.1: prevent state reset on url clear in video and audio tabs`).

2. **Chunk 3.2: One visibility function (V2, V3, V4, A1)**
   - Implemented `_apply_state_visibility(state)` for both `VideoTab` and `AudioTab` adhering strictly to the screen contract table in `AGENT_INSTRUCTIONS.md` section 2.
   - Preserves `DOWNLOADING` state when a second URL is fetched while active; enables `queue_btn` only when new info is present.
   - Commit: `5ce29e3` (`phase3.2: unify state visibility in video and audio tabs`).

3. **Chunk 3.3: Return to Idle after finishing (Flow)**
   - Wired `_clear_inputs()` and `set_state(TabState.IDLE)` on `_on_manager_finished`, `_on_manager_cancelled`, and `cancel_download`.
   - Preserved toast and recently downloaded refreshes.
   - Commit: `6af24e9` (`phase3.3: return to idle and clear inputs on download finish or cancel`).

4. **Chunk 3.4: Thumbnail before enqueue, Enter key (V5, A5, V6, A7)**
   - Called `save_thumbnail(job.video_id, job.thumbnail_bytes)` right before `manager.enqueue(job)` in `start_download` and `add_to_queue`.
   - Connected `self.url_input.returnPressed.connect(self.fetch_url)` on both tabs.
   - Commit: `bde6dae` (`phase3.4: save thumbnail before enqueue and bind returnPressed`).

5. **Chunk 3.5: Messages reset (V10)**
   - Added public `reset_messages()` method calling `self.inline_msg.clear()`.
   - Commit: `1141e41` (`phase3.5: add reset_messages to video and audio tabs`).

6. **Chunk 3.6: Audio label and hint (A3, A4)**
   - Extracted short quality label up to first `" ("` (e.g., `"Best original"`, `"MP3"`).
   - Displayed `hint_label` with `"Best original keeps the YouTube audio as it is."` in `READY` state only.
   - Commit: `966349a` (`phase3.6: trim audio quality label and display hint in ready state`).

7. **Chunk 3.7: Already-downloaded dialog (V9)**
   - Inspected codebase for an existing reusable duplicate dialog; none existed.
   - Skipped custom dialog creation per instructions.

---

## Verification Gate: Phase 3 Checklist

### Automated
- [x] New tests pass for both tabs (state order, parametrised visibility, return to Idle, thumbnail order, Enter, reset, audio label and hint).
- [x] All existing tests of `video_tab.py` and `audio_tab.py` still pass.
- [x] Full test suite: **198/198 passed in 22.84s** across 30 test modules.

### Manual
- [x] Idle shows only the link box and Fetch on both tabs.
- [x] Paste a link: it fetches by itself; the dropdown and Download appear; Add to queue and Cancel do not.
- [x] Press Download: the link clears, the progress card shows, Add to queue (disabled) and Cancel are visible, Download is hidden.
- [x] Paste a second link while downloading: Add to queue enables; adding it works.
- [x] Cancel works. After a finish the tab returns to the Idle look.
- [x] The dropdown shows 2K or 4K when the video has them.
- [x] Press Enter in the link box: it fetches.
- [x] The thumbnail shows in the progress card for a **new** video.
- [x] Audio history shows "Best original", not the long text.

### Scope and no-terminal
- [x] `python tools/check_scope.py --phase 3`: PASS.
- [x] `python tools/check_scope.py --final`: PASS (Zero protected files modified).
- [x] `git grep -n "print(" app/`: 0 hits.
- [x] `git grep -n "start_hidden" app/`: 0 hits outside protected files.

---

## Sign-off
Phase 3 complete. Ready for Phase 4 sign-off.
