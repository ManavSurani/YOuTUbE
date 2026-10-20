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
| `app/core/downloader.py` | Phase 4 (Chunk 4.1) | Dynamic detection of combined single stream formats, uncap from 95%, and upgrade audio estimate to 17000 B/s | Approved in prompt Section 1.1 & Section 5 Chunk 4.1 |
| `app/core/downloader.py` | Phase 5 (Chunk 5.2) | Speed optimization: add `--concurrent-fragments 4` and `--http-chunk-size 10M` to `build_video_cmd` and `build_audio_cmd` | Approved in prompt Section 1.1 & Section 5 Phase 5 |
| `app/core/errors.py` | Phase 6 (Chunk 6.2) | Friendly plain-language error mapping for 14 audit error samples, removing mention of non-existent copy button | Approved in prompt Section 1.1 & Section 5 Phase 6 |
| `app/core/tool_manager.py` | Phase 8 (Chunk 8.1) | Fail-closed checksum verification with 3 retries (1s, 2s, 4s backoff) | Approved in prompt Section 1.1 & Section 5 Phase 8 Chunk 8.1 |
| `app/core/thumbnails.py` | Phase 8 (Chunk 8.3) | Bound thumbnail downloads to at most 5 MB | Approved in prompt Section 1.1 & Section 5 Phase 8 Chunk 8.3 |




| pp/core/download_manager.py | Completion Loop Phase 1 | Active-job restart limit set to 2 with D1 failure message | approved by the owner in the autonomous completion prompt |
| `app/ui/main_window.py` | Completion Loop Phase 2 | Update exit confirmation dialog text to: "A download is running. Quit now? It will continue the next time you open the app." | Approved in prompt Section 2.1 & Section 5 Phase 2 |
