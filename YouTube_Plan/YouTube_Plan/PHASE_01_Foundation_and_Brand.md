# Phase 1 — Foundation and Brand

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** a project skeleton that opens an empty, correctly styled window with the logo, with no console, and with the paths, settings and logging every later phase relies on.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

---

## Chunk 1.1 — Skeleton and constants

**Files you may touch (new):** `requirements.txt`, `requirements-dev.txt`, `README.md`, `app/main.py`, `app/version.py`, `assets/` (copy the supplied logo files in), empty `app/ui/` and `app/core/` packages (`__init__.py` only).

**Do**
- `requirements.txt`: `PySide6` only. `requirements-dev.txt`: `pytest`, `pyinstaller`.
- `version.py`: `APP_NAME = "YouTube"`, `APP_VERSION = "1.0.0"`, `UPDATE_MANIFEST_URL = ""` (filled in Phase 7).
- `main.py`: create `QApplication`, set app name, exit cleanly. No window yet.

**Do not:** add any other constant, helper or package.

**Verify**
- [ ] `pip install -r requirements.txt` succeeds in a fresh virtual environment.
- [ ] `python -m app.main` starts and exits with no error.
- [ ] Logo files exist in `assets/` and open correctly.

## Chunk 1.2 — Paths, settings, logger

**Files you may touch (new):** `app/core/paths.py`, `app/core/settings.py`, `app/core/logger.py`, `tests/test_settings.py`.

**Do**
- `paths.py`: one function/constant per path in the layout (`APP_DATA`, `BIN_DIR`, `HISTORY_DB`, `THUMBS_DIR`, `SETTINGS_FILE`, `LOG_FILE`, `DEFAULT_DOWNLOADS`). Create folders on first use. Use `APP_NAME` from `version.py` for the folder name.
- `settings.py`: load/save `settings.json` with defaults: `download_dir`, `theme: "dark"`, `container: "mkv"`, `auto_update: true`, `shortcut_created: false`, `last_tool_check: 0`, `last_app_check: 0`. A missing or corrupt file falls back to defaults.
- `logger.py`: rotating file logger to `logs\app.log` (small size cap). Nothing printed to a console.

**Verify**
- [ ] Running the app creates `%APPDATA%\YouTube\` with `logs\app.log`.
- [ ] Deleting `settings.json` → defaults come back, no crash.
- [ ] A corrupt `settings.json` (type garbage) → defaults come back, a line appears in the log.
- [ ] `pytest tests/test_settings.py` passes.

## Chunk 1.3 — Theme

**Files you may touch (new):** `app/ui/theme.py`.

**Do**
- One dictionary of colour tokens for dark and one for light, exactly as in `02_DESIGN_SYSTEM.md`.
- One function `build_qss(theme_name)` returning the stylesheet for: window, tabs, line edit, combo box, buttons (primary/secondary via a `role` property), progress bar, list rows, scroll bars, message boxes.
- Set the font to Segoe UI 13.

**Do not:** add shadows, gradients, hover animations or any colour not in the table.

**Verify**
- [ ] `build_qss("dark")` and `build_qss("light")` both return a non-empty string and contain no hex colour outside the token table (a test greps for this).
- [ ] No gradient, shadow or `border-image` keyword appears in the output.

## Chunk 1.4 — Empty main window

**Files you may touch:** `app/ui/main_window.py` (new), `app/main.py` (edit).

**Do**
- Window 760×560, min 640×480, title = `APP_NAME`, icon = `assets/icon.ico`.
- Three tabs: Video, Audio, History, each containing only a placeholder label.
- Top-right status area with a static "Online" dot (real logic comes in Phase 6).
- Apply the theme from settings.

**Verify**
- [ ] Window opens in dark theme; switching `theme` to `"light"` in `settings.json` and reopening shows the light theme.
- [ ] Red appears **only** on the active tab underline (compare with the red-only rule).
- [ ] Taskbar and title bar show the logo.
- [ ] Resizing below 640×480 is blocked.
- [ ] Launching via `pythonw -m app.main` shows **no console window**.

---

## Phase 1 verification (all must pass)

- [ ] Every chunk's Verify list above is fully checked.
- [ ] `grep -rn "print(" app/` returns nothing.
- [ ] Screenshot of the window matches `02_DESIGN_SYSTEM.md` (user confirms by eye).
- [ ] No file outside the lists above was changed (`git status` shows only expected files).
- [ ] Report sent in the format from `00_AGENT_BRIEF.md`, and the user said "go on".
