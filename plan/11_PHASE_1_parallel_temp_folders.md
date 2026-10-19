# Phase 1 Plan: Per-Job Temp Folders and Parallel Same-Video Downloads

**Goal:** Remove the shared temp folder to eliminate file collisions and the cleanup deletion bug, and allow video and audio downloads of the same YouTube link to run simultaneously in parallel.

**Why:** Currently, all jobs dump temporary files into root `TMP_DIR`. In `downloader._cleanup_job_tmp()`, files are deleted by `video_id` and by suffix (`.part`, `.ytdl`), which wiped out concurrent jobs downloading the same video or running in the other lane. To prevent this, cross-lane deferral was artificially introduced. Isolating each job into its own temp folder (`job_tmp_dir(job_id)`) makes downloads completely independent and eliminates the need for deferral.

**Allowed Files:**
- `app/core/paths.py`
- `app/core/downloader.py`
- `app/core/download_manager.py`
- `app/ui/queue_widget.py`
- `tests/`
- `docs/`
- `plan/`

## Chunks

### Chunk 1.1: Paths, Builders, and Cleanup
- **Steps:**
  1. Add `job_tmp_dir(job_id: str) -> Path` in `app/core/paths.py`. Shortens `job_id.replace('-', '')[:12]` and returns `TMP_DIR / short`.
  2. In `app/core/downloader.py`, update `build_video_cmd` and `build_audio_cmd` to use `job_tmp_dir(job_id)` instead of bare `TMP_DIR`.
  3. Update `DownloadWorker._cleanup_job_tmp()` to remove `job_tmp_dir(self.job_id)` with a retry on error, and delete `(TMP_DIR / f"{self.job_id}.path")`. Never scan root `TMP_DIR`.
  4. Ensure success, user cancel, and failure cleanup delete the job's temp folder, while offline pause and app shutdown preserve it.
- **Test First:**
  - `tests/test_downloader.py`: test `job_tmp_dir`, test builders contain `-P temp:<job_dir>`, test `_cleanup_job_tmp` only removes the specific job folder and never scans root `TMP_DIR` (assert root `iterdir` raises if called).
- **Expected Failure:** `AttributeError: cannot import 'job_tmp_dir'` / assertion failure on command strings.
- **Done When:** Tests pass, commands use per-job temp folders, cleanup is isolated.
- **Commit:** `fixLOOP.1.1: per-job temp folders and isolated cleanup`

### Chunk 1.2: Stale Temp Folder Purge
- **Steps:**
  1. In `app/core/paths.py:purge_stale_tmp`, update logic to delete subdirectories in `TMP_DIR` older than 7 days, unless the directory name corresponds to a job ID currently in `queue_video.json` or `queue_audio.json`.
- **Test First:**
  - `tests/test_paths.py` (or `test_downloader.py`): verify that stale unreferenced job folders are removed, while queued job folders and fresh folders are kept.
- **Expected Failure:** Purge does not remove directories or removes queued job folders.
- **Done When:** Purge preserves queued job folders and deletes expired ones.
- **Commit:** `fixLOOP.1.2: purge stale job temp folders preserving queued jobs`

### Chunk 1.3: Remove Cross-Lane Deferral and Update Queue Widget
- **Steps:**
  1. In `app/core/download_manager.py`, remove `_deferred_job_ids`, `deferred_job_ids()`, and the same-video check in `_process_next()`. Clean up unused wake-ups while keeping essential lane wake-ups.
  2. In `app/ui/queue_widget.py`, remove the `"Waiting for the same video to finish"` branch and status text.
  3. Replace old deferral tests with parallel execution tests (same video ID runs simultaneously in both lanes; independent temp dirs; independent cleanup; two history rows).
  4. Record all replaced tests in `docs/verification/test_changes.md`.
- **Test First:**
  - Tests in `tests/test_download_lanes.py` asserting simultaneous video + audio downloads for identical `video_id`.
- **Expected Failure:** Old tests fail due to absence of deferral, new tests fail before code removal.
- **Done When:** All unit tests pass, zero deferral remains.
- **Commit:** `fixLOOP.1.3: remove same-video deferral and enable parallel lanes`

## Verification Checks
1. Run full test suite: `python -m pytest -q -rf -p no:cacheprovider` (must pass 100%).
2. Scope check: only allowed files touched.
3. Grep check: no `print(`, no `shell=True`.
4. Headless scratch experiment: download "Me at the zoo" simultaneously as video and audio via `DownloadWorker`. Check `(Get-Process yt-dlp).Count` reaches 2. Verify both files exist. In a second run, cancel one halfway and verify the other completes.
5. Record sequential vs parallel benchmark timing.
