# Autonomous Fix Loop Plan: YOuTUbE (Phases 0–8)

**Base Commit (BASE):** `7418d4f1585fde429809d1c0778cb9ade5ced9e8` (`7418d4f`)  
**Branch:** `fix/ui-pass`  
**Baseline Suite Count:** 406 passed, 0 failed in 59.26s  
**Repo State:** Verified matching `fixPROG.1` to `fixPROG.4`, `3b`, `4b`, `5`, `7`, and docs commits.  
**Uncommitted / Untracked Files:** `gemini.md` (uncommitted), `plan/08_PROGRESS_MENU_PLAN.md`, `plan/09_ADD_TO_QUEUE_FETCH_PLAN.md`, `docs/verification/fixq_failing_tests.md` (untracked) — left intact per Phase 0 rules.

---

## Phase 0: Baseline & Code Audit
- **Goal:** Document BASE hash, clean suite count, and audit target files.
- **Allowed Files:** `plan/10_AUTONOMOUS_PLAN.md`
- **Steps:**
  1. Record starting hash `7418d4f` as `BASE`.
  2. Run `python -m pytest -q -rf -p no:cacheprovider` -> 406 passed in 59.26s.
  3. Audit `video_tab.py`, `audio_tab.py`, and `history_tab.py`.
- **Done When:** Baseline recorded and complete plan written.
- **Commit:** None (Phase 0 has no commit).

---

## Phase 1: Exact Focus-Ring Test
- **Goal:** Replace loose bounds in `test_animated_checkbox_focus_ring_unclipped_dark_and_light` with exact expectations: `ring rect = box_rect.adjusted(-2, -2, 2, 2)` with `RING=3`, box 18 px, widget height 24 -> ring `(1, 1)` to `(23, 23)`, pen 1.5, scale by device pixel ratio, tolerance ±1 px. Preserve `assert cb.hasFocus() is True` in dark and light themes.
- **Allowed Files:** `tests/test_ui_kit.py` only.
- **Steps:**
  1. Inspect `test_animated_checkbox_focus_ring_unclipped_dark_and_light` in `tests/test_ui_kit.py`.
  2. Ensure assertions verify `expected_min_x = round(1.0 * scale)`, `expected_min_y = round(1.0 * scale)`, `expected_max_x = round(23.0 * scale)`, `expected_max_y = round(23.0 * scale)` with tolerance `abs(val - expected) <= 1`.
  3. Run test in dark and light modes; verify it passes cleanly.
- **Done When:** Exact bounds tested and passing without modifying `checkbox.py`.
- **Commit Message:** `fixAUTO.1: exact focus ring bounds`

---

## Phase 2: Styled Right-Click Menu
- **Goal:** Confirm and verify right-click context menu styling on `AnimatedLineEdit` matching the dropdown look (8px radius, 4px padding, items min-height 32px, item padding 6px 12px, item radius 4px, surface hover, text_muted disabled, border separator, frameless + no drop shadow + WA_TranslucentBackground, 150ms OutCubic fade, Qt effect suppression). Verify grab() transparency: corner pixel alpha == 0, center pixel == surface color. Verify `search_input` in `history_tab.py` uses `AnimatedLineEdit` with exact preservation of properties.
- **Allowed Files:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/history_tab.py`, `tests/test_ui_kit.py`, `tests/test_tab_looks.py`.
- **Steps:**
  1. Verify grab() on QMenu has corner pixel alpha 0 and center pixel surface color.
  2. Confirm `history_tab.py` `search_input` is `AnimatedLineEdit` with `ClickFocus`, placeholder "Search history…", height 36, and `textChanged` connected to `_on_search_changed`.
  3. Ensure all tests in `tests/test_ui_kit.py` and `tests/test_tab_looks.py` covering standard actions (Cut, Copy, Paste, Delete, Select All, Undo, Redo), key shortcuts (Menu, Shift+F10), effect flag restoration, 20 open/close cycles, and plain QLineEdit in Settings pass.
  4. Record row in `docs/verification/scope_exceptions.md` if needed.
- **Done When:** All right-click menu tests pass and visual contract is verified.
- **Commit Message:** `fixAUTO.2: styled right-click menu matching the dropdown`

---

## Phase 3: Report on the Failed 144p Row
- **Goal:** Document read-only log analysis of the 144p HTTP 403 Forbidden error in `docs/verification/progress_log_evidence.md`. Do NOT edit `errors.py`.
- **Allowed Files:** `docs/verification/progress_log_evidence.md`.
- **Steps:**
  1. Verify log records from `%APPDATA%\YOuTUbE\logs\app.log`.
  2. Document video ID `6F5RWSiSxcI`, failure at `04:32:54` (first start of 144p job after 4K download succeeded).
  3. Note that error occurred once for this video on first start (not retry).
  4. Document diagnosis: "likely, unproven" YouTube rate-limiting / token expiration during rapid sequential format extraction.
  5. Commit documentation update.
- **Done When:** Documented accurately with test honesty.
- **Commit Message:** `fixAUTO.3: 403 findings`

---

## Phase 4: Failing Tests for Stuck State (Video Tab)
- **Goal:** Add tests T1–T8 in `tests/test_tab_state_machine.py` following the real sequence (paste -> `fetch_url` sets `FETCHING` -> fetch result).
- **Allowed Files:** `tests/test_tab_state_machine.py` (additions only).
- **Steps:**
  1. Add `DummyWorker` with signals `fetched`, `failed`, `finished`.
  2. Implement T1 (`test_new_link_fetched_during_download_enables_add_to_queue`).
  3. Implement T2 (`test_fetch_fails_during_running_download_returns_to_downloading`).
  4. Implement T3 (`test_fetch_result_stops_fetch_button_spinner`).
  5. Implement T4 (`test_cached_link_during_download_goes_to_downloading_with_queue_enabled` - guard).
  6. Implement T5 (`test_pending_link_survives_running_download_finished`).
  7. Implement T6 (`test_pending_link_survives_running_download_failed_and_cancelled`).
  8. Implement T7 (`test_two_queued_jobs_never_show_idle_between_finish_and_next_start`).
  9. Implement T8 (`test_no_download_running_pasting_link_transitions_fetching_to_ready` - guard).
  10. Run tests, confirm exactly T1, T2, T3, T5, T6, T7 fail for the right reasons, while T4 and T8 pass.
  11. Save output in `docs/verification/fixq_failing_tests.md`.
- **Done When:** 6 expected tests fail and 2 guards pass.
- **Commit Message:** `fixAUTO.4: failing tests for the stuck fetching state (video)`

---

## Phase 5: Fix the Video Tab
- **Goal:** Apply smallest fix in `app/ui/video_tab.py`.
- **Allowed Files:** `app/ui/video_tab.py` only.
- **Steps:**
  1. In `_on_info_fetched`: transition to `DOWNLOADING` if `self._job_running()` else `READY`.
  2. In `_on_info_failed`: transition to `DOWNLOADING` if `self._job_running()` else `IDLE`.
  3. Add `_has_waiting_job() -> bool: return bool(get_download_manager("video").waiting_jobs)`.
  4. In `_on_manager_finished`, `_on_manager_failed`, and `_on_manager_cancelled`:
     - `keep_link = self._current_info is not None or bool(self.url_input.text().strip())`
     - `if not keep_link: self._clear_inputs()`
     - `state = DOWNLOADING if (self._job_running() or self._has_waiting_job()) else (READY if self._current_info is not None else IDLE)`
  5. Confirm in `DOWNLOADING` branch of `_apply_state_visibility`: `fetch_btn.set_loading(False)`, `url_input.setEnabled(True)`, info card/quality combo/Add to queue enabled when `self._current_info is not None`.
  6. Verify all Phase 4 tests pass; verify `test_tab_flow.py`, `test_tab_looks.py`, `test_per_item_cards.py`, `test_recent_sync.py` pass without alterations.
- **Done When:** T1–T8 pass and suite passes cleanly.
- **Commit Message:** `fixAUTO.5: leave the fetching state correctly and keep a pending link (video)`

---

## Phase 6: Audio Tab
- **Goal:** Port tests and fix to `AudioTab`.
- **Allowed Files:** `app/ui/audio_tab.py`, `tests/test_tab_state_machine.py`.
- **Steps:**
  1. Add audio equivalents of T1–T8 to `tests/test_tab_state_machine.py` (manager `"audio"`).
  2. Run audio tests, confirm identical 6 failures.
  3. Apply identical state fix to `app/ui/audio_tab.py`:
     - Add `_has_waiting_job()` helper for `"audio"`.
     - Update `_on_info_fetched` and `_on_info_failed`.
     - Update `_on_manager_finished`, `_on_manager_failed`, and `_on_manager_cancelled` with `keep_link` and `_has_waiting_job()`.
  4. Run audio tests and confirm all pass.
- **Done When:** Audio tests pass cleanly with zero regressions.
- **Commit Message:** `fixAUTO.6: same fix for the audio tab`

---

## Phase 7: Fetch Flow Robustness
- **Goal:** Ensure robustness of fetch lifecycle:
  - Newer paste while older fetch in-flight: old result discarded via `_fetch_seq`, spinner and link box state end cleanly.
  - Fetch finishes after tab reset: no crash, no stale card.
  - Spinner is off (`_is_loading == False`) across fetched, failed, and reset in every state.
- **Allowed Files:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/test_tab_state_machine.py`.
- **Steps:**
  1. Write edge case tests in `tests/test_tab_state_machine.py`.
  2. Run tests to see if any guard is needed.
  3. Add only minimal guards demanded by any failing robustness test.
- **Done When:** All robustness tests pass.
- **Commit Message:** `fixAUTO.7: fetch flow guards`

---

## Phase 8: Final Report and Self-Audit
- **Goal:** Final suite verification, scope proof, detailed report generation, and plan comparison.
- **Allowed Files:** `docs/verification/final_report.md`, `docs/verification/fixq_failing_tests.md`, `docs/verification/scope_exceptions.md`, `docs/verification/progress_log_evidence.md`, `plan/10_AUTONOMOUS_PLAN.md`.
- **Steps:**
  1. Run full suite: `python -m pytest -q -rf -p no:cacheprovider`.
  2. Verify scope: `git diff --name-only BASE HEAD`.
  3. Check cleanliness: `git grep -n "print(" -- app` and `git grep -n "shell=True" -- app`.
  4. Write `docs/verification/final_report.md` with phase table, test data honesty notes, known limits, and visual checklist.
  5. Compare line by line against `plan/10_AUTONOMOUS_PLAN.md`.
  6. Commit docs: `fixAUTO.8: final report and plan`.
  7. Output final summary and visual checklist.
- **Done When:** Final report committed, diff verified, visual checklist presented.
