# Phase D: Per-Item Queue Progress Bars & Strict Tab Separation (UI)

---

## A. Header

### Goal
Implement visual Polish for the queue UI so that:
1. Each queued item in `QueueWidget` displays as a distinct card with its own 6px progress bar (value 0 for waiting), title, thumbnail, status, and Remove/Retry buttons.
2. The running item continues to be rendered by the existing `ProgressCard` on the tab with full live progress, speed, ETA, and size, with the tab's `Cancel` button as its sole Cancel control.
3. Deferred jobs display status: `"Waiting for the same video to finish"`.
4. Strict tab separation is visually enforced: audio jobs NEVER appear on the Video tab, and video jobs NEVER appear on the Audio tab.
5. Signal connections in `QueueWidget` are bound strictly once in `__init__` (never inside `refresh()`).
6. The queue area scrolls smoothly inside a `QScrollArea` when many items are queued without growing the main window.

### Rows Fixed
- **D-1**: Shared queue widget displays jobs of both types on both tabs.
- **D-2**: `QueueRow` lacks individual progress bars for queued items.
- **R2**: Each video in queue gets its own card with its own progress bar.
- **R4**: Audio items must never appear on Video page.
- **R5**: Video items must never appear on Audio page.

### Depends On
- Phase C must be completed, verified, and explicitly approved by the owner before starting Phase D.

### Allowed Files (Exact Paths)
- `app/ui/queue_widget.py`
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `tests/test_per_item_cards.py`
- `tests/test_queue.py`
- `tests/test_tab_flow.py`

### The 15 Strictly Protected Files (Zero Edits Permitted)
```
1.  app/core/downloader.py         6.  app/core/history_db.py         11. app/core/app_updater.py
2.  app/core/proc.py               7.  app/core/history_service.py    12. app/core/tool_manager.py
3.  app/core/info_fetcher.py       8.  app/core/thumbnails.py         13. app/tools.json
4.  app/core/jobs.py               9.  app/core/errors.py             14. installer/setup.iss
5.  app/core/url_tools.py          10. app/core/network_monitor.py    15. app/ui/theme.py
```

### Component Roles
- **Running Item:** Handled by existing `ProgressCard` on the tab with live progress bar, speed, ETA, size, and the tab's `Cancel` button. Do NOT rewrite `ProgressCard` into a new `ItemProgressCard`.
- **Waiting & Failed Items:** Handled by `QueueWidget` and `QueueRow`. Add a 6px progress bar to `QueueRow` (value 0 for waiting; value 0 with red indicator for failed).

### Do / Don't Table
| Do | Don't |
|---|---|
| Keep existing `ProgressCard` for running items | Don't invent duplicate running cards in `QueueWidget` |
| Add 6px progress bar to `QueueRow` | Don't change design system colors or font styles |
| Connect to manager signals strictly ONCE in `QueueWidget.__init__` | Don't connect signals inside `refresh()` or on every redraw |
| Connect `QueueWidget` only to `queue_changed` | Don't re-render queue on high-frequency `progress` signals |
| Isolate video and audio items strictly by lane kind | Don't mix queue items across tabs |

---

## B. Chunks

### Chunk D.1: Per-Item Progress Bar on QueueRow & Deferred Status Text

- **Goal:** Enhance `QueueRow` to include an individual progress bar for queued items and display deferred status text.
- **Files Allowed:** `app/ui/queue_widget.py`, `tests/test_per_item_cards.py`
- **Exact Steps:**
  1. In `app/ui/queue_widget.py:QueueRow`:
     - For the 6px progress bar: `ProgressCard` draws its bar using `ModernProgressBar` in `app/ui/kit/progress_card.py` (which has dynamic corner radius `radius = h / 2.0`). Reuse `ModernProgressBar` by importing it and setting `setFixedHeight(6)` below the metadata row (giving it 3px rounded ends with `#282828` groove). If anything is needed that cannot be reused without creating a new class, **STOP and ask the owner before creating one**.
     - For waiting items:
       - Set progress bar value to 0 (empty groove).
       - If `job.job_id in manager.deferred_job_ids()`:
         - Status text: `"Waiting for the same video to finish"`
       - Else:
         - Status text: `"Waiting"`
       - Display `Remove` button.
     - For failed items:
       - Note: Failure reasons are retrieved from `manager.failed_jobs` tuples (`jobs.py` is protected and frozen).
       - In `QueueWidget.refresh()`, retrieve failure reasons from `manager.failed_jobs` (list of `(job, reason)` tuples).
       - If `reason` is empty or whitespace, fall back to `"Something went wrong"`.
       - Status text: `f"Failed: {reason or 'Something went wrong'}"`
       - Set progress bar value to 0.
       - Display `Retry` and `Remove` buttons.
     - Wire `Remove` button to `manager.cancel_job(job.job_id)`.
     - Wire `Retry` button to `manager.retry_job(job.job_id)`.
  2. Create `tests/test_per_item_cards.py`:
     - `test_queue_row_has_progress_bar`: instantiate `QueueRow` with waiting job, assert progress bar widget exists with value 0 and height 6.
     - `test_queue_row_deferred_status_text`: mock manager with `deferred_job_ids() -> {job_id}`, assert status label contains `"Waiting for the same video to finish"`.
     - `test_queue_row_failed_state`: instantiate `QueueRow` using a `(job, reason)` tuple from `manager.failed_jobs`, assert reason displayed (or fallback `"Something went wrong"` if reason is empty), progress bar value is 0, and Retry/Remove buttons exist.
     - `test_queue_row_thumbnail_saved_shows_real_image`: for a job whose thumbnail was saved (Phase A.4), assert `QueueRow` displays the real image, not the placeholder.
     - `test_queue_row_thumbnail_not_saved_shows_placeholder`: for a job with no saved thumbnail, assert `QueueRow` displays the placeholder without errors.
     - `test_queue_row_remove_action`: clicking Remove calls `manager.cancel_job(job.job_id)`.
     - `test_queue_row_retry_action`: clicking Retry calls `manager.retry_job(job.job_id)`.
  3. Run `pytest tests/test_per_item_cards.py`.
- **Done When:** D.1 extracts failure reasons from manager.failed_jobs (never referencing unmapped attributes on jobs), reuses `ModernProgressBar` (or stops to ask if a new class is needed), contains the thumbnail tests, and all unit tests pass.
- **Commit Message:** `featD.1: per-item progress bar on queue row and deferred status text`

---

### Chunk D.2: Strict Tab Separation & Single Signal Connection in QueueWidget

- **Goal:** Ensure `QueueWidget` connects to its lane manager strictly once in `__init__` and renders items strictly belonging to its lane.
- **Files Allowed:** `app/ui/queue_widget.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/test_per_item_cards.py`
- **Exact Steps:**
  1. In `app/ui/queue_widget.py:QueueWidget`:
     - In `__init__(self, kind: str, parent=None)`:
       - Store `self.kind = kind`.
       - Connect `self.manager.queue_changed.connect(self.refresh)` **strictly ONCE** here.
       - Never connect signals inside `refresh()`.
       - Do NOT connect to high-frequency `progress` signal in `QueueWidget` (running progress is handled by `ProgressCard`).
     - In `refresh(self)`:
       - Retrieve `waiting_jobs = self.manager.waiting_jobs`.
       - Filter strictly: if `job.kind != self.kind`, skip the job and log a warning (never use `assert` in UI code).
       - If no waiting or failed jobs exist for this lane, hide `QueueWidget`.
       - If items exist, show header `Up next ({count})` and render each `QueueRow`.
  2. In `app/ui/video_tab.py` and `app/ui/audio_tab.py`:
     - Verify queue widget only receives and displays this tab's kind.
  3. In `tests/test_per_item_cards.py`:
     - `test_queue_widget_single_signal_connection`: call `refresh()` 5 times consecutively. Emit 1 `queue_changed` signal -> assert `refresh()` is invoked exactly once. Emit 50 `progress` signals -> assert 0 queue redraws occur.
     - `test_strict_tab_isolation_video`: enqueue an audio job into audio manager -> assert Video tab queue widget remains completely empty/hidden.
     - `test_strict_tab_isolation_audio`: enqueue a video job into video manager -> assert Audio tab queue widget remains completely empty/hidden.
     - `test_queue_widget_ignores_wrong_kind_without_exception`: inject a job of the wrong kind into waiting jobs -> assert `refresh()` skips the job and logs a warning without raising an exception.
  4. Run `pytest tests/test_per_item_cards.py tests/test_queue.py`.
- **Done When:** D.2 has no assert, skips mismatched jobs with a warning, and single signal connection test and strict tab isolation tests pass.
- **Commit Message:** `featD.2: strict tab isolation and single signal connection in queue widget`

---

### Chunk D.3: Scrolling Bounds & Layout Polish

- **Goal:** Ensure the queue area scrolls cleanly inside a `QScrollArea` when many items are queued without growing or distorting the main window.
- **Files Allowed:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `tests/test_per_item_cards.py`
- **Exact Steps:**
  1. In `app/ui/video_tab.py` and `app/ui/audio_tab.py`:
     - Apply horizontal scrollbar policy where the scroll area is created in `_setup_ui()`:
       - Set `scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)` on `scroll = QScrollArea(self)`.
     - Ensure the scroll container layout maintains clean vertical scrolling when items are added.
  2. In `tests/test_per_item_cards.py`:
     - `test_tab_scroll_bounds_with_many_queued_items`: with 15 waiting items enqueued in the tab, verify the tab's vertical scrollbar maximum is above 0, the horizontal scrollbar policy is off (`ScrollBarAlwaysOff`), and the window height does not change / expand.
  3. Run `pytest tests/test_per_item_cards.py`.
- **Done When:** D.3 edits only the tab files for scrolling, and the scrolling bounds test passes cleanly.
- **Commit Message:** `featD.3: apply horizontal scrollbar policy in video and audio tabs and verify scroll bounds`

---

## C. Verification Gate: Phase D

### Scope Proof
Run:
```bash
git diff --name-only 62c8db1
```
Must list ONLY:
- `app/core/download_manager.py` (scheduling edits only)
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `app/ui/recent_list.py`
- `app/ui/queue_widget.py`
- `app/ui/main_window.py` (close event & offline)
- Test files under `tests/`
- Documentation files (`gemini.md`, `docs/`, `plan/`)

### Test Command and Expected Output
```bash
pytest tests/test_per_item_cards.py tests/test_queue.py tests/test_tab_flow.py
```
And full test suite pass:
```bash
pytest
```
Expected output: **Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline**.

### Real-PC Checks
1. **Per-Item Cards with Progress Bars (Video Tab):**
   - Start 1 video download.
   - Queue 2 additional videos.
   - *Expect:* Running video shows live speed, ETA, and size in `ProgressCard`. The 2 queued videos each show their own card in `QueueWidget` with thumbnail, title, an empty 6px progress bar (value 0), status `"Waiting"`, and a `Remove` button.
2. **Transition Between Items:**
   - Wait for Video 1 to finish.
   - *Expect:* `ProgressCard` shows Done, then transitions to Video 2. Video 2 moves from `QueueWidget` into `ProgressCard` and begins downloading. Video 3 moves to top of `QueueWidget`.
3. **Strict Tab Isolation:**
   - While video downloads are running and queued, switch to Audio tab.
   - *Expect:* Zero video items appear on the Audio tab.
   - Add 2 audio downloads.
   - *Expect:* Audio downloads run in parallel in their own `ProgressCard` and `QueueWidget`.
4. **Remove Queued Item:**
   - Click `Remove` on a queued item in `QueueWidget`.
   - *Expect:* That item is removed immediately from the queue without interrupting the currently running download.
5. **Deferred Status Display:**
   - Add the same video URL to both Video and Audio tabs simultaneously.
   - *Expect:* The second item displays status `"Waiting for the same video to finish"` with an empty progress bar.

### Stop-and-Ask Triggers Specific to Phase D
- If styling cards requires modifying `app/ui/theme.py`, STOP and ask the owner.
- If any test fails after two attempts, STOP and ask the owner.
- At the verification gate, report results and wait for final sign-off.

---

## D. Evidence Template for docs/verification/phase_D.md

```markdown
# Phase D Verification Evidence

## Scope Proof
Command: `git diff --name-only 62c8db1`
Output:
[Paste terminal output here]

## Pytest Output
Command: `pytest`
Output:
[Paste terminal output here - full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline]

## Real-PC Manual Checks
| Check # | Check Name | Result | Notes |
|---|---|---|---|
| 1 | Per-Item Cards with Progress Bars | PASS / FAIL | |
| 2 | Transition Between Items | PASS / FAIL | |
| 3 | Strict Tab Isolation | PASS / FAIL | |
| 4 | Remove Queued Item | PASS / FAIL | |
| 5 | Deferred Status Display | PASS / FAIL | |

## Captured Assets
- Screenshot: `screenshot_phase_d_queue_cards.png`

## Decision
- Status: PASS / FAIL
- Reason: Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline; zero protected files modified, real-PC UI polish verified.
```

---

## E. "After This Phase" Message & Final Sign-Off Template

### Report to the Owner
When Phase D chunks are complete and the verification gate has passed:
1. Send the comprehensive final report summarizing the successful completion of all four phases (A, B, C, D).
2. Include the final scope proof command output (`git diff --name-only 62c8db1`).
3. Include the full pytest suite run confirmation (confirming full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline).
4. Provide the **Final Sign-Off Template** below for formal approval.

### Final Sign-Off Template
```markdown
# YOuTUbE: Multi-Lane Queue & UI Fixes - Final Sign-Off

- **Baseline Commit:** `62c8db1`
- **Total Phases Completed:** 4 (Phase A, Phase B, Phase C, Phase D)
- **Protected Files Integrity:** 15 of 15 protected files untouched (0 lines changed).
- **Automated Test Suite:** Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline.
- **Key Capabilities Delivered:**
  1. Add to queue is always clickable during downloads; friendly 4-second hint on empty box.
  2. Cancel button stays visible and Download stays hidden when pasting/fetching during download.
  3. "Recently downloaded" automatically clears/updates across Video and Audio tabs on History changes.
  4. Parallel dual lanes: 1 Video + 1 Audio running simultaneously without blocking each other.
  5. Same video ID deferral preserves strict FIFO order without temp file collisions.
  6. Per-item queue cards with 6px progress bars, thumbnail, and Remove/Retry buttons.
  7. Strict visual tab isolation: Audio never on Video tab, Video never on Audio tab.
  8. Graceful offline pause/resume and safe application close with active job protection.

Owner Approval: ___________________________ Date: ______________
```

### Commit Command for the Final Gate
```bash
git commit --allow-empty -m "gate: phase D verified and final project sign-off complete"
```
*(Or commit `docs/verification/phase_D.md` if recorded on disk).*
