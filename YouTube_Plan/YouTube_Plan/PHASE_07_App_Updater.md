# Phase 7 — App Updater

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** the app finds new versions, downloads them safely, verifies them, installs silently, and keeps all history and settings.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

`version.json` (hosted on GitHub, raw file or release asset):

```json
{
  "latest_version": "1.2.0",
  "min_supported_version": "1.0.0",
  "release_date": "2026-10-20",
  "installer_url": "https://github.com/<you>/<repo>/releases/download/v1.2.0/YouTube_Setup.exe",
  "sha256": "<hash of the installer>",
  "notes": ["Faster merging", "Fixed a history bug"],
  "force_update": false
}
```

---

## Chunk 7.1 — Manifest check

**Files you may touch (new):** `app/core/app_updater.py`, `tests/test_app_updater.py`; edit `app/version.py` (set `UPDATE_MANIFEST_URL`).

**Do**
- Fetch `version.json` (timeout 10 s) at launch and then every 24 h (`last_app_check`). Only when `auto_update` is on.
- Compare versions as numbers (`1.10.0` is newer than `1.9.0`), never as plain text.
- Result: `none`, `available(version, notes)`, or `required` (when `force_update` is true or the current version is below `min_supported_version`).

**Verify** (unit tests)
- [ ] `1.10.0 > 1.9.0`, equal versions → `none`, older manifest → `none`.
- [ ] `min_supported_version` above current → `required`.
- [ ] Bad JSON, missing fields, or no internet → `none`, no crash, logged.

## Chunk 7.2 — Banner

**Files you may touch:** `app/ui/main_window.py`.

**Do**
- Thin row at the top: "Version 1.2.0 is available.  [Update now]  [Later]" in the `info` colour on `surface`. "Later" hides it until the next launch.
- If `required`: the main controls stay locked until the update is done, with a clear sentence why.

**Verify**
- [ ] Point the manifest at a fake newer version: banner appears; "Later" hides it; it returns on next launch.
- [ ] `required` locks the Download controls but History still opens.
- [ ] Banner follows the design file.

## Chunk 7.3 — Download and verify

**Files you may touch:** `app/core/app_updater.py`.

**Do**
- Download the installer to `%TEMP%` with progress (show it in the banner row).
- Compute SHA-256 and compare with the manifest. **Mismatch → delete the file and show "The update could not be verified."** Never run an unverified file.

**Verify**
- [ ] Correct hash → file kept and ready.
- [ ] Altered file (change one byte) → rejected and deleted.
- [ ] Network drop mid-download → clean failure message, no half file left, app keeps working.

## Chunk 7.4 — Silent install and relaunch

**Files you may touch:** `app/core/app_updater.py`, `app/ui/main_window.py`.

**Do**
- Start the installer through `proc.py`: `YouTube_Setup.exe /SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`, then exit the app so files can be replaced.
- Installer must reuse the same `AppId` so it upgrades in place.

**Verify** (needs a real installer from Phase 9, or a stub installer for testing)
- [ ] Update 1.0.0 → 1.1.0: app closes, reopens as 1.1.0.
- [ ] History, thumbnails, settings and tools are still there.
- [ ] No second installed copy in "Apps & features".
- [ ] No terminal window at any moment.

---

## Phase 7 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] End-to-end with a test release: banner → download → hash check → silent install → relaunch.
- [ ] Wrong-hash test rejects the file.
- [ ] Only files from the chunk lists changed. User said "go on".
