# Phase 4: Video and Audio Tabs and the Shared Queue

**Goal:** The new flow, a beautiful progress card, "Recently downloaded", and one shared queue.
**Fixes:** B8, B9, B15 (hard-coded text). **Depends on:** Phases 1 to 3.
**Files:** `ui/video_tab.py`, `ui/audio_tab.py`, `ui/kit/progress_card.py`, `core/download_manager.py` (new), `ui/recent_list.py` (new).

---

## Chunk 4.1: DownloadManager (shared queue)

Tasks:
1. `core/download_manager.py`: owns the queue, runs **one job at a time**, emits signals (`job_added`, `job_started`, `progress`, `stage`, `job_finished`, `job_failed`, `job_cancelled`, `queue_changed`).
2. Tabs no longer own workers or queues. They create `DownloadJob`s and send them to the manager.
3. Offline handling moves here: pause the active job when offline, resume when online.
4. Persistence: waiting jobs are saved to `queue.json` in app data and restored at startup (finished jobs are not).
5. Failed jobs keep the friendly reason and a Retry action. Cancelled jobs are removed after a short delay.
6. On `job_finished` the manager calls `HistoryService.save_from_job` (Phase 2). If saving fails, log and emit a visible warning.

Done when: queue tests run three jobs in order with only one worker alive at any time.

---

## Chunk 4.2: Tab state machine

Tasks:
1. Both tabs use the same states: `IDLE`, `FETCHING`, `READY`, `DOWNLOADING`, `DONE`, `OFFLINE`.
2. Button visibility by state:
   - IDLE / FETCHING: Download (disabled), dropdown disabled.
   - READY: Download enabled, dropdown enabled (real options only).
   - DOWNLOADING: Download hidden or locked; **Add to queue** and **Cancel** visible.
   - DONE: clears everything and returns to IDLE.
3. Clicking Download with no valid link shows an `InlineMessage` that auto-hides after 4 s and clears when switching tabs.
4. Going back online restores the **current** state, not "everything enabled".
5. Double-click protection: Download cannot start the same job twice.

Done when: a test drives every state transition and asserts widget visibility and enablement.

---

## Chunk 4.3: Fetch and options

Tasks:
1. Fetch builds `VideoInfo` once. Video dropdown: "Best available" plus real resolutions (4K, 2K, 1080p, ...) from the info JSON. Audio dropdown: Best original, MP3, M4A, Opus, WAV, FLAC.
2. Remove "Preferred video container" usage (always MKV).
3. Remove "Embed cover art" and "Embed metadata" checkboxes (always embedded, see Phase 1.5).
4. Keep the bitrate note but shorten it (one line, muted).
5. If the video is already in History: confirm dialog "Already downloaded. Download again?" with buttons in the new style.
6. Shared info between the tabs: paste once, both tabs show the same info card.

Done when: nothing in the UI references container or embed options, and the duplicate dialog works.

---

## Chunk 4.4: Progress card

Tasks:
1. `ProgressCard`: stage name, thick rounded red bar with soft glow and a moving shine, text line `63% • 12.4 MB/s • ETA 01:20 • 1.2 / 1.9 GB`.
2. Bar animates smoothly (150 ms) and never goes backwards. Indeterminate shimmer while "Getting video info" or "Merging" has no percent.
3. While downloading, show the small thumbnail and title above the card.
4. Success state: the bar fills, a tick appears, then the card collapses.
5. The message uses the real folder name instead of the hard-coded "Saved to Downloads".

Done when: a 4K download shows smooth movement and correct stage changes.

---

## Chunk 4.5: Recently downloaded

Tasks:
1. `RecentList` widget below the progress area on each tab: last 5 history rows of that tab's type, with thumbnail, title, quality, size, **Play** and **Open folder** icon buttons.
2. Updates instantly when a job finishes (slide-in animation). No search, no filters. A small "See all in History" link switches to the History tab.
3. Missing file shows a muted "File missing" state with no Play button.

Done when: finishing a video shows it on the Video tab only; finishing an MP3 shows it on the Audio tab only.

---

## Chunk 4.6: Queue list

Tasks:
1. Queue section appears only when it has items. Rows show thumbnail, title, type and quality, status (Waiting, Downloading with %, Done, Failed with reason), a remove icon for waiting items, Retry for failed items.
2. "Clear finished" ghost button. Header text: "Up next (2)" instead of "Queue (0 waiting)".
3. Row titles come from the job snapshot, never raw URLs.

Done when: adding 3 links shows 3 rows with correct titles and thumbnails, and they finish in order.

---

## Verification Gate: Phase 4

Evidence in `docs/verification/phase_4.md` (screenshots of each state).

### Automated
- [ ] State-machine tests for both tabs.
- [ ] DownloadManager tests (one-at-a-time, pause/resume offline, persistence, retry, cancel).
- [ ] Progress card tests (monotonic, shimmer, success).
- [ ] RecentList tests (filter by type, max 5, missing file).

### Manual
- [ ] Empty Download click: friendly error appears, disappears after about 4 s, and does not come back when switching tabs.
- [ ] Dropdown is disabled before fetch and unlocked after.
- [ ] During download only the progress card plus Add to queue and Cancel are visible.
- [ ] After completion the link clears, the progress hides, and the item shows under Recently downloaded.
- [ ] Add 3 queued items of mixed video and audio: one at a time, correct titles, correct History rows.
- [ ] Turn Wi-Fi off mid-download: popup once, controls lock, download resumes when back.
- [ ] Download the Hal Jordan video as video and MP3: both items appear with thumbnails and correct sizes.

### No-terminal check (mandatory)
- [ ] Full video, MP3, queue and offline-resume run on the console-less build: no window at any time.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 5.
