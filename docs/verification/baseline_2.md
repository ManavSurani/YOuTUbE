# Baseline 2: Autonomous Completion Loop

- **Date:** 2026-10-20
- **START Commit:** `819db71ddabab6394181ef6f4e14b8b936b4df58` (`819db71`)
- **Git Status at Start:** Clean (0 uncommitted modifications, 0 untracked files).
- **Test Suite Results at START:**
  - Total tests collected: 476
  - Tests passing: 475
  - Tests failing: 1 (`tests/test_check_scope.py::test_scope_checker_final`)
  - Execution time: 56.44 seconds
  - Pre-existing failure details: `test_scope_checker_final` invokes `tools/check_scope.py --baseline 62c8db1 --final`, which fails because permitted Section 1.1 files (`app/core/errors.py`, `app/core/thumbnails.py`) were modified during previous loop hardening.

---

## Code Inspection & Differences from Prompt Decisions

### Phase 1: S2 Active-Job Restart Limit
- **Decision D1:** An interrupted job is restored at most 2 times. The 3rd restore sends it to the failed list with the message `"The app closed several times while this download was running. Press Retry."`
- **Current Code (`app/core/download_manager.py:534`):**
  ```python
  restart_count = int(active_dict.get("restart_count", 0))
  if restart_count < 3:
      self._restart_counts[active_job.job_id] = restart_count + 1
      self._waiting_queue.append(active_job)
  else:
      reason = "Download interrupted repeatedly; cancelled"
      self._failed_jobs[active_job.job_id] = (active_job, reason)
  ```
- **Difference:** The current code allows 3 restarts (`restart_count < 3` allows restarts 0, 1, 2) and sends to failed at restart 4; the failure message is `"Download interrupted repeatedly; cancelled"` instead of `"The app closed several times while this download was running. Press Retry."`.

### Phase 2: S2 Closing Dialog Text
- **Decision D3:** Quitting the app during a download keeps the job and resumes it next start. Dialog text must say: `"A download is running. Quit now? It will continue the next time you open the app."`.
- **Current Code (`app/ui/main_window.py:431`):**
  ```python
  msg_box.setText("A download is running. Quit and cancel it?")
  ```
- **Difference:** The dialog text currently says `"A download is running. Quit and cancel it?"`, which falsely states the download is cancelled.

### Phase 3: S1 Corrupt Queue File Handling
- **Decision D5:** Corrupt or empty lane queue file: rename it to `<name>.corrupt` (if that name exists, add a timestamp), log it, start with an empty queue, never raise. A single bad entry inside an otherwise valid list is skipped and logged, and good entries still load.
- **Current Code (`app/core/download_manager.py:516`):**
  Only `_migrate_legacy_queue()` (lines 591, 597, 621) renames `queue.json` to `queue.json.corrupt`. Modern `_load_persisted_queue()` catches JSON decode errors, logs at debug level, and starts with an empty queue, but does NOT rename `queue_video.json` or `queue_audio.json` to `.corrupt`.
- **Difference:** Missing `.corrupt` rename logic for modern lane queue files in `_load_persisted_queue()`.

### Phase 4: S3 Force Stop at ~3 Seconds on Resume
- **Decision D4:** Resume: poll every 100 ms; at attempt 30 (about 3 s) force-stop the old worker's process tree; at attempt 100 (about 10 s) fail the job with `"The download could not be resumed. Press Retry."`.
- **Current Code (`app/core/download_manager.py:269`):**
  ```python
  self._resume_attempts += 1
  if self._resume_attempts <= 20:
      QTimer.singleShot(500, self._resume_active_job)
  else:
      self._on_worker_failed(job, "Download stalled and could not resume.")
  ```
- **Difference:** Poll interval is 500 ms (20 attempts = 10s); there is no intermediate force-stop step at attempt 30 (about 3s); failure message is `"Download stalled and could not resume."` instead of `"The download could not be resumed. Press Retry."`.

### Phase 5: S4 Watchdog Default Timeout
- **Decision D2:** Stall watchdog default: 90 seconds without a progress line, never during merging/converting, at most 3 restarts per job.
- **Current Code (`app/core/downloader.py:408, 420`):**
  ```python
  stall_timeout_seconds: float = 60.0,
  self.stall_timeout_seconds = max(0.05, float(stall_timeout_seconds or 60.0))
  ```
- **Difference:** Default timeout is 60.0 seconds instead of 90.0 seconds.

### Phase 6: A1 Automated Replay Test
- **Requirement A1:** Create `tests/fixtures/progress_dual.txt` and replay tests asserting:
  - Percent never decreases over the whole sequence;
  - Percent rises during the audio stage (never frozen for more than 3 consecutive audio lines);
  - Reported total vs true final size is within 5% at 5%, 50%, and 95%;
  - Single combined format reaches at least 99% before merge;
  - Resumed tracker with finished_bytes continues without dropping;
  - Whole-job ETA.
- **Difference:** Previously only partial synthetic progress tests and manual scratch runs existed; no automated fixture-based 5% tolerance test existed in `tests/`.

### Phase 7: C1 Speed Decision Document
- **Decision D6:** Document speed decision in `docs/verification/speed_decision.md` with alternating pairs and medians. Code flags (`-N 4`, `--http-chunk-size 10M`) match the decision.
- **Difference:** `docs/verification/speed_decision.md` does not exist as a standalone document.
