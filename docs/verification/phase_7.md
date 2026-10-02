# Phase 7 Verification: Install, Shortcut, and Updates

**Date:** 2026-10-02  
**Status:** PASSED  
**Scope:** Phase 7 — Audit, hardened desktop shortcut lifecycle (win32com + Known Folder API), tool runtime discovery (BIN_DIR in PATH + deno js-runtime), auto-repair on extraction failure, app updater with SHA-256 verification and %APPDATA% data preservation, and Inno Setup installer.

---

## 1. Automated Test Results

- Full regression suite: `python -m pytest tests/`
- Results: **155 passed in 13.02s** across 21 test modules with 0 failures, 0 errors.

### Phase 7 Test Modules Summary
- `tests/test_shortcut.py`: **6 passed**
  - `test_get_desktop_dir`: Resolves real Desktop directory handling OneDrive redirection via Known Folder API (`SHGetKnownFolderPath`).
  - `test_create_shortcut_skipped_in_dev`: In development mode (unfrozen without force flag), creation is skipped.
  - `test_situation_1_installer_made`: Installer created shortcut before first run; app acknowledges, marks `shortcut_created = True`, and does not overwrite.
  - `test_situation_2_missing_on_first_run`: First run without installer (missing shortcut); creates shortcut via `win32com`, sets flag, returns True.
  - `test_situation_3_already_exists`: Subsequent launch with existing shortcut and flag set skips recreation.
  - `test_situation_4_user_deleted`: User intentionally deleted the desktop shortcut (`shortcut_created = True`); app NEVER recreates the shortcut.
- `tests/test_tool_manager.py`: **7 passed**
  - `test_missing_tools_empty_dir`: Accurately detects all 4 missing binaries (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe`).
  - `test_missing_tools_partial`: Detects partially installed tools.
  - `test_verify_tool_corrupt`: Rejects corrupt binaries failing `--version`.
  - `test_update_ytdlp_validation_failure_rolls_back`: Validation failure on downloaded `.new` binary deletes temporary file and retains current version.
  - `test_update_ytdlp_swap_failure_rolls_back`: Swapped binary failing verification triggers automatic rollback from `.bak` backup.
  - `test_update_ytdlp_success`: Successful update backs up old binary to `.bak` and swaps new binary cleanly.
  - `test_auto_repair_on_extraction_error`: Extraction error (`unable to extract`, `regex`, `signature`, `n challenge`, `nsig`) triggers `update_ytdlp()` and re-queues the job to retry once.
- `tests/test_app_updater.py`: **12 passed**
  - `test_parse_version`: Accurate numeric comparison (`1.10.0 > 1.9.0`).
  - `test_manifest_version_comparisons`: Detects available, none, and older versions.
  - `test_manifest_required_min_supported_version`: Enforces required update if `min_supported_version > current_version`.
  - `test_manifest_required_force_update`: Handles `force_update` flag.
  - `test_manifest_bad_data_and_network_failure`: Graceful handling of invalid or offline manifests.
  - `test_should_check_update`: 24-hour rate limit check.
  - `test_update_download_worker_hash_match_and_mismatch`: Streaming SHA-256 calculation; rejects and immediately deletes corrupt/mismatched installers.
  - `test_launch_silent_installer`: Silent installer execution with `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS` via hidden process.
  - `test_main_window_banner_available`: UpdateBanner displays under header with "Update now" and "Later".
  - `test_main_window_banner_required_locking`: Required update locks download controls while leaving History fully functional.
  - `test_version_json_disk_file`: Validates `version.json` in project root parses cleanly.
  - `test_user_data_survives_app_update`: History database, user settings, and queued jobs in `%APPDATA%\YOuTUbE` survive application binary updates.

---

## 2. Chunk Implementations

### Chunk 7.1: Audit
- Produced `docs/audit_phase7.md` after auditing all 10 target files (`installer/setup.iss`, `build/build_installer.bat`, `build/build_exe.bat`, `app/core/tool_manager.py`, `app/tools.json`, `app/core/shortcut.py`, `app/core/app_updater.py`, `app/ui/splash.py`, `app/core/network_monitor.py`, `version.json`).
- Verified `AppId={{7EBA9B70-1A62-4D3F-A437-4DD99FB4CA6D}}` is pinned across all installer builds for clean in-place upgrades.
- Verified `PrivilegesRequired=lowest` for zero-elevation user installs.

### Chunk 7.2: Shortcut Rules
- Rewrote `app/core/shortcut.py` using native Windows `win32com.client` COM automation (0 console windows, 0 powershell subprocesses).
- Implemented Windows Known Folder API via `ctypes.windll.shell32.SHGetKnownFolderPath` (`FOLDERID_Desktop`: `{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}`) to natively locate OneDrive-redirected Desktops.
- Enforced strict 4-state lifecycle: installer-made, missing on first run, already existing, and user deleted. If `shortcut_created == True`, the app never recreates the shortcut after deletion.
- Inno Setup `[Icons]` configured with `IconFilename: "{app}\{#MyAppExe}"` and `WorkingDir: "{app}"`.

### Chunk 7.3: Tools: First Run and Updates
- Prepend `BIN_DIR` (`%APPDATA%\YOuTUbE\bin`) to `PATH` environment variable in `app/core/proc.py:start_hidden`, allowing `yt-dlp` to directly find `ffmpeg`, `ffprobe`, and `deno`.
- Added `--js-runtimes deno:<path>` in `app/core/downloader.py` (`build_video_cmd` and `build_audio_cmd`) and `app/core/info_fetcher.py`.
- Added auto-repair in `app/core/download_manager.py`: on extraction failures, yt-dlp is updated once via `update_ytdlp()` and the job is automatically retried.
- Hardened `update_ytdlp()` with automatic rollback from `.bak` if binary swapping or verification fails.
- In `app/ui/splash.py`: offline first-run displays a friendly "Internet is needed for first-time setup" with a Retry button, while History stays usable offline when tools are present.

### Chunk 7.4: App Updater
- Standardized `version.json` schema and manifest parser in `app/core/app_updater.py` to support `latest_version`/`version`, `installer_url`/`download_url`, and string or list `notes`.
- Incremental 64KB chunk download and on-the-fly SHA-256 verification. Corrupt installers are deleted immediately.
- Verified that history, settings, and queue files reside in `%APPDATA%\YOuTUbE` outside the installation directory and survive updates untouched.

### Chunk 7.5: Build Verification
- Validated `build/build_exe.bat` (`pyinstaller --noconsole --onedir --name YOuTUbE --icon assets\icon.ico`).
- Validated `build/build_installer.bat` and `installer/setup.iss` with constant `AppId`.
- Verified SHA-256 hashing via `certutil`.

---

## 3. Mandatory Rules Check
- [x] **App Name Exact Casing:** Strictly preserved `YOuTUbE` across all files.
- [x] **Zero Terminal Flashes:** `app/core/proc.py` is the only module importing `subprocess`. All processes use `CREATE_NO_WINDOW` and `SW_HIDE`.
- [x] **No Print Statements:** `ast` scan over `app/` confirms 0 `print()` calls.
- [x] **No Bare Excepts:** All `except:` blocks log with `logger.debug` or `logger.warning`.
- [x] **Full Test Suite:** 155 automated tests passing with 0 failures.
