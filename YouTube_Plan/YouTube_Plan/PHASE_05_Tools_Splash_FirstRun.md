# Phase 5 — Tools, Splash and First Run (includes the desktop shortcut)

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** the app installs and updates its own tools safely, starts with a quiet splash, creates the desktop shortcut automatically the first time, and handles "no internet on first launch" gracefully.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`. Check the yt-dlp wiki for the current JS-runtime requirement before Chunk 5.1.

---

## Chunk 5.1 — Tool list and installer

**Files you may touch (new):** `app/tools.json`, `app/core/tool_manager.py`, `tests/test_tool_manager.py`.

**Do**
- `tools.json` pins, per tool, a download URL and file type: yt-dlp (`yt-dlp.exe`, from the yt-dlp GitHub "latest" release), ffmpeg + ffprobe (a Windows zip build; prefer an **LGPL** build), deno (Windows zip from the deno GitHub release). **Open every URL once and confirm it downloads before pinning it.**
- `tool_manager.py`: `missing_tools()`, `install_tool(name, progress_cb)` (download to a `.new` temp file in `bin\`, unzip with `zipfile`, move into place). Runs in a worker thread. Uses `urllib`.
- After install, each tool is checked by running `--version` through `proc.py`.

**Verify**
- [ ] With an empty `bin\`, `missing_tools()` lists all four.
- [ ] `install_tool` for each tool leaves a working file; `--version` prints a version.
- [ ] An interrupted download (kill the network) leaves no half file in `bin\`.
- [ ] Unit test: the missing/present logic with a temp folder.

## Chunk 5.2 — Safe updates, rollback, auto-repair

**Files you may touch:** `app/core/tool_manager.py`, `app/core/downloader.py` (only the retry hook), `app/core/settings.py` (uses existing keys).

**Do**
- yt-dlp: check at launch and then every 24 h (`last_tool_check`). Compare `--version` with the latest GitHub release tag.
- Update steps: download `yt-dlp.exe.new` → run `--version` on it → keep the old as `yt-dlp.exe.bak` → replace. If `--version` fails, delete `.new`, keep the old, log it.
- ffmpeg and deno: check about once a month.
- **Auto-repair:** when a download fails with an extraction error, update yt-dlp once and retry once. Never loop.
- A failed update never blocks the app; it only logs and shows a small muted line.

**Verify**
- [ ] Replace `yt-dlp.exe` with an old release → app updates it and the old one stays as `.bak`.
- [ ] Put a corrupt file as the "new" version → rollback keeps the working one.
- [ ] Simulated extraction error triggers exactly one update + one retry.
- [ ] Update runs without freezing the window and without a terminal.

## Chunk 5.3 — Splash and startup flow

**Files you may touch (new):** `app/ui/splash.py`; edit `app/main.py`.

**Do**
- Splash: logo (96 px) centred on `bg`, app name, one muted status line, thin progress bar. Fades in/out in 150 ms. No other effects.
- Startup order (all off the UI thread): internet check (`youtube.com:443`, 3 s) → tools check/install → tool update check (24 h) → open the main window.
- The splash status line says plain things: "Checking tools…", "Downloading components…", "Starting…".

**Verify**
- [ ] Normal start with tools present reaches the main window in under ~3 s.
- [ ] Deleting `bin\` and starting again: splash shows download progress, then the app opens ready to use.
- [ ] The splash looks like the design file (no glow, no gradient, no emoji).

## Chunk 5.4 — Automatic desktop shortcut (first run, once)

**Files you may touch (new):** `app/core/shortcut.py`, `tests/test_shortcut.py`; edit `app/main.py`.

**Do**
- On launch, if `settings.shortcut_created` is `false` **and** no shortcut exists, create `YouTube.lnk` on the user's Desktop, pointing to the running `YouTube.exe`, with `assets/icon.ico` as the icon. Then set `shortcut_created = true`.
- Find the Desktop with `[Environment]::GetFolderPath('Desktop')`, because the Desktop may be redirected (OneDrive).
- Create the `.lnk` with `WScript.Shell` through PowerShell, started **only** via `proc.py` with `-NoProfile -NonInteractive -WindowStyle Hidden`.
- Run only once. If the user deletes the shortcut later, the app does **not** bring it back (the flag stays `true`).
- Also skip when running from source (not frozen), so development never litters the Desktop.
- This is a fallback/safety net. The installer (Phase 9) also creates the shortcut; if it already exists, do nothing and just set the flag.

**Verify**
- [ ] Fresh settings + frozen build (or a forced test flag): shortcut appears on the Desktop with the red logo icon and launches the app.
- [ ] Second launch: no second shortcut, no duplicate.
- [ ] Delete the shortcut, launch again: it is **not** recreated.
- [ ] Desktop redirected to OneDrive: shortcut still lands on the real Desktop.
- [ ] No PowerShell window flashes at any point.

## Chunk 5.5 — First launch without internet

**Files you may touch:** `app/main.py`, `app/ui/splash.py`.

**Do**
- Offline + tools missing: show "Internet is required for first-time setup." and a **Retry** button. Retry re-runs the check. The History tab is still reachable.
- Offline + tools present: open normally, skip updates.

**Verify**
- [ ] Offline first launch shows the message and Retry; History opens.
- [ ] Turning the internet on and pressing Retry downloads the tools and opens the app, with no restart.
- [ ] Offline with tools present opens the main window with no error.

---

## Phase 5 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] On a fresh Windows user profile (or clean VM): first launch downloads tools, creates the shortcut, and a first download succeeds.
- [ ] Broken yt-dlp update rolls back; the app keeps working.
- [ ] No terminal, no PowerShell flash, during the whole flow (screen recording checked).
- [ ] Only files from the chunk lists changed. User said "go on".
