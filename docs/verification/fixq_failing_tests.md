# Chunk 1: Failing Tests for Stuck Fetching State and Queue Behavior (Video Tab)

**Date:** 2026-10-17
**Command:** `python -m pytest tests/test_tab_state_machine.py -k "test_new_link_fetched_during_download_enables_add_to_queue or test_fetch_fails_during_running_download_returns_to_downloading or test_fetch_result_stops_fetch_button_spinner or test_cached_link_during_download_goes_to_downloading_with_queue_enabled or test_pending_link_survives_running_download_finished or test_pending_link_survives_running_download_failed_and_cancelled or test_two_queued_jobs_never_show_idle_between_finish_and_next_start or test_no_download_running_pasting_link_transitions_fetching_to_ready" -v`

## Test Summary
- **Collected:** 34 items (26 deselected, 8 selected)
- **Passed:** 2 passed (T4 cached link guard, T8 idle fetch guard)
- **Failed:** 6 failed (T1, T2, T3, T5, T6, T7)

---

## Detailed Failure Log

### T1: `test_new_link_fetched_during_download_enables_add_to_queue`
```
_________ test_new_link_fetched_during_download_enables_add_to_queue __________
tests\test_tab_state_machine.py:534: in test_new_link_fetched_during_download_enables_add_to_queue
    assert tab._state == TabState.DOWNLOADING  # fails today: stays FETCHING
E   assert <TabState.FETCHING: 2> == <TabState.DOWNLOADING: 4>
E    +  where <TabState.FETCHING: 2> = <app.ui.video_tab.VideoTab(0x23a256216b0)>._state
E    +  and   <TabState.DOWNLOADING: 4> = TabState.DOWNLOADING
```
**Reason:** In `_on_info_fetched`, when a download is running (`self._job_running()`), it executes `self._apply_state_visibility(self._state)`. Because `self._state` was set to `TabState.FETCHING` on link paste, it re-applies `TabState.FETCHING`. State remains `FETCHING`, link input and Add to queue button remain disabled, and spinner continues spinning.

---

### T2: `test_fetch_fails_during_running_download_returns_to_downloading`
```
_______ test_fetch_fails_during_running_download_returns_to_downloading _______
tests\test_tab_state_machine.py:554: in test_fetch_fails_during_running_download_returns_to_downloading
    assert tab._state == TabState.DOWNLOADING  # fails today: stays FETCHING
E   assert <TabState.FETCHING: 2> == <TabState.DOWNLOADING: 4>
E    +  where <TabState.FETCHING: 2> = <app.ui.video_tab.VideoTab(0x2a365f2ba30)>._state
E    +  and   <TabState.DOWNLOADING: 4> = TabState.DOWNLOADING
```
**Reason:** In `_on_info_failed`, when a download is running (`self._job_running()`), it executes `self._apply_state_visibility(self._state)`. Since `self._state` is `TabState.FETCHING`, it re-applies `TabState.FETCHING`.

---

### T3: `test_fetch_result_stops_fetch_button_spinner`
```
________________ test_fetch_result_stops_fetch_button_spinner _________________
tests\test_tab_state_machine.py:574: in test_fetch_result_stops_fetch_button_spinner
    assert tab.fetch_btn._is_loading is False  # fails today: stays FETCHING
E   assert True is False
E    +  where True = <app.ui.kit.buttons.AnimatedButton>._is_loading
```
**Reason:** Because the tab remains in `FETCHING` state, the Fetch button spinner remains active (`_is_loading == True`, `_spinner_timer.isActive() == True`).

---

### T4: `test_cached_link_during_download_goes_to_downloading_with_queue_enabled`
```
PASSED tests/test_tab_state_machine.py::test_cached_link_during_download_goes_to_downloading_with_queue_enabled
```
**Reason:** Cached links skip `set_state(TabState.FETCHING)` so they bypass the stuck state.

---

### T5: `test_pending_link_survives_running_download_finished`
```
____________ test_pending_link_survives_running_download_finished _____________
tests\test_tab_state_machine.py:621: in test_pending_link_survives_running_download_finished
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=BBBBBBBBBBB"  # fails today: cleared
E   AssertionError: assert '' == 'https://www.youtube.com/watch?v=BBBBBBBBBBB'
E     - https://www.youtube.com/watch?v=BBBBBBBBBBB
```
**Reason:** `_on_manager_finished` calls `self._clear_inputs()` and `self.set_state(TabState.IDLE)` unconditionally, wiping the pending URL and media card that the user prepared while the download was running.

---

### T6: `test_pending_link_survives_running_download_failed_and_cancelled`
```
______ test_pending_link_survives_running_download_failed_and_cancelled _______
tests\test_tab_state_machine.py:643: in test_pending_link_survives_running_download_failed_and_cancelled
    assert tab.url_input.text() == "https://www.youtube.com/watch?v=BBBBBBBBBBB"  # fails today: cleared
E   AssertionError: assert '' == 'https://www.youtube.com/watch?v=BBBBBBBBBBB'
E     - https://www.youtube.com/watch?v=BBBBBBBBBBB
```
**Reason:** `_on_manager_failed` and `_on_manager_cancelled` unconditionally wipe typed/pending input.

---

### T7: `test_two_queued_jobs_never_show_idle_between_finish_and_next_start`
```
_____ test_two_queued_jobs_never_show_idle_between_finish_and_next_start ______
tests\test_tab_state_machine.py:698: in test_two_queued_jobs_never_show_idle_between_finish_and_next_start
    assert TabState.IDLE not in observed_states  # fails today: [TabState.IDLE]
E   assert <TabState.IDLE: 1> not in [<TabState.IDLE: 1>]
E    +  where <TabState.IDLE: 1> = TabState.IDLE
```
**Reason:** `_on_manager_finished` transitions to `TabState.IDLE` unconditionally instead of checking `self._has_waiting_job()`.

---

### T8: `test_no_download_running_pasting_link_transitions_fetching_to_ready`
```
PASSED tests/test_tab_state_machine.py::test_no_download_running_pasting_link_transitions_fetching_to_ready
```
**Reason:** Normal single-link flow when idle continues to pass as expected.
