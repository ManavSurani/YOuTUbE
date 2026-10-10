# Phase A: Add to Queue Works While Downloading & Sticky Look

---

## A. Header

### Goal
Fix the button state machine on both the Video and Audio tabs so that:
1. "Add to queue" is always clickable while a download is running. Clicking it with an empty or unfetched link shows a friendly 4-second inline hint without enqueuing.
2. Pasting or fetching a new link during an active download maintains the "Cancel" button and keeps "Download" hidden.
3. Clearing the URL input while a download is running never resets the tab to IDLE or hides Cancel.
4. Active downloads belonging to the other tab kind (e.g. audio running while on Video tab) do not affect this tab's buttons.
5. Thumbnail image bytes are persisted to disk via `save_thumbnail()` before the job is placed into the queue or started via download.

### Rows Fixed
- **A-1**: Empty link box greys out "Add to queue" while downloading.
- **A-2**: Pasting link during download breaks buttons (hides Cancel, shows Download).
- **A-3**: Clearing link box sets IDLE and hides Cancel during download.

### Depends On
- Baseline commit: `62c8db1`. Depends on no prior phases.

### Allowed Files (Exact Paths)
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `tests/test_tab_state_machine.py`
- `tests/test_tab_flow.py`
- `tests/test_tab_looks.py`

### The 15 Strictly Protected Files (Zero Edits Permitted)
```
1.  app/core/downloader.py         6.  app/core/history_db.py         11. app/core/app_updater.py
2.  app/core/proc.py               7.  app/core/history_service.py    12. app/core/tool_manager.py
3.  app/core/info_fetcher.py       8.  app/core/thumbnails.py         13. app/tools.json
4.  app/core/jobs.py               9.  app/core/errors.py             14. installer/setup.iss
5.  app/core/url_tools.py          10. app/core/network_monitor.py    15. app/ui/theme.py
```

### Do / Don't Table
| Do | Don't |
|---|---|
| Use `_job_running()` checking `active_job.kind == "video"` (or `"audio"`) | Don't treat a running audio job as a running video job |
| Keep Cancel visible and Download hidden while this tab's job runs | Don't allow `_on_info_fetched()` to replace Cancel with Download |
| Show 4-second hint via `self.inline_msg.show_info(..., auto_hide_ms=4000)` | Don't enqueue empty or unvalidated jobs |
| Call `save_thumbnail()` before `get_download_manager().enqueue()` in `start_download()` and `add_to_queue()` | Don't touch `app/core/thumbnails.py` (call it as a caller only) |
| Follow standard 5-step chunk cycle | Don't make any changes outside allowed files |

---

## B. Chunks

> [!NOTE]
> **Illustrative Snippets:** All code snippets in this plan are illustrative guidelines. The tabs do not have a `self.manager` attribute—they call `get_download_manager()` inline. The agent must read the real method in the local file first and adapt the implementation to the exact existing structure and variable names. Do not add a `self.manager` attribute.

### Chunk A.1: Confirm & Reproduce with Failing Tests (Video Tab)

- **Goal:** Write unit tests reproducing A-1, A-2, A-3, lane kind isolation, state-dependent queue button enablement, and cancel state restoration on the Video tab, proving they fail on the current code.
- **Files Allowed:** `tests/test_tab_state_machine.py`
- **Exact Steps:**
  1. Open `tests/test_tab_state_machine.py`.
  2. Add parametrised test `test_video_tab_queue_btn_enablement_by_state`:
     - Parametrise over the 5 states/contexts defined in the State & Button Enablement Table below:
       1. Job of kind `"video"` running, link box empty or not fetched -> `queue_btn.isVisibleTo(video_tab)` True, `queue_btn.isEnabled()` True, `cancel_btn.isVisibleTo(video_tab)` True, `download_btn.isVisibleTo(video_tab)` False.
       2. Job running, fetch in progress (`FETCHING`) -> `queue_btn.isVisibleTo(video_tab)` True, `queue_btn.isEnabled()` False, `cancel_btn.isVisibleTo(video_tab)` True, `download_btn.isVisibleTo(video_tab)` False.
       3. Job running, link fetched (`READY`) -> `queue_btn.isVisibleTo(video_tab)` True, `queue_btn.isEnabled()` True, `cancel_btn.isVisibleTo(video_tab)` True, `download_btn.isVisibleTo(video_tab)` False.
       4. Job running, offline (`OFFLINE`) -> `queue_btn.isVisibleTo(video_tab)` True, `queue_btn.isEnabled()` False, `cancel_btn.isVisibleTo(video_tab)` True, `download_btn.isVisibleTo(video_tab)` False.
       5. No job running -> `queue_btn.isVisibleTo(video_tab)` False.
  3. Add test `test_video_tab_queue_btn_enabled_when_downloading_empty_box`:
     - Set up `video_tab` with mock active job (`kind="video"`).
     - Transition to downloading state with empty URL input.
     - Assert `queue_btn.isVisibleTo(video_tab)` is True and `queue_btn.isEnabled()` is True.
  4. Add test `test_video_tab_pasting_link_during_download_keeps_cancel`:
     - While downloading, simulate typing/pasting a new link and entering `FETCHING` state.
     - Assert `cancel_btn.isVisibleTo(video_tab)` is True and `download_btn.isVisibleTo(video_tab)` is False.
  5. Add test `test_video_tab_info_fetched_during_download_keeps_cancel`:
     - While downloading, simulate fetch completion (`_on_info_fetched`).
     - Assert `cancel_btn.isVisibleTo(video_tab)` is True, `download_btn.isVisibleTo(video_tab)` is False, and `queue_btn.isEnabled()` is True.
  6. Add test `test_video_tab_clearing_link_during_download_keeps_cancel`:
     - While downloading, simulate clearing the URL input to `""`.
     - Assert `cancel_btn.isVisibleTo(video_tab)` is True.
  7. Add test `test_video_tab_job_running_kind_isolation`:
     - Set active job with `kind="audio"`.
     - Assert `video_tab._job_running()` returns `False`.
     - When link is ready, assert `download_btn.isVisibleTo(video_tab)` is True and `cancel_btn.isVisibleTo(video_tab)` is False.
  8. Add test `test_video_tab_cancel_download_restores_correct_state`:
     - If link is fetched, `cancel_download()` restores `TabState.READY`.
     - If link is empty, `cancel_download()` restores `TabState.IDLE`.
  *(Note on tests: Use `widget.isVisibleTo(tab)` or show the tab first instead of `isVisible()`, because widgets in unshown windows report False in Qt.)*
  9. Run `pytest tests/test_tab_state_machine.py` and confirm all new tests fail for the exact reasons identified.
- **Done When:** All tests fail with clear assertion failures matching A-1, A-2, A-3, and the state enablement table.
- **Commit Message:** `testA.1: failing tests for video tab sticky downloading look`

---

### Chunk A.2: Make the Downloading Look Sticky (Video Tab)

- **Goal:** Update `video_tab.py` to maintain the downloading presentation while a video job is active, configure Add to queue enablement per the agreed state table, and handle cancel state restoration.
- **Files Allowed:** `app/ui/video_tab.py`

#### State & Button Enablement Table (Video Tab)

| State / Context | Add to Queue Button | Cancel Button | Download Button | Click Behavior / Notes |
|---|---|---|---|---|
| **Job running, link empty or not fetched** | Visible, **ENABLED** | Visible & Enabled | Hidden | Click shows 4-second hint via `show_info()`, nothing enqueued |
| **Job running, fetch in progress (`FETCHING`)** | Visible, **DISABLED** | Visible & Enabled | Hidden | Disabled while fetch worker is resolving URL |
| **Job running, link fetched (`READY`)** | Visible, **ENABLED** | Visible & Enabled | Hidden | Click enqueues job and resets inputs |
| **Job running, offline (`OFFLINE`)** | Visible, **DISABLED** | Visible & Enabled | Hidden | Disabled while network is offline |
| **No job running** | **HIDDEN** | Hidden (or normal) | Visible (when ready) | Normal tab behavior when no job is active |

*Cancel stays visible and enabled in every row where a job is running, including FETCHING.*  
*Download stays hidden in every row where a job is running.*

- **Exact Steps:**
  1. In `video_tab.py`, define helper method using the existing access pattern `get_download_manager().active_job` (do NOT add a `self.manager` attribute; Phase C later adds the kind argument):
     ```python
     def _job_running(self) -> bool:
         job = get_download_manager().active_job
         return job is not None and getattr(job, "kind", "") == "video"
     ```
  2. In `_apply_state_visibility(self)` and `set_state(self, state)`:
     - If `self._job_running()` is True:
       - Force `self.cancel_btn.setVisible(True)` and `self.cancel_btn.setEnabled(True)` across all states (including `FETCHING` and `OFFLINE`).
       - Force `self.download_btn.setVisible(False)`.
       - Force `self.queue_btn.setVisible(True)`.
       - Set `queue_btn` enablement per the table:
         - Disabled if `state in (TabState.FETCHING, TabState.OFFLINE)`.
         - Enabled if `state == TabState.DOWNLOADING` (allows clicking to trigger the 4-second hint when empty, or enqueuing if fetched).
         - Enabled if `state == TabState.READY` and `self._current_info is not None`.
       - Keep `self.progress_card.setVisible(True)`.
  3. In `_on_url_text_changed(self, text)`:
     - If `self._job_running()`, do not switch to `TabState.IDLE` when `text.strip()` is empty; remain in downloading presentation.
  4. In `fetch_url(self)`:
     - If `self._job_running()`, preserve `cancel_btn` visibility, hide `download_btn`, and disable `queue_btn` during fetch.
  5. In `_on_info_fetched(self, info)`:
     - If `self._job_running()`, show card with fetched details, keep `cancel_btn` visible, keep `download_btn` hidden, and enable `queue_btn`.
  6. In `add_to_queue(self)`:
     - If `not self._current_info`:
       - Call `self.inline_msg.show_info("Paste a YouTube link first, then press Add to queue.", auto_hide_ms=4000)`.
       - Return immediately without enqueuing.
     - If `self._current_info` exists:
       - Build and enqueue the job.
       - Clear URL input and media card.
       - If `self._job_running()`, maintain downloading state and visible Cancel button.
  7. In `cancel_download(self)`:
     - If `self._current_info is not None`:
       - `self.set_state(TabState.READY)`
     - Else:
       - `self.set_state(TabState.IDLE)`
  8. In `_on_manager_finished` and `_on_manager_cancelled`:
     - Clean up active job presentation and return tab to `READY` (if link present) or `IDLE`.
  9. Run `pytest tests/test_tab_state_machine.py tests/test_tab_flow.py tests/test_tab_looks.py`.
- **Done When:** All Chunk A.1 tests (including `test_video_tab_queue_btn_enablement_by_state`) pass and zero existing video tab tests break.
- **Commit Message:** `fixA.2: video tab sticky downloading look and add to queue guard`

---

### Chunk A.3: Mirror Sticky Downloading Look in Audio Tab

- **Goal:** Apply the identical sticky state logic, lane isolation, state-dependent queue button enablement table, and Add to queue guard to `audio_tab.py`.
- **Files Allowed:** `app/ui/audio_tab.py`, `tests/test_tab_state_machine.py`

#### State & Button Enablement Table (Audio Tab)

| State / Context | Add to Queue Button | Cancel Button | Download Button | Click Behavior / Notes |
|---|---|---|---|---|
| **Job running, link empty or not fetched** | Visible, **ENABLED** | Visible & Enabled | Hidden | Click shows 4-second hint via `show_info()`, nothing enqueued |
| **Job running, fetch in progress (`FETCHING`)** | Visible, **DISABLED** | Visible & Enabled | Hidden | Disabled while fetch worker is resolving URL |
| **Job running, link fetched (`READY`)** | Visible, **ENABLED** | Visible & Enabled | Hidden | Click enqueues job and resets inputs |
| **Job running, offline (`OFFLINE`)** | Visible, **DISABLED** | Visible & Enabled | Hidden | Disabled while network is offline |
| **No job running** | **HIDDEN** | Hidden (or normal) | Visible (when ready) | Normal tab behavior when no job is active |

*Cancel stays visible and enabled in every row where a job is running, including FETCHING.*  
*Download stays hidden in every row where a job is running.*

- **Exact Steps:**
  1. In `tests/test_tab_state_machine.py`, add parametrised test `test_audio_tab_queue_btn_enablement_by_state` and matching Audio tab tests (using `widget.isVisibleTo(audio_tab)` for all visibility assertions):
     - `test_audio_tab_queue_btn_enablement_by_state`: parametrised over the 5 state combinations from the table.
     - `test_audio_tab_queue_btn_enabled_when_downloading_empty_box`: assert `queue_btn.isVisibleTo(audio_tab)` and `queue_btn.isEnabled()`.
     - `test_audio_tab_pasting_link_during_download_keeps_cancel`: assert `cancel_btn.isVisibleTo(audio_tab)` and not `download_btn.isVisibleTo(audio_tab)`.
     - `test_audio_tab_info_fetched_during_download_keeps_cancel`: assert `cancel_btn.isVisibleTo(audio_tab)`, not `download_btn.isVisibleTo(audio_tab)`, and `queue_btn.isEnabled()`.
     - `test_audio_tab_clearing_link_during_download_keeps_cancel`: assert `cancel_btn.isVisibleTo(audio_tab)`.
     - `test_audio_tab_job_running_kind_isolation`: assert `active_job.kind == "video"` leaves `audio_tab._job_running()` False.
     - `test_audio_tab_cancel_download_restores_correct_state`.
  2. Run `pytest tests/test_tab_state_machine.py` to confirm Audio tests fail.
  3. In `audio_tab.py`, define helper method using existing access pattern `get_download_manager().active_job` (do NOT add a `self.manager` attribute):
     ```python
     def _job_running(self) -> bool:
         job = get_download_manager().active_job
         return job is not None and getattr(job, "kind", "") == "audio"
     ```
  4. Apply the sticky visibility and enablement rules from the table to `_apply_state_visibility`, `set_state`, `_on_url_text_changed`, `fetch_url`, and `_on_info_fetched`.
  5. In `add_to_queue(self)`:
     - If `not self._current_info`, show the 4-second hint:
       `self.inline_msg.show_info("Paste a YouTube link first, then press Add to queue.", auto_hide_ms=4000)`
     - If info exists, enqueue job and reset input while maintaining sticky download look if running.
  6. In `cancel_download(self)`:
     - Restore `TabState.READY` if fetched link present, else `TabState.IDLE`.
  7. Run `pytest tests/test_tab_state_machine.py tests/test_tab_flow.py tests/test_tab_looks.py`.
- **Done When:** All Audio tab tests (including `test_audio_tab_queue_btn_enablement_by_state`) pass and existing Audio tests pass.
- **Commit Message:** `fixA.3: audio tab sticky downloading look and add to queue guard`

---

### Chunk A.4: Persist Thumbnail Before Enqueueing Job (start_download and add_to_queue)

- **Goal:** Ensure thumbnail bytes are saved to disk via `save_thumbnail` before adding the job to the queue in BOTH `start_download()` and `add_to_queue()` across both tabs, avoiding missing thumbnails / placeholder displays in the progress card.
- **Files Allowed:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/test_tab_flow.py`
- **Exact Steps:**
  1. In `tests/test_tab_flow.py`, add 4 tests (2 tabs x 2 paths) plus the empty-bytes cases:
     - `test_video_tab_start_download_saves_thumbnail_before_enqueue`: asserts `save_thumbnail(job.video_id, job.thumbnail_bytes)` is called exactly once, before `enqueue()`, when `start_download()` is invoked with thumbnail bytes present.
     - `test_video_tab_add_to_queue_saves_thumbnail_before_enqueue`: asserts `save_thumbnail(job.video_id, job.thumbnail_bytes)` is called exactly once, before `enqueue()`, when `add_to_queue()` is invoked with thumbnail bytes present.
     - `test_audio_tab_start_download_saves_thumbnail_before_enqueue`: asserts `save_thumbnail(job.video_id, job.thumbnail_bytes)` is called exactly once, before `enqueue()`, when `start_download()` is invoked with thumbnail bytes present.
     - `test_audio_tab_add_to_queue_saves_thumbnail_before_enqueue`: asserts `save_thumbnail(job.video_id, job.thumbnail_bytes)` is called exactly once, before `enqueue()`, when `add_to_queue()` is invoked with thumbnail bytes present.
     - `test_video_tab_empty_thumbnail_bytes_does_not_call_save_thumbnail`: asserts `save_thumbnail` is NOT called when `job.thumbnail_bytes` is empty/None on `video_tab`.
     - `test_audio_tab_empty_thumbnail_bytes_does_not_call_save_thumbnail`: asserts `save_thumbnail` is NOT called when `job.thumbnail_bytes` is empty/None on `audio_tab`.
  2. Run `pytest tests/test_tab_flow.py` and see tests execute.
  3. In `app/ui/video_tab.py`:
     - In BOTH `start_download()` and `add_to_queue()` (or shared helper if both share one): right before `get_download_manager().enqueue(job)`, if `job.thumbnail_bytes` is not empty, call:
       ```python
       if job.thumbnail_bytes:
           save_thumbnail(job.video_id, job.thumbnail_bytes)
       ```
  4. In `app/ui/audio_tab.py`:
     - In BOTH `start_download()` and `add_to_queue()` (or shared helper if both share one): right before `get_download_manager().enqueue(job)`, if `job.thumbnail_bytes` is not empty, call:
       ```python
       if job.thumbnail_bytes:
           save_thumbnail(job.video_id, job.thumbnail_bytes)
       ```
  5. Run `pytest tests/test_tab_flow.py`.
- **Done When:** A.4 lists four tests (2 tabs x 2 paths) plus the empty-bytes case, all passing cleanly.
- **Commit Message:** `fixA.4: persist thumbnail to disk before enqueueing in start_download and add_to_queue`


---

## C. Verification Gate: Phase A

### Scope Proof
Run:
```bash
git diff --name-only 62c8db1
```
Must list ONLY:
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `tests/test_tab_state_machine.py`
- `tests/test_tab_flow.py`
- `tests/test_tab_looks.py`
- Plan / docs files (`gemini.md`, `docs/`, `plan/`)

### Test Command and Expected Output
```bash
pytest tests/test_tab_state_machine.py tests/test_tab_flow.py tests/test_tab_looks.py
```
Expected output: **All phase tests pass (0 failures, 0 errors)**.

And full suite check:
```bash
pytest
```
Expected output: **Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline.**

### Real-PC Checks
1. **Empty Link Hint (Video Tab):** Start a video download. Leave the URL input empty. Click `Add to queue`.
   - *Expect:* 4-second hint appears: `"Paste a YouTube link first, then press Add to queue."`. The active download continues smoothly; Cancel button remains visible.
2. **Paste Second Link (Video Tab):** While video is downloading, paste a second video link.
   - *Expect:* Thumbnail and title load. Cancel button remains visible. Download button remains hidden. `Add to queue` is enabled.
3. **Enqueue Second Link (Video Tab):** Click `Add to queue` with the second link loaded.
   - *Expect:* Inputs clear. Item appears in waiting queue. Running download continues with active progress bar and Cancel button.
4. **Clear URL Box (Video Tab):** While video is downloading, type text into URL box and delete it with Backspace.
   - *Expect:* Cancel button remains visible. Tab does not flip to IDLE.
5. **Cross-Tab Isolation Check:** Start a video download. Switch to Audio tab.
   - *Expect:* Audio tab shows its normal state (Download visible when ready). The Audio tab must not show Cancel for the video job. Until Phase C, a video and an audio download share one queue, so an audio download started while a video runs will WAIT until the video finishes. This is expected. Parallel downloads arrive in Phase C.
6. **Audio Tab Mirror Check:** Repeat checks 1 through 4 on the Audio tab with an audio download.
   - *Expect:* Identical behaviour for audio downloads.
7. **Cancel Restoration Check:** With a link fetched, click Cancel on a running download.
   - *Expect:* Tab returns to `READY` with the fetched link card and Download button visible.

### Stop-and-Ask Triggers Specific to Phase A
- If fixing a button state appears to require editing `app/core/jobs.py` or `app/core/downloader.py`, STOP and ask the owner.
- If a test fails after two attempts, STOP and ask the owner.
- At the verification gate, report results and wait for "approved".

---

## D. Evidence Template for docs/verification/phase_A.md

```markdown
# Phase A Verification Evidence

## Scope Proof
Command: `git diff --name-only 62c8db1`
Output:
[Paste terminal output here]

## Pytest Output
Command: `pytest tests/test_tab_state_machine.py tests/test_tab_flow.py tests/test_tab_looks.py`
Output:
[Paste terminal output here]

## Real-PC Manual Checks
| Check # | Check Name | Result | Notes |
|---|---|---|---|
| 1 | Empty Link Hint (Video) | PASS / FAIL | |
| 2 | Paste Second Link (Video) | PASS / FAIL | |
| 3 | Enqueue Second Link (Video) | PASS / FAIL | |
| 4 | Clear URL Box (Video) | PASS / FAIL | |
| 5 | Cross-Tab Isolation | PASS / FAIL | |
| 6 | Audio Tab Mirror Check | PASS / FAIL | |
| 7 | Cancel Restoration Check | PASS / FAIL | |

## Captured Assets
- Screenshot: `screenshot_phase_a_sticky.png`

## Decision
- Status: PASS / FAIL
- Reason: Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline; zero protected files modified, real-PC checks verified.
```

---

## E. "After This Phase" Message

### Report to the Owner
When all Phase A chunks are complete and the verification gate has passed:
1. Send a concise report summarizing:
   - Automated test results (number of tests passed).
   - Scope verification output confirming zero protected files touched.
   - Real-PC checks confirmation.
2. Ask for explicit approval to proceed to Phase B.

### Exactly What Words to Wait For
Wait for the owner to reply with:
> **approved**

**DO NOT TOUCH ANY CODE IN PHASE B UNTIL THE OWNER REPLIES "approved".**

### Commit Command for the Gate
```bash
git commit --allow-empty -m "gate: phase A verified and approved"
```
*(Or commit `docs/verification/phase_A.md` if recorded on disk).*
