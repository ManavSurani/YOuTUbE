# Phase B: Clear History Updates Video and Audio Pages

---

## A. Header

### Goal
Fix the stale "Recently downloaded" bug so that when history items are cleared or deleted from the History tab, the "Recently downloaded" section on the Video and Audio tabs updates immediately upon switching to the tab, with zero application restart required.

### Rows Fixed
- **B-1**: `RecentList.refresh()` called only on tab init and job finish.
- **B-2**: `_on_clear_all` reloads only HistoryTab list; no signals sent.
- **B-3**: `refresh()` removes only plain widgets, leaving nested layout duplicate links (verified already clean, protected with test).
- **B-4**: Empty `RecentList` hides itself, preventing child `QShowEvent` from triggering auto-refresh.

### Depends On
- Phase A must be completed, verified, and explicitly approved by the owner before starting Phase B.

### Allowed Files (Exact Paths)
- `app/ui/recent_list.py`
- `tests/test_recent_list.py`
- `tests/test_recent_sync.py`

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
| Use `eventFilter` on parent to intercept `QEvent.Type.Show` | Don't rely on child `QShowEvent` (it never fires when widget is hidden) |
| Call `history_service.delete(row_id, delete_file=False)` in tests | Don't call `delete_item` (method does not exist on `history_service`) |
| Recursively clean layouts in `_clear_layout()` | Don't leave duplicate "See all" links or duplicate headers |
| Keep existing `RecentList` layout, colors, and fonts | Don't invent new signals or modify `history_tab.py` |

---

## B. Chunks

### Chunk B.1: Verify Clean Layout Clearing (No Duplicate "See All")

- **Goal:** Ensure `RecentList.refresh()` can be called repeatedly without duplicating header labels or the "See all" footer button.
- **Files Allowed:** `tests/test_recent_list.py`
- **Exact Steps:**
  1. Open `tests/test_recent_list.py`.
  2. Add test `test_recent_list_multiple_refreshes_no_duplicate_elements`:
     - Instantiate `RecentList`.
     - Seed 2 items in history.
     - Call `refresh()` 5 times consecutively.
     - Inspect child widgets: assert exactly 1 header label and 1 "See all" link button exist in the widget hierarchy.
  3. Run `pytest tests/test_recent_list.py`.
  4. Confirm that the local recursive `_clear_layout()` logic cleanly handles all nested layouts without leaks or duplicates.
- **Done When:** Test passes cleanly.
- **Commit Message:** `testB.1: verify clean layout clearing on repeated refresh`

---

### Chunk B.2: Auto-Refresh When Tab Becomes Visible

- **Goal:** Ensure `RecentList` automatically calls `refresh()` whenever its parent tab is shown, overcoming the limitation where a hidden widget does not receive child show events.
- **Files Allowed:** `app/ui/recent_list.py`, `tests/test_recent_list.py`
- **Exact Steps:**
  1. In `tests/test_recent_list.py`, write lifecycle test `test_recent_list_refreshes_on_parent_show`:
     - Create a parent `QWidget` and place `RecentList` inside it.
     - Seed 2 items in history.
     - Show parent: assert `RecentList` is visible with 2 rows.
     - Clear database.
     - Send `QShowEvent` to parent: assert `RecentList.isVisible()` is False and section is cleanly hidden.
  2. Run `pytest tests/test_recent_list.py` and confirm the test fails (parent show event does not refresh child).
  3. In `app/ui/recent_list.py`:
     - In `__init__`, install an event filter on parent:
       ```python
       parent = self.parent()
       if parent is not None:
           parent.installEventFilter(self)
       ```
     - Implement `eventFilter(self, watched, event)`:
       ```python
       def eventFilter(self, watched, event):
           if watched == self.parent() and event.type() == QEvent.Type.Show:
               self.refresh()
           return super().eventFilter(watched, event)
       ```
  4. Run `pytest tests/test_recent_list.py`.
- **Done When:** Lifecycle tests pass cleanly.
- **Commit Message:** `fixB.2: auto-refresh recent list on parent tab show event`

---

### Chunk B.3: End-to-End History Sync Test

- **Goal:** Verify cross-tab synchronization between History mutations (clear all and single delete) and the RecentList on Video and Audio tabs without an application restart.
- **Files Allowed:** `tests/test_recent_sync.py`
- **Important Qt Event Propagation Rule:** Never send a `QShowEvent` directly to a tab object (`VideoTab` or `AudioTab`). `RecentList` installs its event filter on its direct parent container widget (`self.parent()`), which is an internal layout container, NOT the outer tab itself. In Qt, delivering an event directly to the tab object does not reach filters installed on internal child containers. Therefore, tests must trigger show propagation by hiding and showing the tab (`tab.hide(); tab.show()`) so real Qt show propagation cascades to the container. If the test environment cannot show real top-level windows, send `QShowEvent` directly to `tab.recent_list.parent()` instead.
- **Exact Steps:**
  1. Create `tests/test_recent_sync.py`.
  2. Test `test_recent_sync_clear_all`:
     - Setup a temporary SQLite history database.
     - Seed 2 video items and 2 audio items.
     - Initialize `VideoTab` and `AudioTab`.
     - Call `history_service.clear_all(delete_files=False)`.
     - Trigger show propagation on `VideoTab` via `video_tab.hide(); video_tab.show()` (or send `QShowEvent` to `video_tab.recent_list.parent()`): assert `video_tab.recent_list.isVisible()` is False.
     - Trigger show propagation on `AudioTab` via `audio_tab.hide(); audio_tab.show()` (or send `QShowEvent` to `audio_tab.recent_list.parent()`): assert `audio_tab.recent_list.isVisible()` is False.
  3. Test `test_recent_sync_single_delete`:
     - Seed 2 video items (`row1`, `row2`).
     - Trigger show propagation on `VideoTab` (`video_tab.hide(); video_tab.show()` or send `QShowEvent` to `video_tab.recent_list.parent()`): assert 2 rows shown.
     - Call `history_service.delete(row1.id, delete_file=False)`. *(Note: strictly use `delete`, not `delete_item`)*.
     - Trigger show propagation on `VideoTab` (`video_tab.hide(); video_tab.show()` or send `QShowEvent` to `video_tab.recent_list.parent()`): assert only 1 row remains (`row2`).
  4. Test `test_recent_sync_consecutive_tab_switches`:
     - Seed 1 video item.
     - Trigger show propagation on `VideoTab` twice in a row (`video_tab.hide(); video_tab.show()` or two `QShowEvent`s to `video_tab.recent_list.parent()`).
     - Assert that switching to the tab twice causes exactly one extra refresh each time without creating duplicate header labels or duplicate links.
  5. Run `pytest tests/test_recent_sync.py`.
- **Done When:** All end-to-end sync tests pass 100%, and tests never send an event directly to a tab object.
- **Commit Message:** `testB.3: end-to-end history clear and delete sync across tabs`

---

## C. Verification Gate: Phase B

### Scope Proof
Run:
```bash
git diff --name-only 62c8db1
```
Must list ONLY:
- Files approved from Phase A (`video_tab.py`, `audio_tab.py`, tests)
- `app/ui/recent_list.py`
- `tests/test_recent_list.py`
- `tests/test_recent_sync.py`
- Plan / docs files (`gemini.md`, `docs/`, `plan/`)

### Test Command and Expected Output
```bash
pytest tests/test_recent_list.py tests/test_recent_sync.py
```
Expected output: **All phase tests pass (0 failures, 0 errors)**.

And full suite check:
```bash
pytest
```
Expected output: **Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline.**

### Real-PC Checks
1. **Initial Population:**
   - Download 1 video and 1 audio track.
   - Go to Video tab -> verify "Recently downloaded" contains the video item.
   - Go to Audio tab -> verify "Recently downloaded" contains the audio item.
2. **Clear All History:**
   - Go to History tab -> click "Clear all" -> choose "Keep files".
   - Switch to Video tab -> verify "Recently downloaded" section is completely hidden.
   - Switch to Audio tab -> verify "Recently downloaded" section is completely hidden.
3. **Single Item Deletion:**
   - Download a new video. Verify it appears on Video tab.
   - Go to History tab -> click the trash icon on that item to delete it.
   - Switch back to Video tab -> verify "Recently downloaded" section is completely hidden.
4. **App Restart Not Needed:**
   - Verify all the above happens dynamically without restarting the application.

### Stop-and-Ask Triggers Specific to Phase B
- If fixing history sync appears to require editing `app/core/history_service.py` or `app/core/history_db.py`, STOP and ask the owner.
- If a test fails after two attempts, STOP and ask the owner.
- At the verification gate, report results and wait for "approved".

---

## D. Evidence Template for docs/verification/phase_B.md

```markdown
# Phase B Verification Evidence

## Scope Proof
Command: `git diff --name-only 62c8db1`
Output:
[Paste terminal output here]

## Pytest Output
Command: `pytest tests/test_recent_list.py tests/test_recent_sync.py`
Output:
[Paste terminal output here]

## Real-PC Manual Checks
| Check # | Check Name | Result | Notes |
|---|---|---|---|
| 1 | Initial Population | PASS / FAIL | |
| 2 | Clear All History | PASS / FAIL | |
| 3 | Single Item Deletion | PASS / FAIL | |
| 4 | No Restart Needed | PASS / FAIL | |

## Captured Assets
- Screenshot: `screenshot_phase_b_sync.png`

## Decision
- Status: PASS / FAIL
- Reason: Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline; zero protected files modified, real-PC sync verified.
```

---

## E. "After This Phase" Message

### Report to the Owner
When all Phase B chunks are complete and the verification gate has passed:
1. Send a concise report summarizing:
   - Automated test results (number of tests passed in `test_recent_list.py` and `test_recent_sync.py`).
   - Scope verification output confirming zero protected files touched.
   - Real-PC checks confirmation.
2. Ask for explicit approval to proceed to Phase C.

### Exactly What Words to Wait For
Wait for the owner to reply with:
> **approved**

**DO NOT TOUCH ANY CODE IN PHASE C UNTIL THE OWNER REPLIES "approved".**

### Commit Command for the Gate
```bash
git commit --allow-empty -m "gate: phase B verified and approved"
```
*(Or commit `docs/verification/phase_B.md` if recorded on disk).*
