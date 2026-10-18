# ADD TO QUEUE AND FETCH STUCK-STATE FIX PLAN

**Project:** YOuTUbE (Windows desktop app, Python + PySide6)  
**Branch:** `fix/ui-pass` (base commit: `7418d4f`)  
**Scope:** Fix the stuck FETCHING state when fetching while downloading, prevent clearing typed/fetched links on manager events, and eliminate IDLE flicker between queued jobs.

---

## 1. Overview & Root Cause Analysis

### Bug 1: Stuck FETCHING State
When a video or audio download is running:
1. Pasting a new, uncached link triggers `fetch_url()`, which invokes `set_state(TabState.FETCHING)`.
2. `TabState.FETCHING` disables `url_input` and `queue_btn`, and starts the Fetch button spinner (`fetch_btn.set_loading(True)`).
3. When `_on_info_fetched()` or `_on_info_failed()` completes:
   ```python
   if self._job_running() or self._state == TabState.DOWNLOADING:
       self._apply_state_visibility(self._state)
   ```
   At this point `self._state` is `TabState.FETCHING`. Therefore `_apply_state_visibility(TabState.FETCHING)` is called again.
4. The tab never transitions out of `FETCHING`. The link box and Add to queue button remain disabled, and the spinner never stops until the active download ends.
5. Links in `_FETCH_CACHE` bypass `fetch_url()`'s `set_state(TabState.FETCHING)` call, which masked the bug during repeat URL tests.

### Bug 2: Premature Reset on Manager Events
1. In `_on_manager_finished` and `_on_manager_failed`:
   ```python
   self._clear_inputs()
   self.set_state(TabState.IDLE)
   ```
   This unconditionally wipes any link typed or fetched by the user while the download was running.
2. It transitions to `TabState.IDLE` even if there are waiting jobs in the queue (`_has_waiting_job()`), causing an IDLE visual flash between sequential jobs.
3. In `_on_manager_cancelled`, if `_current_info` is `None`, `_clear_inputs()` also wiped any raw URL string the user typed.

---

## 2. Chunk-by-Chunk Plan

### Chunk 1: Failing Tests, Video Tab
- **Goal:** Write comprehensive tests for the real sequence on `VideoTab`, confirming that T1–T3 and T5–T7 fail for the expected reasons, while guards T4 and T8 pass.
- **Allowed Files:** `tests/test_tab_state_machine.py` (additions only).
- **Steps:**
  1. Add `DummyWorker` (QObject with signals `fetched`, `failed`, `finished`, no-op `start`).
  2. Implement `test_new_link_fetched_during_download_enables_add_to_queue` (T1).
  3. Implement `test_fetch_fails_during_running_download_returns_to_downloading` (T2).
  4. Implement `test_fetch_result_stops_fetch_button_spinner` (T3).
  5. Implement `test_cached_link_during_download_goes_to_downloading_with_queue_enabled` (T4 guard).
  6. Implement `test_pending_link_survives_running_download_finished` (T5).
  7. Implement `test_pending_link_survives_running_download_failed_and_cancelled` (T6).
  8. Implement `test_two_queued_jobs_never_show_idle_between_finish_and_next_start` (T7).
  9. Implement `test_no_download_running_pasting_link_transitions_fetching_to_ready` (T8 guard).
  10. Record failure output in `docs/verification/fixq_failing_tests.md`.
- **Test First:** Run Chunk 1 tests on `HEAD` (confirmed: 6 failed, 2 passed).
- **Expected Failure:**
  - T1: `assert <TabState.FETCHING: 2> == <TabState.DOWNLOADING: 4>`
  - T2: `assert <TabState.FETCHING: 2> == <TabState.DOWNLOADING: 4>`
  - T3: `assert True is False` (`fetch_btn._is_loading` remains True)
  - T5: `assert '' == 'https://www.youtube.com/watch?v=BBBBBBBBBBB'`
  - T6: `assert '' == 'https://www.youtube.com/watch?v=BBBBBBBBBBB'`
  - T7: `assert <TabState.IDLE: 1> not in [<TabState.IDLE: 1>]`
- **Done When:** All 8 tests exist in `tests/test_tab_state_machine.py`, the 6 expected failures are confirmed, and output is documented.
- **Commit Message:** `fixQ.1: add failing tests for the stuck fetching state (video)`

---

### Chunk 2: Fix the Video Tab
- **Goal:** Apply the minimal state machine fix in `app/ui/video_tab.py` to leave FETCHING correctly, preserve pending links, and prevent IDLE flashing.
- **Allowed Files:** `app/ui/video_tab.py` only.
- **Steps:**
  1. Add private helper `_has_waiting_job() -> bool`:
     ```python
     def _has_waiting_job(self) -> bool:
         return bool(get_download_manager("video").waiting_jobs)
     ```
  2. In `_on_info_fetched`:
     ```python
     if self._job_running():
         self.set_state(TabState.DOWNLOADING)
     else:
         self.set_state(TabState.READY)
     ```
  3. In `_on_info_failed`:
     ```python
     if self._job_running():
         self.set_state(TabState.DOWNLOADING)
     else:
         self.set_state(TabState.IDLE)
     ```
  4. In `_on_manager_finished` and `_on_manager_failed`:
     ```python
     keep_link = self._current_info is not None or bool(self.url_input.text().strip())
     if not keep_link:
         self._clear_inputs()
     if self._job_running() or self._has_waiting_job():
         self.set_state(TabState.DOWNLOADING)
     elif self._current_info is not None:
         self.set_state(TabState.READY)
     else:
         self.set_state(TabState.IDLE)
     ```
  5. In `_on_manager_cancelled`:
     ```python
     self.progress_card.reset()
     keep_link = self._current_info is not None or bool(self.url_input.text().strip())
     if not keep_link:
         self._clear_inputs()
     if self._job_running() or self._has_waiting_job():
         self.set_state(TabState.DOWNLOADING)
     elif self._current_info is not None:
         self.set_state(TabState.READY)
     else:
         self.set_state(TabState.IDLE)
     ```
  6. Verify in `_apply_state_visibility(TabState.DOWNLOADING)`:
     - `self.fetch_btn.set_loading(False)` ensures spinner stops.
     - `self.url_input.setEnabled(True)` ensures link box remains editable.
     - `has_new_link = self._current_info is not None`: shows info card, enables quality combo, and enables `queue_btn`.
- **Test First:** Chunk 1 tests are already written and failing.
- **Done When:** All Chunk 1 tests (T1–T8) pass, and all existing tests in `test_tab_state_machine.py`, `test_tab_flow.py`, `test_tab_looks.py`, `test_per_item_cards.py`, and `test_recent_sync.py` pass with zero regressions.
- **Commit Message:** `fixQ.2: leave the fetching state correctly and keep a pending link (video)`

---

### Chunk 3: Audio Tab
- **Goal:** Port the exact test suite and fix to `AudioTab`.
- **Allowed Files:** `app/ui/audio_tab.py`, `tests/test_tab_state_machine.py`.
- **Steps:**
  1. Add audio equivalents of tests T1–T8 in `tests/test_tab_state_machine.py` targeting `AudioTab` and manager `"audio"`.
  2. Run the tests to confirm the identical 6 failures on `AudioTab`.
  3. Apply the exact same logic in `app/ui/audio_tab.py`:
     - Add `_has_waiting_job() -> bool: return bool(get_download_manager("audio").waiting_jobs)`
     - Update `_on_info_fetched` to transition to `DOWNLOADING` if `_job_running()` else `READY`.
     - Update `_on_info_failed` to transition to `DOWNLOADING` if `_job_running()` else `IDLE`.
     - Update `_on_manager_finished`, `_on_manager_failed`, and `_on_manager_cancelled` with `keep_link` logic and `_has_waiting_job()` checks.
  4. Verify all audio tests pass.
- **Test First:** Run audio tests and confirm failure before applying fix to `audio_tab.py`.
- **Done When:** All video and audio tests pass cleanly.
- **Commit Message:** `fixQ.3: same fix for the audio tab (tests first)`

---

### Chunk 4: Fetch Robustness
- **Goal:** Verify and guard edge cases in the fetch flow across both tabs.
- **Allowed Files:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/test_tab_state_machine.py`.
- **Steps:**
  1. Test sequence tracking (`_fetch_seq`): when user pastes link A then quickly link B before A finishes, verify response A is discarded and tab transitions cleanly for B.
  2. Test tab reset / clear during active fetch: verify no crash and no stale card populated when fetch returns.
  3. Verify spinner state (`_is_loading == False`) across all exit points: fetched, failed, reset.
  4. Add only minimal guards demanded by any failing robustness tests.
- **Test First:** Add robustness tests to `tests/test_tab_state_machine.py`.
- **Done When:** All robustness tests pass cleanly without touching any protected files.
- **Commit Message:** `fixQ.4: fetch flow guards`

---

### Chunk 5: Final Gate
- **Goal:** Complete full verification gate with zero regressions.
- **Allowed Files:** None (verification and gate check only).
- **Steps:**
  1. Run full test suite without `--ignore`:
     `python -m pytest -q -rf -p no:cacheprovider`
     Confirm all tests pass except known baseline exception (`test_exact_command_string_unicode`).
  2. Verify scope:
     `git diff --name-only 7418d4f HEAD`
     Confirm diff only contains `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/`, `docs/`, `plan/`.
  3. Check code cleanliness:
     `git grep -n "print(" -- app` -> 0 hits.
     `git grep -n "shell=True" -- app` -> 0 hits.
  4. Provide manual verification check instructions (a through f).
- **Done When:** Full test suite passes, scope check passes, checks list presented, waiting for "approved final".

---

### Chunk 6: Save to GitHub
- **Goal:** Push `fix/ui-pass` branch to GitHub and fast-forward merge to `main` upon explicit approval.
- **Steps:**
  1. `git status` (clean)
  2. `git fetch origin`
  3. `git status -sb` (not behind)
  4. `git push origin fix/ui-pass` (never `--force`)
  5. `git rev-parse HEAD origin/fix/ui-pass` (same hash twice)
  6. Ask user: "Merge into main? (approved merge)"
  7. Upon receiving "approved merge":
     ```bash
     git checkout main
     git pull --ff-only origin main
     git merge --ff-only fix/ui-pass
     python -m pytest -q -rf -p no:cacheprovider
     git push origin main
     git checkout fix/ui-pass
     ```

---

## 3. Questions & Recommended Answers

| # | Question | Recommended Answer |
|---|---|---|
| **Q1** | When `_on_manager_cancelled` runs and `self._current_info` is `None`, but the user has typed text in `url_input` (e.g. fetch is pending or failed), should that typed URL be kept? | **Yes.** Use `keep_link = self._current_info is not None or bool(self.url_input.text().strip())`. Only call `_clear_inputs()` when `not keep_link`. This satisfies Decision D2. |
| **Q2** | In tests, how should `manager.waiting_jobs` be simulated given that `waiting_jobs` is a property backed by `self._waiting_queue`? | **Use `monkeypatch.setattr(mgr, "_waiting_queue", [job2])`.** This matches the existing convention in `test_download_lanes.py` and `test_per_item_cards.py`. |
| **Q3** | When a download completes and the user has a fetched link ready (`self._current_info is not None`), what state should the tab transition to if there are no waiting jobs? | **`TabState.READY`.** This keeps the fetched title, thumbnail, and Download button immediately available for the user. |
| **Q4** | When a download completes and there are queued waiting jobs (`_has_waiting_job()`), what state should the tab transition to? | **`TabState.DOWNLOADING`.** This prevents any flicker or temporary display of the `IDLE` state between sequential queue items. |
| **Q5** | Should Chunk 1 failing tests be committed as `fixQ.1` immediately upon plan approval before making Chunk 2 code changes? | **Yes.** Commit `fixQ.1` first so git history clearly preserves the failing tests before the fix in `fixQ.2`. |
