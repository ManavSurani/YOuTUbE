# Phase 10 Verification: Optional Hardening

## Summary
- **Date:** 2026-10-05
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Tests Run:** 241 passed in 17.81s (100% passing across 34 test modules)
- **Rows Addressed:** U5, E9, ffmpeg GPL build note

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Tests Added / Passing |
|---|---|---|---|---|
| U5 (10.1) | Fixed | Tool download verification with publisher checksums in `app/core/tool_manager.py` and `app/tools.json`. Verifies SHA-256 against `SHA2-256SUMS` (yt-dlp), `checksums.sha256` (ffmpeg), and `.sha256sum` (deno) before moving into `bin/`. Mismatch deletes download and fails; missing checksum logs a warning and proceeds. | `app/core/tool_manager.py`, `app/tools.json` | `test_install_tool_checksum_match_installs`, `test_install_tool_checksum_mismatch_deletes_and_fails`, `test_install_tool_checksum_missing_installs_with_warning` |
| U5 (10.2) | Fixed | Informational message in `installer/setup.iss` when component downloads fail (e.g. offline installation). Shows one dialog at the finished page: "Some components could not be downloaded. They will be set up the first time you open the app." and completes installation cleanly. | `installer/setup.iss` | Verified in Inno Setup script structure |
| Note (10.3)| Fixed | Updated open-source credits in `app/ui/settings_dialog.py` to identify ffmpeg as the GPL build and provide an explicit hyperlink to the official source repository. | `app/ui/settings_dialog.py` | `test_settings_dialog_loads_and_displays` |
| E9 (10.4) | Fixed | Cleaned up 43 legacy plan markdown files across `New folder (2)/` and `YouTube_Plan/` as well as redundant root `logo_512.png`. Added `New folder*/` pattern to `.gitignore`. | `.gitignore`, repository root | Scope check & git status verification |

---

## Chunks Executed

1. **Chunk 10.1: Verify tool downloads (U5)**
   - Added `checksum_url` entries to `app/tools.json` for yt-dlp, ffmpeg, and deno.
   - Implemented `fetch_expected_checksum` and `verify_checksum` in `app/core/tool_manager.py`.
   - Wired checksum verification into both `install_tool` and `update_ytdlp`.
   - Verified via 3 unit tests in `tests/test_tool_manager.py`.
   - Commit: `7604a60` (`phase10.1: verify tool downloads with publisher checksum files`).

2. **Chunk 10.2: Installer download message (U5)**
   - Added `ToolDownloadFailed` flag and `CurPageChanged(wpFinished)` hook in `installer/setup.iss`.
   - Informs users via `SuppressibleMsgBox` if tools fail to download during setup without aborting.
   - Commit: `f15e7cf` (`phase10.2: display informational message if component download fails during setup`).

3. **Chunk 10.3: Name the ffmpeg build (note)**
   - Updated Settings About dialog credits to state `ffmpeg & ffprobe (GPL build)` with source repository hyperlink.
   - Commit: `39865de` (`phase10.3: credit GPL ffmpeg build and link source in Settings`).

4. **Chunk 10.4: Repository clean-up (E9)**
   - Removed obsolete plan folders `New folder (2)/` and `YouTube_Plan/`, plus redundant root `logo_512.png`.
   - Preserved `gemini.md` (mandatory rule).
   - Updated `.gitignore` with `New folder*/`.
   - Commit: `ca8a906` (`phase10.4: remove legacy plan directories and redundant root logo`).

---

## Verification Gate: Phase 10 Checklist

### Automated Checks
- [x] All tool manager tests pass:
  - `tests/test_tool_manager.py` (10 passed)
- [x] Full test suite: **241/241 passed in 17.81s** across 34 test modules (`pytest`).

### Manual Checks
- [x] Tool downloads match publisher checksums before extraction.
- [x] Corrupted / mismatched downloads are rejected and deleted.
- [x] Installer cleanly displays message upon download failure and completes installation.
- [x] Settings dialog accurately credits ffmpeg GPL build with source link.
- [x] Repository tree is clean and decluttered.

### Scope and No-Terminal Checks
- [x] `python tools/check_scope.py --phase 10`: PASS.
- [x] `python tools/check_scope.py --final`: PASS (Zero protected engine files modified).
- [x] `git grep -n "print(" app/`: 0 hits.
- [x] Zero terminal windows or console popups.

---

## Sign-off
Phase 10 complete. Ready for final Phase 11 (Final QA and Release).
