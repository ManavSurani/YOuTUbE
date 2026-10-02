# Phase 7 Audit: Install, Shortcut, and Updates

**Date:** 2026-10-02  
**Auditor:** Antigravity  
**Target Files:**
1. `installer/setup.iss`
2. `build/build_installer.bat`
3. `build/build_exe.bat`
4. `app/core/tool_manager.py`
5. `app/tools.json`
6. `app/core/shortcut.py`
7. `app/core/app_updater.py`
8. `app/ui/splash.py`
9. `app/core/network_monitor.py`
10. `version.json`

---

## 1. Audit Findings by File

### 1. `installer/setup.iss`
- **What works:**
  - `AppId={{7EBA9B70-1A62-4D3F-A437-4DD99FB4CA6D}` is pinned and constant across all builds for in-place upgrades.
  - `PrivilegesRequired=lowest` ensures user-level installation into `{autopf}` without administrative elevation prompts.
  - Shortcuts for `{autoprograms}` and `{autodesktop}` are created automatically without redundant wizard checkboxes.
  - Supports silent upgrades via `CloseApplications=yes` and `RestartApplications=yes`.
  - Downloads tools on first setup using Inno Setup's built-in download page; if offline, catches failure gracefully and allows app first-run to handle tools setup.
  - Uninstaller removes app binaries and tools in `{userappdata}\YOuTUbE\bin`, but prompts to preserve user data (history and settings), defaulting to Keep (No).
- **Hardening Applied:**
  - Added explicit `IconFilename: "{app}\{#MyAppExe}"` and working directory to shortcut definitions.

### 2. `build/build_exe.bat` and `build/build_installer.bat`
- **What works:**
  - `build_exe.bat` uses `pyinstaller --noconsole --onedir --name YOuTUbE --icon assets\icon.ico` bundling `app/tools.json` and `assets`.
  - `build_installer.bat` checks for ISCC.exe in multiple standard directories, compiles `setup.iss`, checks for `signtool.exe`, and computes SHA-256 using `certutil`.
- **Hardening Applied:**
  - Validated that `--onedir` mode is strictly enforced per Chunk 7.5.

### 3. `app/core/shortcut.py`
- **What worked:**
  - Created desktop shortcut on first run and recorded `shortcut_created: true` in `settings.json`.
- **Risks & Issues Found:**
  - Used hidden PowerShell subprocess with `WScript.Shell`, which created process overhead.
  - Did not handle OneDrive Desktop redirection using native Windows APIs.
  - Did not explicitly handle all 4 lifecycle states: installer-made, missing on first run, already existing, user intentionally deleted.
- **Hardening Applied:**
  - Migrated to native `win32com.client` (runs in-process, 0 console windows, 0 subprocess overhead).
  - Implemented Windows Known Folder API via `ctypes.windll.shell32.SHGetKnownFolderPath` (`FOLDERID_Desktop`) to natively resolve OneDrive-redirected Desktops.
  - Enforced the rule: if `shortcut_created` is True, never recreate the shortcut if the user intentionally deleted it.

### 4. `app/core/tool_manager.py` and `app/tools.json`
- **What works:**
  - Tools are stored in `%APPDATA%\YOuTUbE\bin` (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe`).
  - Safe replacement for yt-dlp: downloads to `.new`, runs `--version`, moves existing to `.bak`, and swaps cleanly.
- **Hardening Applied:**
  - Added auto-repair in `download_manager.py`: on an extraction failure (`unable to extract`, `regex`, `signature`, `n challenge`), updates yt-dlp once and automatically retries the job.
  - Verified JavaScript runtime requirement (`deno`): passes `--js-runtimes deno:<path>` and prepends `BIN_DIR` to `PATH` in `proc.py`.

### 5. `app/core/app_updater.py` and `version.json`
- **What works:**
  - Numeric version comparison (`parse_version`).
  - Supports `min_supported_version` and `force_update`.
  - Rate-limited to once every 24 hours (with manual check bypass).
  - Streams installer in 64KB chunks to `%TEMP%` and computes SHA-256 incrementally.
  - Mismatched hash triggers immediate `.part` deletion and error notification.
  - Silent installer execution using `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS` via hidden process.
- **Hardening Applied:**
  - Standardized manifest field reading in `check_manifest_dict` to accept both `latest_version`/`version` and `installer_url`/`download_url`.

### 6. `app/ui/splash.py` and `app/core/network_monitor.py`
- **What works:**
  - If tools are missing and offline on first run: displays clear message ("Internet is needed for first-time setup") with a Retry button; does not crash.
  - If tools are present: launches immediately even when offline; History remains fully accessible.

---

## 2. Key Questions Checklist

| Question | Status | Details |
|---|---|---|
| Does installer create Desktop and Start Menu shortcut with logo icon? | **YES** | Configured in `setup.iss` `[Icons]`. |
| Does `AppId` stay constant? | **YES** | `{{7EBA9B70-1A62-4D3F-A437-4DD99FB4CA6D}` pinned. |
| Is `PrivilegesRequired=lowest` used? | **YES** | Installs to `{autopf}` without admin prompt. |
| Does installer or app download tools? | **BOTH** | Installer downloads during setup; splash screen serves as safety net. |
| Is SHA-256 verified before running update? | **YES** | Verified incrementally; corrupt files deleted immediately. |
| Are silent installer flags used? | **YES** | `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS` executed hidden. |
| Do history, settings, and queue survive updates? | **YES** | Stored in `%APPDATA%\YOuTUbE\` outside app binary folder. |
