# Scope Exceptions Log

This log records every approved file modification permitted during the autonomous fix loop under Section 1.1 of the prompt instructions.

| File | Phase | Reason | Approval Status |
|---|---|---|---|
| `app/core/paths.py` | Phase 1 (Chunk 1.1) | Add `job_tmp_dir(job_id)` returning `TMP_DIR / short_id` | Approved in prompt Section 1.1 & Section 5 Chunk 1.1 |
| `app/core/downloader.py` | Phase 1 (Chunk 1.1) | Update `build_video_cmd`, `build_audio_cmd`, `_cleanup_job_tmp` to use per-job temp folder and isolated cleanup | Approved in prompt Section 1.1 & Section 5 Chunk 1.1 |
