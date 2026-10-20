# Phase 6 Plan: Friendly Error Messages

## Goals
Satisfy autonomous requirement **E1**:
- The 14 error samples map to the friendly plain-language texts specified in the prompt.
- Fix generic fallback: remove mention of the non-existent "Copy the details" button; replace with `"Something went wrong. Open Settings and press Export log to see the details."`
- Keep all existing valid mappings.
- Test-first methodology (Rule R2): add test table for 14 sample stderr lines and generic fallback before updating `app/core/errors.py`.
- Document test changes in `docs/verification/test_changes.md`.

---

## Chunk 6.1: Test Suite for the 14 Error Samples (`tests/test_errors.py`)
- Add tests covering the 14 sample stderr lines:
  1. Private: `"This video is private or for members only."`
  2. Age: `"This video is age restricted and can't be downloaded without sign-in."`
  3. Bot check: `"YouTube asked for verification. Try again later or update tools."`
  4. Unavailable / Geo: `"This video is not available."`
  5. DNS / Network: `"The internet connection was interrupted. Check your connection and press Retry."`
  6. Disk full: `"Not enough free space..."`
  7. HTTP 403: `"YouTube refused the download for now. Wait a minute and press Retry. If it keeps happening, update the tools."`
  8. HTTP 429: `"YouTube says there were too many requests. Wait a few minutes and try again."`
  9. HTTP 404: `"This video or file is no longer available."`
  10. WinError / Socket: `"The internet connection was interrupted. Check your connection and press Retry."`
  11. PermissionError: `"The app cannot write to the download folder. Choose another folder in Settings or close the program that uses the file."`
  12. Merger failure: `"The video and audio could not be combined. Press Retry. If it repeats, update the tools."`
  13. Copyright: `"This video was removed because of a copyright claim."`
  14. Live / Premiere: `"This is a live stream or premiere that is not ready yet."`
  15. Generic fallback: `"Something went wrong. Open Settings and press Export log to see the details."`

---

## Chunk 6.2: Implementation in `app/core/errors.py`
- Add pattern matching in `explain()` before the generic fallback:
  - `403` / `http error 403`
  - `429` / `too many requests`
  - `404` / `http error 404`
  - `permissionerror` / `permission denied`
  - `[merger]` / `invalid data found` / `error parsing`
  - `copyright`
  - `live event will begin` / `is live` / `premiere`
- Update network error message to: `"The internet connection was interrupted. Check your connection and press Retry."`
- Update fallback to: `"Something went wrong. Open Settings and press Export log to see the details."`

---

## Chunk 6.3: Verification of Phase 6
- Run `python -m pytest tests/test_errors.py`.
- Run full test suite.
- Run `python tools/check_scope.py --baseline cdfed4e --final`.
- Update `docs/verification/requirements_matrix.md` row E1 to PASS.
- Update `docs/verification/autonomy_log.md` and commit.
