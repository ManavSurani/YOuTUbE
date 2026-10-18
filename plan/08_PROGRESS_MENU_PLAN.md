# 08 — Progress Numbers, Checkbox and Menu Fix Plan (Approved)

## 0. Base Commit & Scope Exceptions (R9)

- **Base:** The 8 uncommitted modified files from previous A.1 to B.1 work remain untouched until owner sends `"checks passed"`. Once committed by staging strictly those 8 files by name, that **new commit hash** will serve as the baseline for the Final Gate (Chunk 7).
- **Files for Base Commit (staged only by name, no `git add .` or `-A`):**
  1. `app/core/download_manager.py`
  2. `app/core/downloader.py`
  3. `app/ui/audio_tab.py`
  4. `app/ui/video_tab.py`
  5. `tests/test_download_manager.py`
  6. `tests/test_downloader.py`
  7. `tests/test_tab_flow.py`
  8. `tests/test_tab_looks.py`
  *(Note: `plan/` and `docs/` files stay strictly out of this base commit).*
- **Commit `bdd80ac` File List:**
  1. `app/core/downloader.py`
  2. `app/ui/audio_tab.py`
  3. `app/ui/kit/progress_card.py`
  4. `app/ui/video_tab.py`
  5. `tests/test_downloader.py`
  6. `tests/test_tab_flow.py`
  7. `tests/test_tab_looks.py`
  8. `tests/test_ui_kit.py`
  9. `tools/check_scope.py`
- **Recorded Scope Exceptions (pending owner approval):**
  - `app/core/downloader.py`: A.1 quality template and Chunk 2 progress lines (whole-job byte math).
  - `app/core/download_manager.py`: A.2/A.2b retry overwrite tracking, and passing `duration_seconds` to `DownloadWorker`.
  - `tools/check_scope.py`: Scope check whitelist adjustments in `bdd80ac`.
- **Pre-existing Verification Documents (Verified Existing on Disk):**
  - [`docs/verification/test_comparison.md`](file:///c:/Vs/YOuTUbE/docs/verification/test_comparison.md) (exists)
  - [`docs/verification/scope_exceptions.md`](file:///c:/Vs/YOuTUbE/docs/verification/scope_exceptions.md) (exists)

---

## 1. Overview and Problems

1. **P1 — Numbers under the progress bar vanish or are wrong:**
   - `ProgressCard.set_progress()` drops missing components (speed, ETA, sizes) in each individual update instead of retaining the last known good values.
   - `parse_line()` in `app/core/downloader.py` sets `total_bytes = 0` when `total == NA` and `estimate <= downloaded`, or when `estimate < 100,000`. This leads to `percent = 0.0`, freezing the bar while bytes continue to grow.
   - Streams with `NA` downloaded bytes cause sizes to disappear.
   - The progress bar previously utilized hardcoded weights (85% video, 10% audio, 5% post-processing) while the displayed text reflects individual stream bytes, creating a mismatch between the visual bar and the displayed MB (e.g. 216.7 MB / 513.6 MB = 42%, but bar showed 35%).
   - **Resolution:**
     - First (Chunk 2): `DownloadWorker` emits whole-job done and total bytes calculated from whole-job byte math (using ~13,000 B/s audio guess during video stream).
     - Second (Chunk 3): `ProgressCard` displays these directly, keeps last good values, and **does not** reset stored numbers on stage change.

2. **P2 — Clear download history dialog checkbox cut on the left:**
   - `AnimatedCheckBox.paintEvent()` draws an 18 px box at `x = 1.0` and its focus ring with `box_rect.adjusted(-2, -2, 2, 2)`, placing the left edge at `x = -1.0` (outside the widget boundary and clipped).
   - `sizeHint()` (`20 + (8 if text else 0) + text_w`) leaves no margin for the outer focus ring.
   - Used in `ClearAllDialog` (`app/ui/history_tab.py`) and in `SettingsDialog`.

3. **P3 — Right-click context menu does not match the dropdown:**
   - Link input fields in Video and Audio tabs, and the History search box (`search_input`), use standard OS context menu styling.
   - **Resolution:** Reuse existing `AnimatedLineEdit` from `app/ui/video_tab.py`, styled with `get_current_theme_tokens()` (dropdown's theme detection function), 8 px border-radius, 32 px items, `text_muted` verified, and 150 ms `windowOpacity` fade. Tested and proven: corner pixel alpha is 0 (transparent) and fade starts from 0.0. Use for Video, Audio, and History search box (`search_input`).

4. **P4 — Queue row generic failure ("Something went wrong. Copy the details and try again."):**
   - A 144p download failed with a generic fallback message from `app/core/errors.py`.
   - Investigation indicates yt-dlp failed with:
     `ERROR: unable to download video data: HTTP Error 403: Forbidden`
   - Reported as "likely, unproven"; no new message proposed until owner decides.

---

## 2. Log and Runtime Evidence (Step 1 Investigation)

### YTPROG Log Sample (Last 40 Lines from `%APPDATA%\YOuTUbE\logs\app.log`)
```text
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71155833|97370030|NA|2317487.9420334543|11|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71164025|97370030|NA|3395946.9421748985|7|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71180409|97370030|NA|5745155.822049622|4|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71213177|97370030|NA|9680271.166571265|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71278713|97370030|NA|12590850.990074327|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71409785|97370030|NA|11457919.15636181|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71671929|97370030|NA|11171772.832463745|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|72196217|97370030|NA|11333712.203925494|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|73244793|97370030|NA|11404826.218875991|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|75341945|97370030|NA|11547164.944092283|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|79536249|97370030|NA|11479972.459069975|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81364456|97370030|NA|11425477.19230436|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81365480|97370030|NA|1019697.8385565053|15|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81367528|97370030|NA|1542178.5622980252|10|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81371624|97370030|NA|2385714.257419457|6|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81379816|97370030|NA|4056192.7494805767|3|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81396200|97370030|NA|6600762.786971395|2|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81428968|97370030|NA|11005569.822175222|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81494504|97370030|NA|13536688.090135252|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81625576|97370030|NA|10987987.443867007|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81887720|97370030|NA|11089807.171400419|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|82412008|97370030|NA|11226420.485180492|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|83460584|97370030|NA|11466480.842779616|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|85557736|97370030|NA|11462345.088014515|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|89752040|97370030|NA|11503742.181211991|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91691144|97370030|NA|11471960.12295657|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91692168|97370030|NA|689954.5857028113|8|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91694216|97370030|NA|990917.6257786665|5|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91698312|97370030|NA|1743693.949193829|3|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91706504|97370030|NA|2851651.444759207|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91722888|97370030|NA|4943158.944718767|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91755656|97370030|NA|7693572.352800682|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91821192|97370030|NA|10743551.369718933|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91952264|97370030|NA|9711347.708131976|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|92214408|97370030|NA|11326519.145250272|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|92738696|97370030|NA|11166192.387062343|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|93787272|97370030|NA|11298231.661363967|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|95884424|97370030|NA|11374530.85080569|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|97370030|97370030|NA|11417610.752642773|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|finished|97370030|97370030|NA|10392636.424171438|NA|none|opus
```

### ERROR Log & Context Analysis (Problem P4)
- **Log lines:**
  `ERROR: unable to download video data: HTTP Error 403: Forbidden`
  `yt-dlp exited 1: [youtube] Extracting URL: https://www.youtube.com/watch?v=6F5RWSiSxcI`
- **Context Investigation:**
  - Video `6F5RWSiSxcI` was downloaded at 2160p (4K) successfully at `04:31:33` - `04:32:49`.
  - Exactly 5 seconds later at `04:32:49`, the queue started job `3c911825-1044-401b-938b-7a91e55e4988` for the **same video** at 144p (`format 394+251`).
  - At `04:32:54`, YouTube returned `HTTP Error 403: Forbidden` during video stream extraction.
  - **Repetition:** Appeared **once** in the log for this video.
  - **Start type:** Was a **first start** from the queue, not a retry.
  - **Diagnosis:** Likely, unproven: YouTube rate-limiting / player API token expiration during rapid sequential format extraction for the same video.
  - No new error message proposed until owner decides.

---

## 3. Plan Chunks (Approved Order)

### CHUNK 1 — Evidence (No Code)
- **Goal:** Record real log output, statistics table, and initial download lines into verification documentation.
- **Allowed files:** `docs/verification/*.md` only. No other `.md` files; nothing appended to `gemini.md`.
- **Steps:**
  1. Create `docs/verification/progress_log_evidence.md` with extracted lines, stats, and 403 context analysis.
- **Done when:** `docs/verification/progress_log_evidence.md` exists and contains complete evidence.
- **Commit message:** `fixPROG.1: record real progress log evidence`

---

### CHUNK 2 — Accurate Bar and Totals (Worker Side)
*(Done before card chunk so worker emits whole-job bytes first)*
- **Goal:** Compute whole-job byte-based progress across video and audio streams, replacing hardcoded 85/10/5 weights. Ensure bar strictly matches `overall_done / overall_total`.
- **Allowed files:** `app/core/downloader.py` (progress lines only), `app/core/download_manager.py` (pass `duration_seconds` to worker; R9 exception), `tests/test_downloader.py`.
- **Steps:**
  1. In `app/core/download_manager.py`:
     In `_start_worker()`, pass `duration_seconds=job.duration_seconds` to `DownloadWorker`.
  2. In `app/core/downloader.py`:
     - Accept `duration_seconds: int = 0` in `DownloadWorker.__init__`.
     - Track whole-job totals (standard signal `progress(float, str, str, int, int)` preserved; no "~" marker):
       - `finished_bytes` (sum of totals of finished streams).
       - `overall_done = finished_bytes + current_done`.
       - `overall_total = finished_bytes + current_total + remaining_estimate`.
       - While video stream is active, `remaining_estimate = int(duration_seconds * 13_000)` (~13 KB/s audio guess, e.g. ~97.4 MB for 2:09:16 video). Once audio stream's real total is known, `remaining_estimate = 0`.
       - If duration is unknown, use `current_total`.
     - `percent = min(99.9, (overall_done / overall_total) * 100.0)`. Post-processing/merging = 95..99, done = 100.
     - Eliminate hardcoded 0.85 / 0.10 weights.
     - On status `"finished"`, add stream total to `finished_bytes` and close stream.
     - Latch rule: only allow progress bar to move backwards if total changes by > 25%. Bar never exceeds 100%.
- **Tests first (in `tests/test_downloader.py`):**
  - Exact total stream; estimate > done; estimate <= done; NA downloaded.
  - First tiny fragment latching.
  - Video stream finished followed by audio stream start.
  - Bar percent strictly matches `overall_done / overall_total` within 1 point.
  - 42% byte case (216.7 / 513.6 MB) produces ~42% on bar, never 35%.
  - Real first lines test from Chunk 1 log evidence.
  - Audio total replacing audio guess test: total drop when real audio arrives keeps bar within 25% rule and never above 100%.
- **Expected failure:** Current 85/10 weights produce 35% instead of 42%.
- **Done when:** All tests pass; full suite passes.
- **Commit message:** `fixPROG.2: byte-based overall progress with accurate totals`

---

### CHUNK 3 — Sticky, Stable Numbers in the Card (Card Side)
- **Goal:** Prevent missing values from blanking numbers in `ProgressCard`. The card displays whole-job numbers emitted by the worker and **does NOT** reset numbers on a stage change.
- **Allowed files:** `app/ui/kit/progress_card.py`, `tests/test_ui_kit.py`.
- **Steps:**
  1. In `ProgressCard.__init__` and `bind_job()`:
     Initialize sticky state: `_last_done = 0`, `_last_total = 0`, `_last_speed = ""`.
  2. In `set_stage(stage_text)`:
     Update `stage_label.setText(stage_text)`. **Do NOT reset** `_last_done`, `_last_total`, or `_last_speed` on stage changes.
  3. In `set_progress()`:
     - Preserve existing guard: `if percent > 0 or self._max_percent == 0: self._max_percent = percent`.
     - Latch non-zero/non-empty inputs:
       - `if done_bytes > 0: self._last_done = done_bytes`
       - `if total_bytes > 0: self._last_total = total_bytes`
       - `if speed: self._last_speed = speed`
     - Compute `done = self._last_done`, `total = max(self._last_total, done)`.
     - Compute `size`:
       `f"{self._fmt_bytes(done)} / {self._fmt_bytes(total)}"` if total else (`self._fmt_bytes(done)` if done else `"calculating…"`)
     - Build fixed 3-slot layout: `[self._last_speed or "-- MB/s", size, f"ETA {eta}" if eta else "ETA --:--"]`
     - `stats_label.setText(" • ".join(slots))`.
- **Tests first (in `tests/test_ui_kit.py`):**
  - Speed, done, and total arrive, followed by an update with `done=0, total=0, speed=""` -> numbers stay sticky and visible.
  - `total` smaller than `done` displays as `done / done`.
  - Stage change from `"Downloading video"` to `"Downloading audio"` does **NOT** reset the stored numbers.
  - The three slots (`speed • size • ETA`) are always present (placeholders when unknown).
- **Expected failure:** Current `ProgressCard` drops slots when missing in a single update.
- **Done when:** Tests pass; full suite passes.
- **Commit message:** `fixPROG.3: keep last good speed and sizes in the progress card`

---

### CHUNK 4 — Checkbox Focus Ring Fix
- **Goal:** Prevent focus ring from clipping on the left edge and ensure `sizeHint()` reserves proper margin.
- **Allowed files:** `app/ui/kit/checkbox.py`, `tests/test_ui_kit.py`, `tests/test_tab_looks.py`.
- **Focus Ring Pen Color Verification (Condition 1):**
  - In `app/ui/kit/checkbox.py` (line 121), the focus ring is **hard-coded** as:
    `painter.setPen(QPen(QColor("#3EA6FF"), 1.5))`
  - It is **not** read from theme tokens.
  - In the light theme, `checkbox.py` currently draws the exact same `#3EA6FF` (blue) ring.
  - The tests will assert what the code really draws: `QColor("#3EA6FF")` in both dark and light themes.
- **Steps:**
  1. Define `RING = 3.0` constant in `app/ui/kit/checkbox.py`.
  2. In `paintEvent()`:
     - `box_rect = QRectF(RING, box_y, box_size, box_size)`.
     - Draw focus ring with `box_rect.adjusted(-2, -2, 2, 2)`. Left edge starts at `x = 3.0 - 2.0 = 1.0` (fully inside widget `x >= 0`).
     - Shift text and checkmark offsets accordingly.
  3. In `sizeHint()`:
     - Reserve `int(2 * RING) + 18 + (8 if self.text() else 0) + text_w`.
- **Tests first:**
  - Grab focused `AnimatedCheckBox` and assert pixels in columns 0..2 contain `QColor("#3EA6FF")` (in both dark and light themes) and no ring pixel is clipped at `x < 0`.
  - Verify `ClearAllDialog` opens unchecked with Cancel button focused.
  - Verify clicking label text toggles checkbox.
  - Verify Settings checkbox functions correctly.
- **Expected failure:** Current focus ring clips at `x < 0`.
- **Done when:** Visual focus ring is unclipped and all tests pass.
- **Commit message:** `fixPROG.4: show the full checkbox focus ring`

---

### CHUNK 5 — Styled Right-Click Menu
- **Goal:** Match right-click menus on URL link boxes (Video, Audio) and History search box (`search_input`) with dropdown styling and 150 ms fade.
- **Allowed files:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/history_tab.py`, `tests/test_ui_kit.py`, `tests/test_tab_looks.py`.
  *(No new `styled_menu.py` file needed — reusing existing `AnimatedLineEdit` from `app/ui/video_tab.py`).*
- **Raw Proof of QMenu Translucency & Fade (Condition 2, Measured on Shown Widget):**
  ```text
  Initial windowOpacity: 0.000
  Corner pixel (0,0): alpha=0, r=0, g=0, b=0 (100% transparent corner)
  Corner pixel (1,1): alpha=0, r=0, g=0, b=0 (100% transparent corner)
    0.2 ms: windowOpacity = 0.059
   16.4 ms: windowOpacity = 0.165
   32.5 ms: windowOpacity = 0.271
   48.3 ms: windowOpacity = 0.384
   64.0 ms: windowOpacity = 0.486
   79.8 ms: windowOpacity = 0.592
   95.6 ms: windowOpacity = 0.698
  111.2 ms: windowOpacity = 0.800
  127.2 ms: windowOpacity = 0.980
  143.0 ms: windowOpacity = 0.992
  162.7 ms: windowOpacity = 0.996
  178.3 ms: windowOpacity = 1.000 (Animation Complete)
  ```
- **Steps:**
  1. In `app/ui/video_tab.py`, enhance `AnimatedLineEdit.contextMenuEvent()`:
     - Detect theme tokens using dropdown's existing `get_current_theme_tokens()`.
     - Build menu stylesheet matching dropdown (8 px border-radius, 32 px item height, surface/border/text/surface_hover, `text_muted` verified in dark and light tokens).
     - Apply stylesheet, `FramelessWindowHint`, `NoDropShadowWindowHint`, `WA_TranslucentBackground`.
     - Keep `UI_FadeMenu` / `UI_AnimateMenu` suppression around `popup()`, 150 ms `OutCubic` `windowOpacity` animation, and `deleteLater()` on hide.
  2. Use `AnimatedLineEdit` for:
     - `video_tab.py`: `url_input` (already using it).
     - `audio_tab.py`: `url_input` (already using it).
     - `history_tab.py`: `self.search_input` (verified attribute name; replace `QLineEdit` with `from app.ui.video_tab import AnimatedLineEdit` — verified 0 circular imports).
- **Tests first:**
  - Verify menu stylesheet contains dropdown's 8 px border-radius, 32 px item height, and theme colors in both themes.
  - Verify menu contains standard actions (Cut, Copy, Paste, Delete, Select All, Undo, Redo).
  - Verify History search box (`search_input`) uses `AnimatedLineEdit` and right-click triggers styled menu.
  - Verify pasting text in all three inputs works as expected.
- **Expected failure:** History `search_input` currently uses unstyled native OS context menu.
- **Done when:** All three line edits show the styled 8 px rounded menu with smooth 150 ms fade.
- **Commit message:** `fixPROG.5: styled right-click menu matching the dropdown`

---

### CHUNK 6 — Failed-Row Reason (Report Only)
- **Goal:** Report root cause of the 144p HTTP 403 failure from Chunk 1 log evidence.
- **Allowed files:** None (investigation and reporting only).
- **Findings to Report:**
  - Error: `HTTP Error 403: Forbidden`.
  - Diagnosis: Likely, unproven: YouTube rate-limiting / player API token expiration during rapid sequential format extraction for the same video.
  - Occurrence: Appeared once for video `6F5RWSiSxcI`.
  - Start type: First start of queued format `394+251` (144p AV1) immediately following a successful 4K download of the same video.
  - No new message proposed until owner decides.

---

### CHUNK 7 — Final Gate
- **Baseline:** Compare against NEW commit hash (after user commits A.1–B.1 with `"checks passed"`).
- **Full test suite execution:**
  `python -m pytest -q -rf -p no:cacheprovider`
  Must pass cleanly with no new failures beyond documented baseline in [`docs/verification/test_comparison.md`](file:///c:/Vs/YOuTUbE/docs/verification/test_comparison.md).
- **Scope proof:**
  - `git diff --name-only <NEW_COMMIT_HASH> HEAD` lists only allowed files.
  - Diff against the 14 protected files prints nothing.
  - `git grep -n "print(" -- app` and `git grep -n "shell=True" -- app` return 0 hits.
- **Owner visual checks list:**
  1. Start a 1 GB+ download -> verify speed, downloaded / total, and ETA are continuously shown with no vanishing slots.
  2. Compare progress bar with MB -> bar percent matches `downloaded / total` within 1 point.
  3. Re-download a video -> bar starts near 0%, does not jump to 85%.
  4. Clear history dialog -> checkbox and focus ring are fully visible without clipping; box is unchecked and Cancel is focused.
  5. Settings dialog -> update checkbox looks crisp and toggles correctly.
  6. Right-click in Video link box, Audio link box, and History search -> styled 8 px rounded menu fades in; Cut, Copy, Paste, Select All work.
  7. Review ERROR log lines for the failed 144p row.

---

### CHUNK 8 — GitHub Sync (Only After "approved final")
- Verify clean status: `git status`.
- Verify sync: `git fetch origin ; git status -sb`.
- Security scan: `git grep -n -i -E "(api[_-]?key|secret|token|password)" -- . ":!tests" ":!gemini.md"`.
- Push branch: `git push origin fix/ui-pass`.
- Verify hashes: `git rev-parse HEAD origin/fix/ui-pass`.
- Merge request to owner: `Merge into main? (approved merge)`.
- On approval:
  - `git checkout main ; git pull --ff-only origin main ; git merge --ff-only fix/ui-pass`
  - `python -m pytest -q -rf -p no:cacheprovider`
  - `git push origin main ; git rev-parse HEAD origin/main ; git checkout fix/ui-pass`

---

## 4. Questions and Recorded Answers

### Q1: May `downloader.py` be edited, progress lines only (percent/total maths), and the earlier change in `bdd80ac` be accepted as a recorded exception?
- **Answer:** **Yes.** Progress lines only. Recorded in `docs/verification/scope_exceptions.md` as pending owner approval.

### Q2: Does the worker know the video duration (needed for the audio-size estimate)?
- **Answer:** `DownloadJob` in `app/core/jobs.py` already has `duration_seconds: int`. In Chunk 2 (Worker), `_start_worker()` in `app/core/download_manager.py` will pass `duration_seconds=job.duration_seconds` to `DownloadWorker.__init__`. Recorded in `docs/verification/scope_exceptions.md` as pending owner approval. `jobs.py` stays untouched.

### Q3: Does Chunk A.4 (Best-vs-explicit label collision and wrong label in history) go before or after this task?
- **Answer:** **After this task, as its own separate commit.**
