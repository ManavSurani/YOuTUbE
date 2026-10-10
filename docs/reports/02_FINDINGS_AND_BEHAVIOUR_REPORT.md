# Plan 2 Detailed Report: Codebase Findings & Target Behavior Architecture

**Project:** YOuTUbE Desktop Application  
**Milestone:** Multi-Lane Parallel Queue & UI State Hardening  
**Plan Reference:** `plan/02_FINDINGS_AND_BEHAVIOUR.md`  
**Status:** ALL FINDINGS RESOLVED & TARGET BEHAVIORS VERIFIED

---

## 1. Executive Summary

Plan 2 identified 11 critical defects across the UI state machine, cross-tab synchronization, queue scheduling, and process lifetime handling (findings `A-1` through `D-2`). It established the target behavioral contract (`R1` through `R6`) guaranteeing thread-safe, independent dual-lane operations with strict visual tab isolation.

---

## 2. Complete Findings vs. Resolution Matrix

| ID | Finding Description | Original Root Cause | Architectural Resolution | Resolution Status |
|---|---|---|---|---|
| **A-1** | Empty link box greyed out "Add to queue" during download | `queue_btn.setEnabled(has_new_link)` where `has_new_link = self._current_info is not None` | Decoupled queue button enablement from input presence. Button is clickable while a job of this tab's kind runs; disabled while fetching or offline, presenting a gentle 4-second inline hint if no link is present. | **RESOLVED (Phase A)** |
| **A-2** | Pasting link during download hid Cancel and displayed Download | `fetch_url()` unconditionally set `FETCHING`, and `_on_info_fetched()` set `READY`, hiding `cancel_btn` | Introduced `self._job_running()` sticky check in `set_state()`, keeping `cancel_btn` visible and `download_btn` hidden while active. | **RESOLVED (Phase A)** |
| **A-3** | Clearing link box reset state to IDLE, hiding Cancel button | `textChanged` triggered `set_state(TabState.IDLE)` on empty string regardless of active job | Protected state transitions: clearing text while a download runs remains in `DOWNLOADING` state with Cancel button preserved. | **RESOLVED (Phase A)** |
| **B-1** | `RecentList.refresh()` called only on tab init and job finish | Zero listener connections existed for HistoryTab changes | Installed an event filter on `QEvent.Type.Show` on the tab container to auto-refresh recently downloaded items on every tab switch. | **RESOLVED (Phase B)** |
| **B-2** | HistoryTab "Clear all" failed to notify Video and Audio tabs | `_on_clear_all` updated SQLite and internal table with zero broadcast | Handled via parent `Show` event filter polling the local SQLite database directly on tab activation, requiring zero complex bus coupling. | **RESOLVED (Phase B)** |
| **B-3** | Nested layouts created duplicate "See all" links on refresh | Plain widget iteration missed child layout items | Verified recursive `_clear_layout()` removes all layout items and child widgets cleanly before rebuild. | **RESOLVED (Phase B)** |
| **B-4** | Empty `RecentList` hid itself, breaking child `QShowEvent` | `setVisible(False)` prevented Qt from delivering `QShowEvent` to the child widget | Replaced child `showEvent` with parent-level event filter monitoring the visible parent container. | **RESOLVED (Phase B)** |
| **C-1** | Single shared `DownloadManager` serialized both video and audio | Global singleton held 1 active job, 1 worker, 1 queue file (`queue.json`) | Refactored into two dedicated singletons: `get_download_manager("video")` and `get_download_manager("audio")`. | **RESOLVED (Phase C)** |
| **C-2** | Temp file collision if same video ID downloaded as video & audio | `yt-dlp` used identical `%(title)s [%(id)s]` patterns in shared `TMP_DIR` | Enforced same-video-ID cross-lane deferral: identical video IDs run strictly serially, preventing concurrent file overwrites. | **RESOLVED (Phase C)** |
| **C-3** | App `closeEvent` only inspected default manager instance | Checked single manager active job before shutdown prompt | Checked active jobs across BOTH lane managers, displaying a single prompt and enforcing a unified 2.0s shutdown deadline. | **RESOLVED (Phase C)** |
| **C-4** | `DownloadManager.set_online()` never invoked by window handler | NetworkMonitor disconnected from queue manager instances | Wired `set_online(False)` / `set_online(True)` in `MainWindow` offline/online handlers to pause and resume both active lane workers. | **RESOLVED (Phase C)** |
| **D-1** | Shared queue widget displayed mixed jobs on both tabs | `QueueWidget` rendered all waiting jobs without filtering by kind | Refactored `QueueWidget` to accept `kind` parameter and strictly filter `job.kind != self.kind`, hiding if count is 0. | **RESOLVED (Phase D)** |
| **D-2** | `QueueRow` lacked individual progress bars for queued items | `QueueRow` showed only static text labels with no progress indicators | Implemented `ModernProgressBar(height=6)` on every `QueueRow` with state-specific indicators (Waiting: 0, Failed: red 0). | **RESOLVED (Phase D)** |

---

## 3. Behavioral Specification Verification

1. **R1: Add to Queue Sticky Behavior:**
   - Active download preserves Cancel button and hides Download button regardless of input box edits.
   - 4-second hint banner *"Paste a YouTube link first, then press Add to queue."* appears on empty queue click.

2. **R2: Visual Role Separation:**
   - Active job displays exclusively in top `ProgressCard`.
   - Queued and failed jobs display exclusively in bottom `QueueWidget` with 6px progress bars and action buttons.

3. **R3 & R6: Dual Parallel Lanes:**
   - Video and audio run concurrently on separate threads.
   - Same video ID deferral preserves strict FIFO order in its lane.

4. **R4 & R5: Visual Tab Isolation:**
   - Audio jobs never appear on Video tab; Video jobs never appear on Audio tab.
