# Phase 2: Data and History Integrity

**Goal:** A history row is always correct, complete and independent of the file. Thumbnails never vanish. Deleting is safe and honest.
**Fixes:** B5, B6, B7, B15 (duplicates). **Depends on:** Phase 1.
**Files:** `core/jobs.py` (new), `core/history_service.py` (new), `core/thumbnails.py` (new), `core/history_db.py`, `tests/`.

---

## Chunk 2.1: DownloadJob snapshot

Tasks:
1. `core/jobs.py`: frozen dataclass `DownloadJob` with `job_id`, `url` (clean), `video_id`, `title`, `channel`, `duration_seconds`, `thumbnail_url`, `thumbnail_bytes` (or saved path), `kind` (video/audio), `quality_label`, `height` or `audio_format`, `output_dir`, `created_at`.
2. A job is created **at the moment of Download or Add to queue**, from the already-fetched `VideoInfo`. If info is not ready, fetch it first (or block the click) so a job never has `title = url`.
3. Nothing after job creation reads the link box, the info card or the dropdown.

Done when: unit test creates a job, clears the widgets, finishes the job, and the history row still has the right url, title, thumbnail and duration.

---

## Chunk 2.2: Thumbnail store

Tasks:
1. `core/thumbnails.py`: saves `history/thumbs/<video_id>.jpg` and keeps a **reference count** (or one file per row: `<row_id>.jpg`; pick one and document it).
2. `get_pixmap(video_id, size)` returns a cached rounded pixmap. If the file is missing, re-download from `https://i.ytimg.com/vi/<id>/hqdefault.jpg` in a worker, then update the widget.
3. Last fallback is a neutral play (video) or music (audio) icon. **No letters.**
4. Deleting a history row removes its thumbnail only when no other row uses it.

Done when: test: add video and audio rows for the same id, delete one, thumbnail still loads for the other.

---

## Chunk 2.3: History database v2

Tasks:
1. Add `PRAGMA user_version` and a migration runner.
2. Migration 1 adds columns: `video_id`, `file_missing` (cached flag), `source_job_id`, `channel`, and fills `duration`.
3. Move the database and thumbnails to `%APPDATA%\YOuTUbE\history\` (copy, verify, then switch; keep the old file as `history.db.bak`).
4. Automatic backup `history_YYYYMMDD.bak` once per day, keep the last 7.
5. `add_item` fails loudly (raises) if `file_path` is empty or title equals the URL. The caller logs and shows a message.

Done when: migrating a copy of your current `history.db` works and loses no rows.

---

## Chunk 2.4: HistoryService

Tasks:
1. `save_from_job(job, final_path)`: verifies the file, measures size, stores the row, stores the thumbnail. Returns the row or raises.
2. **Duplicate rule:** same `video_id` + same kind + same quality means update the existing row's date, path and size. Otherwise add a new row.
3. `delete(row_id, delete_file: bool)`:
   - `delete_file=True`: send the file to the **Recycle Bin** (add `Send2Trash` to `requirements.txt`), then remove the row. If the file is locked or the move fails, keep the row and return a clear reason ("The file is open in another program").
   - `delete_file=False`: remove the row only.
4. `clear_all(delete_files: bool)`.
5. `relink(row_id, new_path)` ("Locate file"): verifies the file exists and updates path and size.
6. `refresh_status()`: checks files in a worker thread (not the UI thread) and updates `file_missing`.

Done when: unit tests cover save, duplicate update, delete with file, delete locked file (file held open), relink.

---

## Chunk 2.5: Repair existing rows

Tasks:
1. One-time repair on first start after migration: for each row where `size_bytes == 0` or the file is missing, search the current download folder for a file containing `[<video_id>]` or an exactly matching title.
2. If found: fix path and size. If not: leave the row, mark missing.
3. Rows whose title is a URL: fetch the title in a worker and update it; if offline, retry later.
4. Write a short summary to `app.log` and show one toast ("Repaired 3 items").

Done when: running it on the 4 rows from your screenshots repairs titles and finds files when they exist.

---

## Verification Gate: Phase 2

Evidence in `docs/verification/phase_2.md`.

### Automated
- [ ] Tests for jobs, thumbnails (shared id), migration, save, duplicate update, delete, locked-file delete, relink, repair.
- [ ] No bare `except: pass` left in `core/` (a scan test fails if it finds one without logging).
- [ ] Scan test: no `subprocess` outside `core/proc.py`.

### Manual
- [ ] Download a video, then "Add to queue" a second link right away: both History rows show the correct own title, thumbnail, size and URL.
- [ ] Download the same video as video and as MP3, delete one row: the other keeps its thumbnail.
- [ ] Delete a file in Explorer: the History row stays, shows "File missing" and keeps title and thumbnail.
- [ ] Open a downloaded video in a player, then try "delete file too": a clear message appears, the row stays.
- [ ] "Delete file too" on a normal file: it appears in the Recycle Bin.
- [ ] Move a file to another folder and use "Locate file": the row is reconnected.

### No-terminal check (mandatory)
- [ ] Repeat a download and a delete with the console-less build. No window appears.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 3.
