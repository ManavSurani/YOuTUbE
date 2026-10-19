# Phase 2 Plan: Atomic Queue Persistence and Active-Job Crash Recovery

## Goal & Background
In the baseline codebase, two major persistence and recovery vulnerabilities were identified during the audit:
1. **Non-atomic queue writes:** `_save_persisted_queue` called `Path.write_text()` directly. If the application crashed, the process was killed, or power was lost mid-write, the queue file (`queue_video.json` or `queue_audio.json`) could be truncated to 0 bytes or left with partial JSON, destroying user queues.
2. **Active-job loss on exit/crash:** When a job started downloading, it was popped from `_waiting_queue` and removed from disk persistence. If the process crashed, was killed via Task Manager, or Windows restarted, the active job was completely lost from persistence, leaving orphan `.part` files in `TMP_DIR` that were never resumed.

## Plan & Architecture

### Chunk 2.1: Atomic Write Helper
- Implement `_atomic_write_json(path: Path, data: Any, lock: threading.Lock) -> None`:
  - Uses `tempfile.NamedTemporaryFile` or unique temporary path `path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex[:8]}")` in the same directory (same filesystem ensures atomic `os.replace`).
  - Serializes JSON, flushes buffer (`f.flush()`), and commits to physical storage using `os.fsync(f.fileno())`.
  - Atomically renames to target `path` using `os.replace` under lane/global `threading.Lock`.
  - Cleans up temporary file in `finally` if replace fails.
- Replace all direct `write_text` calls in `_save_persisted_queue` and `migrate_legacy_queue_if_needed`.
- Tests:
  - Atomic write replaces file cleanly.
  - Concurrent writes from multiple threads never corrupt JSON.
  - Simulated write failure (e.g. disk/permission mock) preserves the original queue file intact.

### Chunk 2.2: Active-Job Persistence Across Crash, Kill, and Exit
- Data structure:
  - In `queue_video.json` and `queue_audio.json`, store a dict structure or array that preserves both the active job and waiting queue:
    `{"active_job": <dict or null>, "waiting_queue": [<dict>, ...]}`
    (with full backward-compatibility if an older flat list is found on disk).
  - Include `restart_count: int` (default 0) on `DownloadJob` / serialized item dict.
- Lifecycle:
  - When a job transitions from waiting to active (`_process_next`), it is recorded as `active_job` in `_save_persisted_queue()`.
  - When a job completes (`_on_worker_finished`), fails (`_on_worker_failed`), or is explicitly cancelled (`cancel_active` / `cancel_job`), `self._active_job = None` and the file is updated immediately.
  - On startup:
    - If `active_job` was persisted:
      - If `restart_count < 3`: increment `restart_count += 1`, insert `job` at index 0 of `_waiting_queue`. When `start_restored_jobs()` runs, it resumes downloading via `yt-dlp --continue`, picking up existing `.part` files in `job_tmp_dir(job.job_id)`.
      - If `restart_count >= 3`: do not attempt retry; move to `_failed_jobs` with plain-language message: `"Download interrupted repeatedly; cancelled."`.
    - If user explicitly clicks Cancel on an active job, `cancel_active()` clears `_active_job` and saves the queue file with `active_job: None` so it never re-appears on subsequent launches.
- Tests:
  - Kill worker process tree -> restart app -> active job restored at head of queue and resumes.
  - Restart 3 times consecutively -> moves to failed jobs, not waiting.
  - User clicks Cancel -> quit app -> restart app -> job does not return.

### Chunk 2.3: Phase 2 Verification & Safety Checks
- Full unit test coverage for queue serialization, atomic writes, concurrent writes, and crash recovery.
- Verification that scope checker `python tools/check_scope.py --baseline cdfed4e --final` passes cleanly.
- Full pytest suite verification (`python -m pytest -q -rf -p no:cacheprovider`).
- Update requirements matrix rows S1 and S2 to PASS.
