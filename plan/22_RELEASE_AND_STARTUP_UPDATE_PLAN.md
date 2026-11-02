# Plan 22: One-Command Release + Update on App Start

## Goal

1. **One command releases a new version:**
   ```
   python tools/release.py 1.0.3 --notes "Exact download size"
   ```
   It runs the tests, raises the version, builds the app and installer, uploads the installer to GitHub, and updates `version.json`. After that, every installed app can see the new version.

2. **The app updates itself when it opens** (desktop shortcut):
   ```
   [logo] YOuTUbE
   Checking for app update…          ← new, first
   Downloading update 1.0.3… 45%     ← only if a new version exists
   Installing update…                → app closes, installs, reopens by itself
   ─────────────────────────────────
   Checking for tool updates…        ← same as today (yt-dlp)
   Starting…                         → main window
   ```

Nothing else changes: same splash screen look (logo, title, status text, 6 px bar), same colors and fonts, same yt-dlp/ffmpeg/deno steps, same banner in the main window as a fallback.

---

## Findings (read from code and checked online)

| # | Where | What is true today | Effect on this plan |
|---|---|---|---|
| **F1** | GitHub API `repos/ManavSurani/YOuTUbE/releases` | **No releases exist.** | `version.json` points to `…/releases/download/v1.0.2/YOuTUbE_Setup.exe`, which returns **404**. The updater has never had a file to download. The release script fixes this. |
| **F2** | `version.json` `sha256` | `cda03a…`. Today's build hash is `393e85…`. | The hash must be set **after** each build, by the script, never by hand. |
| **F3** | `app/version.py` (`APP_VERSION`), `installer/setup.iss` (`#define MyAppVersion`), `version.json` | The version number lives in **3 places**, all `1.0.2`. | The script must change all 3 together. |
| **F4** | `app/version.py` → `UPDATE_MANIFEST_URL` = `raw.githubusercontent.com/…/main/version.json` | Apps read the manifest from the **main** branch. | A release only goes live when `version.json` is pushed to `main`. GitHub's raw cache can take up to about 5 minutes. |
| **F5** | Branches | `fix/ui-pass` is **63 commits ahead** of `origin/main`, with uncommitted work (Plans 20 and 21, gradle). | The first release needs this work committed and merged to `main`. That is the owner's decision (Phase 0). |
| **F6** | `gh` (GitHub CLI) | **Not installed.** | Needed to upload releases. One-time owner setup (Phase 0). |
| **F7** | `app/core/app_updater.py` | Already has everything needed: `check_for_update()`, `UpdateDownloadWorker` (download + SHA-256 check), `launch_silent_installer()` (`/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`), `should_check_update()` (respects `auto_update`). | **Reuse as is.** This file stays unchanged. |
| **F8** | `app/ui/splash.py` → `StartupWorker.run()` | Order: internet check → missing tools → yt-dlp update (24 h) → shortcut → done. Splash has a status label and progress bar. | The update step goes **after the internet check, before the tools.** The existing label and bar are reused. |
| **F9** | `app/ui/main_window.py` → `_check_for_updates()` | Checks once per 24 h **after** the window opens and shows `UpdateBanner`. | Stays as the fallback. When the splash has checked, it saves `last_app_check`, so the window does not check twice. **No edit needed.** |
| **F10** | `installer/setup.iss` `[Run]` → `Flags: nowait postinstall skipifsilent` | `skipifsilent` means: **after a silent install, the app is not reopened.** `/RESTARTAPPLICATIONS` does not help, because the app quits itself before the installer runs. | After an update the app would just disappear. Fix: remove `skipifsilent` (Phase 3). |
| **F11** | Running from source (`python -m app.main`) | No `sys.frozen`. | The splash must **never** auto-install while running from source, or it would replace the installed app during development. |
| **F12** | `installer/setup.iss` → `PrivilegesRequired=lowest`, installed to `%LOCALAPPDATA%\Programs\YOuTUbE` | Per-user install, no admin prompt. | A silent update needs no UAC prompt. |

---

## Rules for Claude (binding for this plan)

| # | Rule |
|---|---|
| **R1** | **Only the files in the Allowed list may change.** Every other file must show 0 lines changed. |
| **R2** | **Reuse what exists.** Use `app_updater.check_for_update`, `UpdateDownloadWorker`, `launch_silent_installer`, `should_check_update`, `parse_version`, the splash `status_label` / `progress_bar`, and `build\build_installer.bat`. Never copy their logic into new code. |
| **R3** | **Protected files stay protected:** `app/core/app_updater.py`, `app/ui/main_window.py`, `app/core/tool_manager.py`, and `app/ui/theme.py` get **0 edits**. `installer/setup.iss` gets **one** hand edit (Phase 3: remove `skipifsilent`). After that, only the release script changes its version line. |
| **R4** | **Smallest change only.** No new windows, dialogs, colors, fonts, styles, settings UI, or refactors. The splash keeps its size, layout, and fade. All new text is plain (Plan 17 style). |
| **R5** | **Safe by default.** (a) No auto-install when running from source (F11). (b) No auto-install when `auto_update` is off. (c) Any update error (offline, timeout, bad hash, installer missing) → the app starts normally, exactly as today. (d) The same failed version is never retried in a loop. |
| **R6** | **The manifest goes last.** The script changes `version.json` on `main` **only after** the installer is uploaded and its downloaded SHA-256 matches. If any earlier step fails, users see nothing new. |
| **R7** | **Failing test first:** write each new test, see it fail for the right reason, then change the code. |
| **R8** | **Tests are add-only.** Never delete, weaken, or rewrite an existing test. If an existing test must change, **stop and ask the owner**. |
| **R9** | **Known red tests:** `test_check_scope.py::test_scope_checker_final` (old failure) and `test_single_instance.py::test_single_instance_detection` (fails while the app is open). Do not edit `tools/check_scope.py`. Close the app before test runs. |
| **R10** | **Outward actions need the owner's "yes" at that moment:** merging to `main`, pushing, creating a GitHub release, or uploading a file. This applies even inside the loop (Phases 5–6). Approval of this plan is **not** approval to publish. |
| **R11** | **No extra docs** besides this plan and `docs/verification/release_update_result.md`. Usage help lives in `tools/release.py --help`. |
| **R12** | **Commits:** only when the owner asks, except commits the release script makes itself during an approved release (version bump + manifest). |
| **R13** | **Loop rule:** after approval, run Phase 1 → 2 → 3 → 4 back to back. Each phase ends with a **gate** (its tests + full suite). Pass → next phase. Stop only if (a) a gate fails and the fix would break R1–R12, (b) an existing test needs changing, or (c) an R10 action is next. Phases 5–6 start only after the owner says yes. Send **one** summary after Phase 4 and one at the end. |

**Allowed files (complete list):**

```
tools/release.py                              (new, Phases 1–2)
tests/test_release_script.py                  (new, Phases 1–3)
app/ui/splash.py                              (Phase 4)
tests/test_splash_update.py                   (new, Phase 4)
installer/setup.iss                           (Phase 3 flag; version line by script only)
app/version.py                                (version line, by script only)
version.json                                  (by script only)
docs/verification/release_update_result.md    (result note)
plan/22_RELEASE_AND_STARTUP_UPDATE_PLAN.md    (this plan)
```

---

## Phase 0: Prerequisites and Baseline (owner and Claude)

### Task 0.1: Owner, one-time setup
1. Install the GitHub CLI: `winget install --id GitHub.cli`
2. Log in: `gh auth login` (GitHub.com → HTTPS → browser)
3. Check: `gh auth status` shows `ManavSurani`.

### Task 0.2: Owner, get `main` ready (F5)
- Decide what goes into the first release. The normal path: commit the Plan 20 and 21 work on `fix/ui-pass`, then merge `fix/ui-pass` into `main` and push.
- Claude does this **only** when the owner says so (R10).
- Until then, Phases 1–4 can be built and tested on `fix/ui-pass`.

### Task 0.3: Claude, baseline
```
git status --porcelain
pytest -q
```
Record the counts. Expected: everything passes except the two R9 tests.

**Phase 0 gate:** baseline recorded. `gh` set up (or noted as pending, which only blocks Phases 5–6).

---

## Phase 1: Release Script Core (pure functions, no network, no git)

### Task 1.1: Failing tests in `tests/test_release_script.py`

| Test | Checks |
|---|---|
| `test_bump_patch` | `bump("1.0.2") == "1.0.3"`, `bump("1.0.9") == "1.0.10"` |
| `test_validate_new_version` | accepts `1.0.3` over `1.0.2`; rejects `1.0.2`, `1.0.1`, `1.0`, `v1.0.3x`, empty |
| `test_set_version_py` | replaces only the `APP_VERSION = "…"` line; `APP_NAME` and `UPDATE_MANIFEST_URL` lines are identical |
| `test_set_setup_iss` | replaces only `#define MyAppVersion "…"`; all other lines are byte-identical |
| `test_build_manifest` | sets `latest_version`, `version`, `installer_url`, `download_url`, `sha256`, `release_date`, `notes`; **keeps** `min_supported_version`, `force_update`, `android` exactly |
| `test_manifest_passes_app_updater` | `check_manifest_dict(build_manifest(...), current_version="1.0.2").status == "available"` (uses the real app parser) |
| `test_installer_url_pattern` | `https://github.com/ManavSurani/YOuTUbE/releases/download/v1.0.3/YOuTUbE_Setup.exe` |
| `test_sha256_file` | matches `hashlib.sha256` for a tmp file |

### Task 1.2: Code in `tools/release.py`
Small, standard library only. Pure functions: `bump`, `validate_new_version` (uses `app.core.app_updater.parse_version`, R2), `set_version_py`, `set_setup_iss`, `build_manifest`, `installer_url`, `sha256_file`. Plus `main()` with `argparse` (`version` optional, default = patch bump; `--notes`, repeatable; `--dry-run`). In this phase, `main()` only parses arguments.

### Task 1.3: Run
```
pytest tests/test_release_script.py -q
pytest -q
```
**Phase 1 gate:** green, same R9 failures only.

---

## Phase 2: Release Script Flow + Dry Run

### Task 2.1: The release flow (order matters, R6)

| Step | Action | If it fails |
|---|---|---|
| 1 | **Preflight:** on branch `main`; tree clean; `HEAD == origin/main` after `git fetch`; `gh auth status` OK; new version is valid; tag `vX` does not exist | Stop. Nothing changed. |
| 2 | **Tests:** `python -m pytest -q`. Only the R9-known failures are allowed. | Stop. Nothing changed. |
| 3 | **Bump:** write the version into `app/version.py` and `installer/setup.iss` | Stop and restore both files. |
| 4 | **Build:** `cmd /c build\build_installer.bat` (reused) → `Output\YOuTUbE_Setup.exe` | Stop and restore both files. |
| 5 | **Commit + push:** `release: vX` (version.py + setup.iss) → `git push origin main` | Stop. Print the recovery steps. |
| 6 | **Publish:** `gh release create vX Output\YOuTUbE_Setup.exe --target main --title "YOuTUbE X" --notes …` | Stop. The manifest is untouched, so users see nothing. |
| 7 | **Verify:** download the asset URL and compare its SHA-256 with the local file | Stop. The manifest is untouched. |
| 8 | **Manifest:** `build_manifest()` → write `version.json` → commit `release: vX manifest` → push | Stop. Print the recovery steps. |
| 9 | **Live check:** poll the raw manifest URL (every 30 s, up to 10 min) until it shows `X` | Warn only (cache delay). |

- Every external command goes through **one** helper `run(cmd)` in `tools/release.py` that logs it and fails on a non-zero exit code. Tests mock this helper.
- `--dry-run` runs steps 1–2 (with the branch check relaxed to a warning) and step 4 with the **current** version. It prints the planned version, SHA-256, URL, and manifest diff. It writes no files, makes no commits, pushes nothing, and uploads nothing.

### Task 2.2: Failing tests (mock `run`, tmp repo copies)

| Test | Checks |
|---|---|
| `test_flow_order` | the commands are called in the order 1→9; the manifest commit comes **after** `gh release create` and the hash check |
| `test_stops_on_dirty_tree` | no bump, build, or `gh` call |
| `test_stops_on_failed_tests` | no bump; files unchanged |
| `test_build_failure_restores_files` | `version.py` and `setup.iss` are back to their original text |
| `test_upload_failure_keeps_manifest` | `version.json` is unchanged |
| `test_hash_mismatch_keeps_manifest` | `version.json` is unchanged; exit code is non-zero |
| `test_dry_run_changes_nothing` | no git, `gh`, or file writes; the plan is printed |

### Task 2.3: Real dry run (local only, safe)
```
python tools/release.py --dry-run
```
Check: the installer is built, a SHA-256 is printed, and `git status` is the same as before.

**Phase 2 gate:** new tests green, full suite green (R9 only), dry run OK.

---

## Phase 3: Installer Reopens the App After a Silent Update (F10)

### Task 3.1: Failing test in `tests/test_release_script.py`
`test_setup_iss_relaunches_after_silent_install`: the `[Run]` line for `{#MyAppExe}` has `postinstall` and **no** `skipifsilent`.

### Task 3.2: Code
In `installer/setup.iss`, change:
```
Flags: nowait postinstall skipifsilent
```
to:
```
Flags: nowait postinstall
```
Nothing else in that file changes (R3). A normal (non-silent) install still shows the "Launch YOuTUbE" checkbox as today.

**Phase 3 gate:** green. The real check is in Phase 6.

---

## Phase 4: Update Check on the Startup Screen (`app/ui/splash.py`)

### Task 4.1: Behaviour

`StartupWorker.run()`: directly after `is_online = check_internet()`, add step 1b:
```
if is_online and auto-update is allowed (see below):
    status "Checking for app update…"
    info = check_for_update(timeout=5.0)          # reused, R2
    save settings["last_app_check"] = now          # main window will not check again (F9)
    if info.status in ("available", "required"):
        emit update_found(info) and return         # stop here; tools run after the update
```
**Auto-update is allowed** only when all of these are true:
- `getattr(sys, "frozen", False)` (F11)
- `settings.get("auto_update", True)`
- the worker was not started with `skip_app_update=True`
- **Loop guard:** `settings.get("update_attempt_version")` is not `info.latest_version` **while** `APP_VERSION` is still lower. That would mean an install was tried and did not apply, so skip and let the banner handle it.

`SplashScreen`:
- `_on_update_found(info)` → status `Downloading update {v}…` → start the **existing** `UpdateDownloadWorker(info)`. Connect `progress` → `progress_bar` + status `Downloading update {v}… {n}%`, and `stage` → status.
- `finished(path)` → status `Installing update…` → save `update_attempt_version = v` → `launch_silent_installer(path)` → if True, `QApplication.quit()`.
- `failed(msg)`, or the launch returns False → restart `StartupWorker(skip_app_update=True)`. The app then starts normally, as today, and the banner can still offer the update later.
- The `StartupWorker` constructor gets one optional argument, `skip_app_update: bool = False`. `_on_retry` keeps working unchanged.

The yt-dlp step and everything after it are unchanged.

### Task 4.2: Failing tests in `tests/test_splash_update.py`
Mock `check_internet`, `check_for_update`, `missing_tools`, `update_ytdlp`, `create_desktop_shortcut`, `load_settings` / `save_settings`, `UpdateDownloadWorker`, `launch_silent_installer`, and `QApplication.quit`. Set `sys.frozen` with monkeypatch.

| Test | Expected |
|---|---|
| `test_source_run_never_checks_app_update` | not frozen → `check_for_update` not called; tools step runs |
| `test_auto_update_off_skips` | `auto_update=False` → not called |
| `test_offline_skips_update_check` | offline → not called; behaviour as today |
| `test_no_update_continues_to_tools` | status `none` → `update_ytdlp` path runs, `finished` emitted, `last_app_check` saved |
| `test_update_found_stops_before_tools` | `available` → `update_found` emitted; `missing_tools` / `update_ytdlp` **not** called |
| `test_required_update_also_installs` | `required` → same as available |
| `test_download_progress_shown_on_splash` | progress 45 → bar 45, text `Downloading update 1.0.3… 45%` |
| `test_download_success_launches_and_quits` | `launch_silent_installer` called with the path; `update_attempt_version` saved; `quit` called |
| `test_download_failure_starts_normally` | the worker is restarted with `skip_app_update=True`; `startup_completed` is still reached |
| `test_launch_failure_starts_normally` | same as above |
| `test_loop_guard_skips_same_version` | `update_attempt_version == "1.0.3"`, `APP_VERSION == "1.0.2"`, manifest 1.0.3 → no download |
| `test_retry_button_unchanged` | the offline first-run path still shows Retry |

### Task 4.3: Run
```
pytest tests/test_splash_update.py -q
pytest -q
```
**Phase 4 gate:** green (R9 only). **Send the owner one summary and ask for a yes to Phase 5 (R10).**

---

## Phase 5: First Real Release v1.0.3 (only after the owner says yes)

Prerequisites: Phase 0 done (`gh` logged in; work merged to `main`; on `main`).

1. `python tools/release.py --dry-run` → check the output.
2. `python tools/release.py 1.0.3 --notes "Exact download size" --notes "App updates itself on start"`
3. Check:
   - The GitHub Releases page shows `v1.0.3` with `YOuTUbE_Setup.exe`.
   - The raw `version.json` shows `1.0.3` and the matching `sha256`.
   - The script printed "Live".
4. Install 1.0.3 on the owner's PC by running `Output\YOuTUbE_Setup.exe`, so the PC has the new startup updater.

**Phase 5 gate:** release live, 1.0.3 installed. Ask for a yes to Phase 6.

---

## Phase 6: End-to-End Test + Final Check (only after the owner says yes)

### Task 6.1: Real auto-update (the main proof)
1. Release `1.0.4` with a small visible change: the release notes, plus the version number shown in the app (the version bump is enough).
2. Wait for "Live". Close the app.
3. Double-click the **desktop shortcut** (1.0.3 installed).

| # | Pass when |
|---|---|
| 1 | Splash shows `Checking for app update…`, then `Downloading update 1.0.4… n%` with the bar moving |
| 2 | `Installing update…`, the app closes, the installer runs silently (no wizard clicks) |
| 3 | The app **reopens by itself** (Phase 3 fix), and the splash then shows the normal tool check |
| 4 | Installed version is 1.0.4: `YOuTUbE.exe` → Properties → Details, or the app log line |
| 5 | Open the app again → no update download (already latest), starts as fast as before |
| 6 | Wi-Fi off → open the app → starts normally, no update error, no delay over about 5 s |
| 7 | Settings → turn "Check for updates automatically" off → open the app → no update check |
| 8 | Downloads still work (one video, one audio) |

### Task 6.2: Final automated checks
```
pytest -q
git status --porcelain
git diff --stat main~N   (only allowed files)
```

### Task 6.3: Result note
`docs/verification/release_update_result.md`: baseline and final test counts, dry-run output, release URLs for 1.0.3 and 1.0.4, the Task 6.1 table (pass or fail per row), and known limits.

**Phase 6 gate:** one final summary to the owner.

---

## How the Owner Uses It Afterwards

```
1. Change code, test with the Dev shortcut or python -m app.main
2. Commit and merge to main
3. python tools/release.py --notes "What changed"      (auto patch bump)
4. Open the desktop app → it updates itself
```
Every user's installed app does the same on its next start.

---

## Known Limits

- GitHub's raw cache can delay a new release by up to about 5 minutes (F4).
- A release needs internet, `gh` login, and the `main` branch.
- Users on old versions without this plan (≤ 1.0.2) still get the update through the existing banner (once the release exists, F1). From 1.0.3 on, it happens on the startup screen.
- No code signing certificate, so Windows SmartScreen may warn on the **first manual** install. Silent updates run from the app.

## Out of Scope (do NOT do)

- Changing `app_updater.py`, `main_window.py`, the banner, `tool_manager.py`, or the yt-dlp update timing.
- Delta or partial updates, update channels, rollback UI, or code signing.
- GitHub Actions or CI release pipelines (the local script only).
- Android releases (the `android` block in `version.json` is copied unchanged).
- Any change to the splash look (size, colors, fonts, logo).
