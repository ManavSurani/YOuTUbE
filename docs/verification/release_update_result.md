# Plan 22 Result: One-Command Release + Update on App Start

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Baseline (Phase 0, app closed): **518 passed, 1 failed** (`test_check_scope.py::test_scope_checker_final`, known).
- After Phase 4: **552 passed, 2 failed**. The failures are the known scope test and `test_tab_looks.py::test_animated_combobox_click_fade_and_completion`, a timing flake that passed 6 out of 6 on its own and failed once in Plan 21 before any Plan 22 code existed.
- New tests: `tests/test_release_script.py` (20), `tests/test_splash_update.py` (15). No existing test was edited.

## Phase results
| Phase | Result |
|---|---|
| 1: script core | `bump`, `validate_new_version`, `set_version_py`, `set_setup_iss`, `build_manifest`, `installer_url`, `sha256_file`. The manifest is accepted by the real `check_manifest_dict`. |
| 2: flow + dry run | Order: preflight → tests → bump → build → commit/push → `gh release create` → download and verify hash → manifest commit/push → live check. Failures before the manifest step leave `version.json` untouched; a build failure restores the version files. |
| 3: relaunch | `installer/setup.iss` `[Run]`: `skipifsilent` removed (1 line). |
| 4: startup update | The splash checks for an app update after the internet check and before the tools. It downloads with progress on the splash, installs silently, then quits. Any failure starts the app normally. Skipped for source runs, with `auto_update` off, offline, or by the loop guard. |

## Found and fixed during the work
- `app/version.py` and `version.json` use CRLF line endings. The script now writes bytes and keeps each file's line-ending style, so only the version lines change in diffs.
- A missing `gh` crashed the script with `WinError 2`. It now reports "not installed" (a warning in dry run, a clear stop in a real release).

## Real dry run (`python tools/release.py --dry-run`)
```
WARNING (dry run): Releases are made from branch main, current branch is fix/ui-pass
WARNING (dry run): Working tree has uncommitted changes
WARNING (dry run): Local main is not the same as origin/main (pull or push first)
WARNING (dry run): GitHub CLI is not logged in (run: gh auth login)
Tests OK
DRY RUN: would release 1.0.3
  installer: Output\YOuTUbE_Setup.exe (36450644 bytes)
  url:       https://github.com/ManavSurani/YOuTUbE/releases/download/v1.0.3/YOuTUbE_Setup.exe
Nothing was changed, committed, pushed or uploaded.
```
`git status` and `git diff` were identical before and after.

## Scope (Plan 22 files)
```
tools/release.py               (new)
tests/test_release_script.py   (new)
tests/test_splash_update.py    (new)
app/ui/splash.py               | 71 +++++++-
installer/setup.iss            |  2 +-
```
`app_updater.py`, `main_window.py`, `tool_manager.py`, `version.py`, and `version.json`: 0 changes.

## Pending (needs the owner: Phase 0 setup + "yes", R10)
| Step | Status |
|---|---|
| `gh` installed and logged in | pending |
| Work committed and merged to `main` | pending |
| Phase 5: release v1.0.3, install on PC | pending |
| Phase 6: release v1.0.4, desktop shortcut auto-updates and reopens | pending |
