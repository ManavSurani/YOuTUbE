# YOuTUbE: Findings and Target Behaviour Specification

This document details the exact code findings (A-1 through D-2) based on inspection of the local codebase at baseline `62c8db1`, along with the definitive target behaviour specifications (R1 through R6, History Sync, and Offline/Close Handling).

---

## 1. Findings Table (A-1 through D-2)

Every row below was confirmed by direct inspection of the local repository:

| ID | Finding | Evidence & Local File/Line | Local Code Status | Impact |
|---|---|---|---|---|
| **A-1** | Empty link box greys out "Add to queue" while downloading | `video_tab.py:344`<br>`audio_tab.py:255` | **CONFIRMED** (`queue_btn.setEnabled(has_new_link)` where `has_new_link = self._current_info is not None`) | While a download is actively running, user cannot click "Add to queue" until they paste and fetch a new link. The button looks dead/broken. |
| **A-2** | Pasting link during download breaks buttons (hides Cancel, shows Download) | `video_tab.py:299-328, 419, 448-452`<br>`audio_tab.py:207-238, 329, 355-358` | **CONFIRMED** (`fetch_url()` unconditionally sets `FETCHING`; `_on_info_fetched()` sets `READY`, replacing Cancel with Download) | Download keeps running, but the tab completely loses the Cancel button, replacing it with the Download button. |
| **A-3** | Clearing link box sets IDLE and hides Cancel during download | `video_tab.py:408`<br>`audio_tab.py:318` | **CONFIRMED** (Non-DOWNLOADING state triggers `set_state(TabState.IDLE)` on empty text) | If user clears the text box while a download is running, Cancel disappears. |
| **B-1** | `RecentList.refresh()` called only on tab init and job finish | `video_tab.py:514`<br>`audio_tab.py:411` | **CONFIRMED** (Zero callers exist when History is cleared or items are deleted) | Clearing history in the History tab leaves stale items in "Recently downloaded" on Video and Audio tabs until restart. |
| **B-2** | `_on_clear_all` reloads only HistoryTab list; no signals sent | `history_tab.py:782-800` | **CONFIRMED** (HistoryTab reloads internally without notifying other tabs) | No cross-tab signal or broadcast exists for history mutations. |
| **B-3** | `refresh()` removes only plain widgets, leaving nested layout duplicate links | `recent_list.py:135-151` | **ALREADY IMPLEMENTED** (Local code already has recursive `_clear_layout()` and passing test `test_recent_list_refresh_no_duplicate_see_all`) | Verified fixed in local baseline, but requires regression testing. |
| **B-4** | Empty `RecentList` hides itself, preventing child `QShowEvent` | `recent_list.py:154-156` | **CONFIRMED** (Child `setVisible(False)` stops Qt show events; parent event filter is required) | A hidden widget never receives `QShowEvent`, so it cannot auto-refresh unless listening to its parent. |
| **C-1** | Single shared `DownloadManager` singleton forces serial queue for both types | `download_manager.py:22-44, 317-322` | **CONFIRMED** (One `_active_job`, one `_worker`, one `_waiting_queue`, one `queue.json`) | Audio downloads cannot run concurrently with video downloads; they block each other in a single serial queue. |
| **C-2** | Temp file collision if same video ID runs as video and audio | `downloader.py:127, 135, 170, 177` | **CONFIRMED** (`yt-dlp` writes `.part` files using `%(title)s [%(id)s]...`) | Concurrent video and audio jobs with identical `video_id` write to the same stream file in `TMP_DIR`, corrupting output. |
| **C-3** | App close handler only checks single manager instance | `main_window.py:399-405` | **CONFIRMED** (`closeEvent` checks `manager.active_job` on default instance only) | If audio lane has an active job, window could close without prompt or orphan worker process. |
| **C-4** | `DownloadManager.set_online()` is not called by `main_window.py` | `main_window.py:369-382` | **CONFIRMED** (Offline handler calls header and tabs, but neither calls `manager.set_online()`) | Network drop does not propagate to the download manager instance. |
| **D-1** | Shared queue widget displays jobs of both types on both tabs | `queue_widget.py:95-98, 120-124` | **CONFIRMED** (`QueueWidget` connects to shared manager and renders all jobs regardless of kind) | Audio downloads appear on the Video tab; Video downloads appear on the Audio tab. |
| **D-2** | `QueueRow` lacks individual progress bars for queued items | `queue_widget.py:24-83` | **CONFIRMED** (`QueueRow` displays static labels "Waiting" or "Failed", no progress bars) | Queued cards do not visually show progress bars, giving an incomplete appearance. |

---

## 2. Definitive Target Behaviour Specification

### R1: Add to Queue While Downloading & Sticky Look
- **Sticky Look:** While a download of this tab's kind is running:
  - `Cancel` button remains strictly visible and enabled.
  - `Download` button remains strictly hidden.
  - `Add to queue` button remains strictly visible and enabled.
  - The live `ProgressCard` remains visible showing download progress.
- **Empty URL Guard:** Clicking `Add to queue` with an empty link box or without fetched info displays a subtle 4-second inline message via `InlineMessage`:
  - Text: *"Paste a YouTube link first, then press Add to queue."*
  - Zero disruption to the running download.
- **Background Enqueue:** Clicking `Add to queue` with a fetched link:
  - Thumbnail is safely cached to disk (`save_thumbnail`).
  - Job is placed into that lane's waiting queue in the background.
  - Link input and metadata card are cleared ready for the next link.
  - The tab stays in its downloading look with Cancel visible.
- **Completion / Cancellation Restoration:**
  - When the running job finishes, normal state is restored.
  - `cancel_download()` restores `TabState.READY` if a link is fetched, otherwise `TabState.IDLE`.

### R2: Per-Item Queue Progress Bars & Visual Roles
- **Running Item:** Handled exclusively by the existing `ProgressCard` on the tab with live progress bar, % indicator, download speed, ETA, and size. The tab's `Cancel` button is the sole Cancel control for the running item.
- **Waiting Items:** Handled by `QueueWidget` and `QueueRow`.
  - Each waiting item has its own compact card with thumbnail, title, quality badge, a 6px progress bar (value 0, empty groove), status `"Waiting"`, and a `Remove` button.
  - If a waiting item is deferred due to identical `video_id`, its status displays: `"Waiting for the same video to finish"`.
- **Failed Items:** Handled by `QueueRow`.
  - Compact card with thumbnail, title, a 6px progress bar (value 0, red indicator), status `"Failed: <plain reason>"`, `Retry` button, and `Remove` button.

### R3 & R6: Dual Parallel Lanes (1 Video + 1 Audio Simultaneously)
- **Lane Concurrency:**
  - **Video Lane:** Manages video jobs. Executes strictly ONE video at a time in FIFO order. Next video starts only when the previous video finishes, fails, or is cancelled.
  - **Audio Lane:** Manages audio jobs. Executes strictly ONE audio at a time in FIFO order. Next audio starts only when the previous audio finishes, fails, or is cancelled.
  - **Parallelism:** One video and one audio download run simultaneously. An audio download never waits for a video download, and a video download never waits for an audio download.
- **Same Video ID Deferral Rule:**
  - If a video job and an audio job share the exact same `video_id`, the second job that arrives is marked **deferred** in its lane as long as the other job is running.
  - **Strict FIFO Preservation:** A deferred job **blocks** later jobs in its own lane. Later jobs in that lane never bypass a deferred job to jump ahead.
  - As soon as the first job finishes, fails, or is cancelled, the deferred job wakes up immediately and begins downloading.

### R4 & R5: Strict Visual Tab Isolation
- **Video Tab:** Displays ONLY video jobs (running video in `ProgressCard`, waiting/failed video jobs in `QueueWidget`). Audio jobs NEVER appear anywhere on the Video tab.
- **Audio Tab:** Displays ONLY audio jobs (running audio in `ProgressCard`, waiting/failed audio jobs in `QueueWidget`). Video jobs NEVER appear anywhere on the Audio tab.

### History Synchronization Across Tabs (Phase B)
- **Tab Switching Detection:** `RecentList` monitors its parent tab via an event filter on `QEvent.Type.Show`.
- **Clear All:** When the user clicks "Clear all" in the History tab (with or without deleting files from disk), switching to the Video or Audio tab immediately hides the "Recently downloaded" section.
- **Single Item Deletion:** When the user deletes an individual history row, switching to the Video or Audio tab immediately removes that row from "Recently downloaded".
- **Zero Restart Requirement:** Full synchronization occurs in-memory and via SQLite without restarting the application.

### Network Monitoring & Application Shutdown (Phase C)
- **Offline Pause:** When network drops, `main_window.py` calls `.set_online(False)` on both lane managers. Both active downloads cleanly pause and display "Waiting for internet…", preserving `.part` files.
- **Online Resume:** When network reconnects, `main_window.py` calls `.set_online(True)` on both lane managers. Both active downloads resume.
- **Safe Close (`closeEvent`):**
  - When closing the application, if either the video lane or the audio lane has an active job, a confirmation prompt is displayed once.
  - On confirmation, `shutdown()` is called on both managers, stopping active workers within 2 seconds without starting pending waiting jobs, and preserving persisted queues.
