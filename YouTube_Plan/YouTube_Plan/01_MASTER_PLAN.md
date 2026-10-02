# 01 — Master Plan

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

A Windows desktop app (`Setup.exe`) that downloads YouTube video or audio in the best quality, with a calm minimalist UI, live progress, history, a one-file installer that sets everything up, an automatic desktop shortcut, and automatic updates. An optional Android app follows after Windows ships.

## 1. Goals

| # | Goal |
|---|---|
| 1 | User pastes a link. **No terminal is ever visible** (see `00_AGENT_BRIEF.md`) |
| 2 | Video tab downloads **best quality (up to 4K+) with audio merged** by default |
| 3 | Quality dropdown is built from what the video really offers (720p, 1080p, 2K, 4K, 8K, future ones) |
| 4 | Audio tab downloads **best original audio** by default, plus MP3, M4A, Opus, WAV, FLAC |
| 5 | Live progress: percent, speed, ETA, size, current stage |
| 6 | History (video and audio) with play, open folder, copy link, re-download, delete |
| 7 | Internet monitor: offline → lock the link box, tell the user once, history still works |
| 8 | **One installer** installs the app and downloads every needed tool automatically |
| 9 | **Desktop shortcut is created automatically** on first install/launch |
| 10 | **Auto-update** for the app, and for yt-dlp / ffmpeg / deno |
| 11 | Minimalist YouTube-matching design (red / near-black / white), no decorative effects |
| 12 | A real logo and icon (`assets/`) used by the window, shortcut, installer and uninstaller |
| 13 | Easy to share: a single `YouTube_Setup.exe` |

## 2. Name note (please read)

The app name is **YouTube**, as requested. "YouTube" and its logo are trademarks of Google. An app that uses that name can be flagged by antivirus vendors or hosting sites, rejected by stores, or draw a takedown, and users may think it is official. The logo in `assets/` is **original** (a red tile with a download arrow), not Google's play button. To make a rename painless, the name lives in **one constant** (`APP_NAME` in `app/version.py`) and one `#define` in `setup.iss`. Never hard-code the name anywhere else.

## 3. Tech stack

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Same language as yt-dlp, fast to build |
| GUI | PySide6 (Qt) | Tabs, lists, progress, threads |
| Download engine | `yt-dlp.exe` via `proc.py` (hidden) | Updatable without rebuilding |
| Merge / convert | `ffmpeg.exe` + `ffprobe.exe` | Merge video + audio, convert to MP3 etc. |
| JS runtime | `deno.exe` | Current yt-dlp needs an external JS runtime for full YouTube support. Check the yt-dlp wiki ("EJS" / JS runtime) for the current requirement before Phase 5 |
| History | SQLite (stdlib `sqlite3`) | One file, no dependency |
| HTTP / zip / hash | stdlib (`urllib`, `zipfile`, `hashlib`) | Keeps `requirements.txt` to PySide6 only |
| Packaging | PyInstaller `--onedir --noconsole` | Fast start, fewer antivirus alarms |
| Installer | Inno Setup 6.1+ (built-in download page) | No extra plugin needed |
| Updates | GitHub Releases + `version.json` | Free, simple |
| Signing | Code-signing certificate (optional, strongly advised) | Avoids SmartScreen warnings |

## 4. Project layout (source)

```
youtube/
 ├─ assets/
 │   ├─ logo.svg  logo_512.png  icon.ico        # supplied with this plan
 ├─ app/
 │   ├─ main.py                  # entry point
 │   ├─ version.py               # APP_NAME, APP_VERSION, UPDATE_MANIFEST_URL
 │   ├─ tools.json               # pinned tool URLs (+ checksums where available)
 │   ├─ ui/
 │   │   ├─ theme.py             # colour tokens + builds the stylesheet (dark/light)
 │   │   ├─ main_window.py
 │   │   ├─ splash.py
 │   │   ├─ video_tab.py
 │   │   ├─ audio_tab.py
 │   │   ├─ history_tab.py
 │   │   └─ settings_dialog.py
 │   └─ core/
 │       ├─ proc.py              # THE ONLY place that starts external programs (hidden)
 │       ├─ paths.py             # every folder/file path
 │       ├─ settings.py          # settings.json read/write
 │       ├─ logger.py            # logs\app.log
 │       ├─ url_tools.py         # validate + clean links
 │       ├─ info_fetcher.py      # yt-dlp -J → quality list
 │       ├─ downloader.py        # command builder, progress parser, worker
 │       ├─ errors.py            # raw yt-dlp error → plain sentence
 │       ├─ history_db.py        # SQLite
 │       ├─ tool_manager.py      # install/update yt-dlp, ffmpeg, deno
 │       ├─ shortcut.py          # desktop shortcut (first run, once)
 │       ├─ network_monitor.py   # online/offline watcher
 │       └─ app_updater.py       # updates the app itself
 ├─ installer/setup.iss
 ├─ build/build_exe.bat  build_installer.bat
 ├─ tests/                       # pytest, pure-logic tests only
 ├─ requirements.txt             # PySide6
 ├─ requirements-dev.txt         # pytest, pyinstaller
 └─ README.md
```

Only create a file when its chunk says so.

## 5. Layout on the user's PC

```
%LOCALAPPDATA%\Programs\YouTube\        app files (installer / updater replace these)
   YouTube.exe  _internal\...
%APPDATA%\YouTube\                      data + tools (never wiped by updates)
   bin\  yt-dlp.exe  ffmpeg.exe  ffprobe.exe  deno.exe
   history.db  thumbnails\  settings.json  logs\app.log
%USERPROFILE%\Downloads\                default save folder (changeable)
Desktop\YouTube.lnk                     created automatically
```

## 6. Phases

| Phase | File | Work | Rough time |
|---|---|---|---|
| 1 | `PHASE_01_Foundation_and_Brand.md` | Skeleton, paths, settings, logger, theme, empty window | 2 to 3 days |
| 2 | `PHASE_02_Download_Engine.md` | Hidden runner, URL cleaning, command builder, progress, cancel | 3 to 4 days |
| 3 | `PHASE_03_Video_and_Audio_Tabs.md` | Info fetch, dynamic quality list, both tabs | 3 to 4 days |
| 4 | `PHASE_04_History.md` | SQLite history, list, filter, actions | 2 to 3 days |
| 5 | `PHASE_05_Tools_Splash_FirstRun.md` | Tool manager, updates, splash, **desktop shortcut**, first-run | 4 to 5 days |
| 6 | `PHASE_06_Network_Monitor.md` | Online/offline watcher, lock, one-time popup | 1 to 2 days |
| 7 | `PHASE_07_App_Updater.md` | `version.json`, download, SHA-256, silent install | 3 to 4 days |
| 8 | `PHASE_08_Polish_Errors_Settings.md` | Error messages, settings, queue, notifications | 3 to 4 days |
| 9 | `PHASE_09_Packaging_and_Installer.md` | PyInstaller, Inno Setup with tool download + shortcut | 3 to 4 days |
| 10 | `PHASE_10_Testing_and_Release.md` | Clean-PC tests, update test, release | 3 to 4 days |
| 11 | `PHASE_11_Android_Optional.md` | Separate Android app | 3 to 5 weeks |

Phases run in order. Each phase is split into **chunks**; each chunk ends with a **Verify** list; each phase ends with a **Phase verification**.

## 7. Changes from the earlier plan

- `styles.qss` → `ui/theme.py` (one token table builds dark and light, no duplicate files).
- Added `core/proc.py` (single hidden-process helper), `settings.py`, `logger.py`, `url_tools.py`, `errors.py`, `shortcut.py`.
- Installer uses Inno's **built-in** download page instead of the Inno Download Plugin.
- Fixed the earlier Inno sketch: Inno does not allow `; comment` after a value on the same line.
- Playlist support and clipboard watcher moved to the backlog (not in v1.0).

## 8. Risks

1. **YouTube changes often.** yt-dlp stays separate and auto-updates.
2. **Antivirus false positives** on PyInstaller apps. Use `--onedir`, sign the files, report false positives to vendors.
3. **Terms of service / copyright.** Downloading can violate YouTube's terms, and saving copyrighted content without permission may be illegal where you live. Keep it for content you have the right to save, and think before distributing it widely.
4. **Store policies.** Google Play and Microsoft Store do not accept this kind of app. Share by direct download.
5. **Keep signing keys safe** (code-signing certificate, Android keystore). Losing them breaks the update path.
6. **Name/trademark** — see Section 2.
