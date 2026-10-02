# Phase 2 Verification: Data and History Integrity

**Date:** 2026-10-02  
**Result:** ✅ PASS — all gates cleared

---

## Automated Gate

| Check | Result |
|---|---|
| `test_download_job_snapshot_immutability` — Immutable snapshot against UI race conditions | ✅ PASS |
| `test_download_job_rejects_empty_or_url_title` — Disallows `title = url` or blank title | ✅ PASS |
| `test_thumbnail_saving_and_pixmap` — Rounded thumbnail rendering | ✅ PASS |
| `test_fallback_pixmap_no_letters` — Neutral play/music fallback; no "V" or "A" letter badges | ✅ PASS |
| `test_thumbnail_shared_reference_retention` — Shared `video_id` ref-count retention | ✅ PASS |
| `test_init_db_and_version` — `PRAGMA user_version = 1` | ✅ PASS |
| `test_migration_from_v0_schema` — Upgrades older schemas and backfills `video_id` | ✅ PASS |
| `test_add_item_validation` — Fails loudly on empty `file_path` or `title == url` | ✅ PASS |
| `test_find_duplicate_and_update` — Duplicate download updates path and size, no duplicate rows | ✅ PASS |
| `test_daily_backup` — Daily database backup in `history/backups/`, 7-day retention | ✅ PASS |
| `test_save_from_job_and_duplicate` — Snapshot saving and duplicate update | ✅ PASS |
| `test_save_from_job_missing_file_raises` — Rejects missing file paths | ✅ PASS |
| `test_delete_options_and_locked_file` — Locked file keeps row and returns clear warning | ✅ PASS |
| `test_relink_and_refresh_file_status` — Relink ("Locate file") updates path/size and clears `file_missing` | ✅ PASS |
| `test_repair_existing_rows` — Auto-repairs missing/0 B rows by matching `[video_id]` or title | ✅ PASS |
| `test_no_bare_except_pass_in_core` — R9 rule: 0 bare `except: pass` without logging | ✅ PASS |
| `test_no_subprocess_outside_proc` — R1 rule: subprocess strictly in `proc.py` | ✅ PASS |
| **Total Test Suite** | ✅ **113+ passed, 0 failed** |

---

## Bugs Fixed

| Bug | Description | Fix |
|---|---|---|
| B5 | History rows were built from live UI widgets at finish time; clearing widgets caused `title = url` and missing thumbnails | Added `DownloadJob` immutable snapshots created at click time; `save_from_job` saves from snapshot |
| B6 | Deleting any history row deleted its thumbnail even if another row shared the same video | Implemented `thumbnails.py` with ref-count retention (`delete_thumbnail_if_unreferenced`); fallback uses neutral play/audio icons instead of letter badges |
| B7 | History save and file deletion had silent `except: pass` and permanent unlinking | Wired `send2trash` for safe Recycle Bin moves; locked files preserve the history row and display friendly error; zero silent `pass` |
| B15 | Duplicates created multiple rows for same video | Duplicate rule updates date, path, and size for identical `(video_id, kind, quality)` |

---

## Files Added/Modified

| File | Change |
|---|---|
| `app/core/jobs.py` | **NEW:** `DownloadJob` immutable snapshot dataclass with validation |
| `app/core/thumbnails.py` | **NEW:** Permanent thumbnail store, rounded clipping, neutral fallback icons, ref-count retention |
| `app/core/history_db.py` | v2 schema migration, PRAGMA user_version, daily backups (7-day purge), validation |
| `app/core/history_service.py` | **NEW:** High-level history service (`save_from_job`, `delete`, `relink`, `repair_existing_rows`) |
| `app/ui/history_tab.py` | Updated row actions to use `HistoryService.delete` and neutral thumbnail rendering |
| `app/ui/video_tab.py` | Stores `DownloadJob` on queue item; saves history from snapshot via `save_from_job` |
| `app/ui/audio_tab.py` | Stores `DownloadJob` on queue item; saves history from snapshot via `save_from_job` |
| `app/main.py` | Calls `repair_existing_rows()` on startup |
| `tests/test_history_db.py` | Updated tests for migrations, validation, and backups |
| `tests/test_jobs.py` | **NEW:** Tests for DownloadJob snapshot immutability |
| `tests/test_thumbnails.py` | **NEW:** Tests for thumbnail storage and shared ref retention |
| `tests/test_history_service.py` | **NEW:** Tests for save, duplicate update, safe recycle, relink, repair |
| `tests/test_phase2_integrity.py` | **NEW:** Enforces R1 (proc only) and R9 (no bare except pass) |

---

## Sign-off

Phase 2 complete. Ready to proceed to Phase 3.
