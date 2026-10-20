# Phase 3: S1 Corrupt Modern Queue File

## Goal
Gracefully handle corrupt, empty (0-byte), or non-dictionary/non-list modern lane queue files (`queue_video.json`, `queue_audio.json`) by renaming them to `<filename>.corrupt` (or `<filename>.corrupt_<timestamp>` if the `.corrupt` file already exists), logging a warning, starting with an empty queue, and never crashing. When a file contains valid JSON structure but individual job records are malformed, skip the bad records, log warnings, and preserve valid jobs without renaming the entire file.

## Why
Status report audit found that while legacy queue migration (`migrate_legacy_queue_if_needed`) renames bad `queue.json` files to `queue.json.corrupt`, the modern lane queue loader (`_load_persisted_queue()`) merely caught `Exception`, logged at debug level, and left the corrupt file in place. Corrupt or zero-byte files caused recurring decode warnings on every restart, risked crashes on unexpected types, and could prevent users from starting fresh queues without manual filesystem intervention.

## Allowed Files
- `app/core/download_manager.py` (implementation)
- `tests/test_download_manager.py` (unit tests)
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 3.1: Corrupt File Detection, Renaming, and Malformed Item Resilience
1. In `_load_persisted_queue()` in `app/core/download_manager.py`:
   - If `self._queue_file.is_file()`:
     - Check file size. If size is 0: trigger corrupt-file handling.
     - Try reading text and parsing JSON with `json.loads(raw)`. If `json.JSONDecodeError` or other decoding error occurs: trigger corrupt-file handling.
     - Check parsed data type. If data is not an `isinstance(data, (dict, list))`: trigger corrupt-file handling.
   - Corrupt-file handling helper (`_handle_corrupt_queue_file(reason)`):
     - Compute corrupt destination: `corrupt_target = self._queue_file.with_name(f"{self._queue_file.name}.corrupt")`.
     - If `corrupt_target.exists()`:
       - Append timestamp: `f"{self._queue_file.name}.corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`.
     - Perform atomic rename via `os.replace` or `self._queue_file.rename(corrupt_target)`.
     - Log warning: `f"Corrupt or empty {self._queue_file.name} detected ({reason}); renamed to {corrupt_target.name}"`.
     - Reset `self._waiting_queue.clear()`, `self._active_job = None`, `self._restart_counts.clear()`.
     - Return without saving an empty file over the renamed file.
   - In individual item iteration:
     - If item in `waiting_queue` or `active_job` fails deserialization or is not a dict: log warning, skip bad item, load good items, and save the sanitized queue.

## Tests First
Add unit tests to `tests/test_download_manager.py`:
1. `test_load_corrupt_zero_byte_queue_renames_to_corrupt`:
   - Write 0-byte `queue_video.json`. Initialize or invoke `_load_persisted_queue()`.
   - Assert `queue_video.json` no longer exists.
   - Assert `queue_video.json.corrupt` exists.
   - Assert `waiting_jobs` is empty.
2. `test_load_corrupt_invalid_json_renames_to_corrupt`:
   - Write malformed JSON (e.g. `{"waiting_queue": [incomplete`) to `queue_video.json`.
   - Run `_load_persisted_queue()`.
   - Assert `queue_video.json` does not exist, `queue_video.json.corrupt` exists, queue is empty.
3. `test_load_corrupt_queue_when_corrupt_already_exists_adds_timestamp`:
   - Pre-create `queue_video.json.corrupt`.
   - Write malformed JSON to `queue_video.json`.
   - Run `_load_persisted_queue()`.
   - Assert both `queue_video.json.corrupt` and `queue_video.json.corrupt_...` exist.
4. `test_load_corrupt_queue_non_dict_non_list_renames`:
   - Write scalar JSON (e.g. `12345` or `"string"`) to `queue_video.json`.
   - Run `_load_persisted_queue()`.
   - Assert renamed to `.corrupt` and queue is empty.
5. `test_load_queue_with_one_invalid_job_skips_and_does_not_rename`:
   - Modern queue dict with one invalid job (missing URL/id/corrupt fields) and one valid job.
   - Assert queue file is NOT renamed to `.corrupt`.
   - Assert valid job is loaded into `waiting_jobs`.

## Expected Failure
Before implementation, tests will fail because `_load_persisted_queue()` catches decode errors and ignores them without renaming to `.corrupt`, leaving corrupt files on disk.

## Done-When
- All 5 new tests pass.
- Full test suite passes (only known pre-existing failure `test_scope_checker_final`).
- No forbidden files touched.
- Matrix row S1 marked PASS.

## Rollback
If anything fails or breaks invariants, `git checkout -- app/core/download_manager.py tests/test_download_manager.py`.
