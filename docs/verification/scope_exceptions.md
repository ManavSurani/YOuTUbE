# Scope Exceptions Log

This log records every approved file modification permitted during the autonomous fix loop under Section 1.1 of the prompt instructions.

| File | Phase | Reason | Approval Status |
|---|---|---|---|
| `app/core/paths.py` | Phase 1 (Chunk 1.1) | Add `job_tmp_dir(job_id)` returning `TMP_DIR / short_id` | Approved in prompt Section 1.1 & Section 5 Chunk 1.1 |
| `app/core/downloader.py` | Phase 1 (Chunk 1.1) | Update `build_video_cmd`, `build_audio_cmd`, `_cleanup_job_tmp` to use per-job temp folder and isolated cleanup | Approved in prompt Section 1.1 & Section 5 Chunk 1.1 |
| `app/core/paths.py` | Phase 1 (Chunk 1.2) | Update `purge_stale_tmp` to remove stale dirs and preserve queued jobs | Approved in prompt Section 1.1 & Section 5 Chunk 1.2 |
| `app/core/download_manager.py` | Phase 1 (Chunk 1.3) | Remove `_deferred_job_ids`, `deferred_job_ids()`, and same-video cross-lane deferral logic | Approved in prompt Section 1.1 & Section 5 Chunk 1.3 |
| `app/ui/queue_widget.py` | Phase 1 (Chunk 1.3) | Remove 'Waiting for the same video to finish' status handling and text | Approved in prompt Section 1.1 & Section 5 Chunk 1.3 |
| `app/core/download_manager.py` | Phase 2 (Chunk 2.1) | Add `_atomic_write_json` helper and replace direct `write_text` calls | Approved in prompt Section 1.1 & Section 5 Chunk 2.1 |
| `app/core/download_manager.py` | Phase 2 (Chunk 2.2) | Persist active job, restore to queue head on startup, enforce 3-restart limit, preserve across shutdown | Approved in prompt Section 1.1 & Section 5 Chunk 2.2 |
| `app/core/paths.py` | Phase 2 (Chunk 2.2) | Update `purge_stale_tmp` to inspect dict-format queue files (`active_job` + `waiting_queue`) | Approved in prompt Section 1.1 & Section 5 Chunk 2.2 |
| `app/core/download_manager.py` | Phase 3 (Chunk 3.1) | Flapping network debouncer, worker collision guard on resume, and active job zombie prevention | Approved in prompt Section 1.1 & Section 5 Chunk 3.1 |
| `app/core/downloader.py` | Phase 3 (Chunk 3.2) | Download stall watchdog detecting 60s silence, skipping merge, restarting via --continue with 3-retry limit | Approved in prompt Section 1.1 & Section 5 Chunk 3.2 |


