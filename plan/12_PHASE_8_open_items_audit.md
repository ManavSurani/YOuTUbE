# Phase 8: M6, M3, M4, M11 Open Items Audit & Resolution

## Goal
Audit the 4 open items identified in the status report (M6, M3, M4, M11):
1. **M6 (Failed queue row "Copy details" button):**
   Add a "Copy details" icon button to failed rows in `app/ui/queue_widget.py`, allowing users to copy the exact error explanation or failure reason to the clipboard. Mark **CLOSED**.
2. **M4 (Two video qualities of same video filename conflict):**
   Audit and confirm that `build_video_cmd` formats filenames with `[%(height)sp]` (e.g. `title [id] [1080p].ext`), preventing overwrites when downloading multiple qualities of the same video. Mark **CLOSED**.
3. **M11 (Identified safety defects):**
   Confirm that dialogue text (S2b), active-job restart limit (S2a), corrupt queue renaming (S1), resume force-stopping (S3), and 90s watchdog (S4) are all resolved and verified. Mark **CLOSED**.
4. **M3 (Path & URL scrubbing in logs):**
   Audit privacy implications. Retain as **OPEN** with full documentation and owner recommendation to avoid breaking log-parsing tests or debug diagnostics in production without an explicit user-facing opt-in.

## Allowed Files
- `app/ui/queue_widget.py` (implementation for M6)
- `tests/test_per_item_cards.py` (unit test for M6)
- `docs/verification/open_items_audit.md` (documentation for M6, M3, M4, M11)
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 8.1: Implement M6 Copy Details Button
- In `app/ui/queue_widget.py`: on `QueueRow`, if `failure_reason` is present, instantiate `self.copy_btn = IconButton("copy", size=28, tooltip="Copy error details", parent=self)`.
- Wire `copy_btn.clicked` to copy `failure_reason` to system clipboard and trigger `flash_success()`.
- Test in `tests/test_per_item_cards.py`.

### Chunk 8.2: Document Audit Status for M6, M3, M4, M11
- Write `docs/verification/open_items_audit.md` documenting evidence, rationale, and status for each row.

## Tests First
Add `test_failed_queue_row_has_copy_details_button_and_copies_to_clipboard` to `tests/test_per_item_cards.py`.

## Expected Failure
Before change, `row.copy_btn` does not exist on failed `QueueRow`.

## Done-When
- M6 test passes.
- All existing tests pass.
- `docs/verification/open_items_audit.md` is committed.
- Matrix rows M6, M3, M4, M11 updated.

## Rollback
`git checkout -- app/ui/queue_widget.py tests/test_per_item_cards.py`.
