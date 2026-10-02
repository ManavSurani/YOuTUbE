# Phase 7: Install, Shortcut and Updates (audit and harden)

**Goal:** Prove that install, first-run setup, the desktop shortcut, tool updates and app updates work on a clean PC, and fix what does not.
**Depends on:** Phases 1 to 6.
**Existing code to audit (not reviewed yet):** `installer/setup.iss`, `build/build_installer.bat`, `core/tool_manager.py`, `app/tools.json`, `core/app_updater.py`, `core/shortcut.py`, `ui/splash.py`, `core/network_monitor.py`, `version.json`.

---

## Chunk 7.1: Audit

Tasks:
1. Read each file above and write findings into `docs/audit_phase7.md` (what works, what is missing, what is risky). Ask the owner before changing anything beyond the fixes below.
2. Check: does the installer create the Desktop and Start Menu shortcut with the logo icon? Does `AppId` stay constant? Is `PrivilegesRequired=lowest` used? Does the installer download or does the app download tools on first run?
3. Check the updater against `version.json`: SHA-256 verified before running? Silent install flags used? App closed and relaunched correctly?

Done when: the audit file exists and the owner approves the list of fixes.

---

## Chunk 7.2: Shortcut rules

Tasks:
1. Installer creates `YOuTUbE.lnk` on the Desktop and in the Start Menu automatically (no checkbox).
2. First-run safety net in `core/shortcut.py`: only if `shortcut_created` is false and no shortcut exists, create it with `win32com` (no console), then set the flag.
3. Find the Desktop with the Known Folder API (handles OneDrive redirection).
4. Never duplicate or recreate after the flag is true. Uninstaller removes shortcuts.

Done when: tests cover all four situations (installer-made, missing, already exists, user deleted).

---

## Chunk 7.3: Tools: first run and updates

Tasks:
1. Tools live in `%APPDATA%\YOuTUbE\bin`. Verify downloads with a size/hash check where upstream provides one.
2. Update flow: download to `.new`, run `--version`, swap, keep `.bak`, roll back on failure.
3. Auto-repair: on an extraction failure, update yt-dlp once and retry the job automatically.
4. Check yt-dlp's current JavaScript runtime requirement (deno) against the yt-dlp wiki and make sure the app passes what yt-dlp needs.
5. Offline at first run: friendly "Internet is needed for first-time setup" with Retry; History stays usable.

Done when: deleting `yt-dlp.exe` and restarting restores it with an animated splash, and an old version is replaced automatically.

---

## Chunk 7.4: App updater

Tasks:
1. Manifest `version.json` on GitHub: `latest_version`, `min_supported_version`, `installer_url`, `sha256`, `notes`, `force_update`.
2. Update banner appears under the header; download with progress; **verify SHA-256**; run installer silently (`/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`); relaunch.
3. History, settings and queue survive the update (they live in `%APPDATA%`).
4. A wrong hash is rejected and deleted.

Done when: updating 1.0.0 to 1.0.1 keeps History and the queue.

---

## Chunk 7.5: Build

Tasks:
1. `pyinstaller --noconsole --onedir --icon logo.ico` (use `--onedir`).
2. Inno Setup builds `YOuTUbE_Setup.exe` with the same `AppId` each time.
3. Sign both exe files if a certificate is available.
4. Record the SHA-256 for `version.json`.

Done when: the build scripts produce a working installer from a clean checkout.

---

## Verification Gate: Phase 7

Evidence in `docs/verification/phase_7.md`.

### Automated
- [ ] Shortcut tests (four situations). Tool-manager tests (missing, old, corrupt download, rollback). Updater tests (newer, same, force, bad hash).

### Manual (use a clean Windows 10 or 11 PC or Windows Sandbox)
- [ ] Run `YOuTUbE_Setup.exe` with internet only: installs, desktop shortcut with the YOuTUbE icon appears automatically.
- [ ] First launch downloads all tools with a visible animated splash and then opens.
- [ ] Install with the internet off: installer finishes, app asks for internet, then recovers.
- [ ] Delete the desktop shortcut, restart the app: the shortcut is **not** recreated.
- [ ] Old yt-dlp is replaced automatically.
- [ ] Update 1.0.0 to 1.0.1 works and keeps History and queue.
- [ ] Uninstall removes shortcuts and app files; user data is kept unless the user chooses to remove it.

### No-terminal check (mandatory)
- [ ] Install, first run, tool update and app update all complete with no console window at any moment.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 8.
