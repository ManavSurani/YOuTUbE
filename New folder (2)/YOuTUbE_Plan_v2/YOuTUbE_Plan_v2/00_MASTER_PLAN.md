# YOuTUbE v2: Fix, Redesign and Ship (Master Plan)

> Read `AGENT_INSTRUCTIONS.md` first, then this file, then the phase files in order.
> Repo reviewed: `github.com/ManavSurani/YOuTUbE` (Python + PySide6 app, Android scaffold, installer script, tests).

---

## 1. Where the project stands

The repo already contains: splash screen, tool manager (yt-dlp / ffmpeg / deno download), app updater, desktop shortcut module, network monitor, queue, history database, settings dialog, Inno Setup script, tests, and an Android scaffold. This plan does **not** rebuild those. It fixes the real bugs found in the code audit, redesigns the screens you described, and then hardens install, update and release.

Files reviewed for this plan: `core/downloader.py`, `core/proc.py`, `core/history_db.py`, `ui/video_tab.py`, `ui/audio_tab.py`, `ui/history_tab.py`, `ui/settings_dialog.py`, `ui/main_window.py` (header/tabs), `ui/theme.py` (checkbox rules). Other modules (splash, tool_manager, app_updater, shortcut, installer, Android) exist but were **not** audited; Phase 7 does that.

---

## 2. Code audit: verified problems

"Verified" means I reproduced it by running yt-dlp locally against a test file. "Confirmed in code" means it is visible in the source. "Likely" means it fits the evidence and must be confirmed on a real Windows PC in the phase named.

| ID | Problem | Evidence | Fixed in |
|---|---|---|---|
| B1 | **Live progress and stage names never work.** `--print` makes yt-dlp quiet, so it prints no progress lines at all, only the final path. The bar sits at 0% and jumps to 100%. | Verified | Phase 1 |
| B2 | **Progress parser can never match.** In `PROGRESS_TEMPLATE`, `download:` is yt-dlp's template *type selector*, not printed text, so output lines never start with `download:`. Unit tests pass only because they feed fake `download:` lines. | Verified | Phase 1 |
| B3 | **"File missing" and "0 B" for titles with special characters** (`\|`, `:`, `/`). yt-dlp writes the real file with look-alike characters, but when its output is piped on Windows it prints the path in the system code page and drops those characters. The path stored in history then does not exist. Plain-ASCII titles (the Starboy audio) work, which matches your screenshots. | Verified by simulation; confirm on your PC | Phase 1 |
| B4 | **Cancel deletes other programs' files.** `cleanup_temp_files()` removes every `*.part`, `*.ytdl`, `*.temp` in the whole Downloads folder (Firefox uses `.part`). | Confirmed in code | Phase 1 |
| B5 | **History row is built from live widgets at finish time**: URL, video id and thumbnail are read from the link box and info card. After "Add to queue" clears them, the row gets a blank or wrong URL, a missing or wrong thumbnail, and `title = url` when info was not ready. | Confirmed in code | Phase 2 |
| B6 | **Thumbnails vanish.** One thumbnail file per video id (`thumbs/<id>.jpg`); deleting any history row deletes it for every other row of the same video (for example the video and the MP3 of one link). The row then shows the "V" or "A" letter. | Confirmed in code | Phase 2 |
| B7 | **Failures are invisible.** History saving and file deletion are wrapped in `except Exception: pass`. "Also delete the file" can fail (file open in a player) with no message. | Confirmed in code | Phase 2, 5 |
| B8 | **Video and Audio have separate queues**, each with its own worker, so two downloads can run at once. History has no duration (`duration=0`). | Confirmed in code | Phase 4 |
| B9 | **Quality dropdown and Download button are usable with no link.** Going back online re-enables them even with nothing fetched. Errors never auto-hide. | Confirmed in code | Phase 4 |
| B10 | **Settings button is clipped.** It is a 28 px button inside the tab widget's corner area, which is shorter than the button. | Confirmed in code | Phase 3 |
| B11 | **Checkboxes look unchecked even when checked.** The checked style fills the box white with no tick. Both audio checkboxes and "Check for updates automatically" are actually **ON** (earlier notes said unchecked; that was wrong). | Confirmed in code | Phase 3 |
| B12 | **Search box shows a text cursor** when History opens (it takes default focus). | Confirmed in screenshots | Phase 5 |
| B13 | **"Duplicate Best available" is not a bug.** The popup shows one item. The real issue is B9. | Screenshots | n/a |
| B14 | Title bar is the Windows accent colour (blue-grey) instead of dark. | Screenshots | Phase 3 |
| B15 | Hard-coded "Saved to Downloads" even when a custom folder is set. Same video downloaded twice creates duplicate rows. | Confirmed in code | Phase 4, 5 |
| B16 | Tests do not catch B1 to B3 because they never run real yt-dlp output through the parser. | Confirmed | Phase 1 |

---

## 3. Decisions (defaults applied; change any before building)

| # | Decision | Default |
|---|---|---|
| D1 | Colours | **Keep current red and black.** Only add shades for hover/pressed states |
| D2 | Video container | Remove the setting. Always **MKV** (supports 4K/8K). Alternative: automatic MP4 up to 1080p |
| D3 | Audio cover art and metadata | Remove both checkboxes. Always embed title, artist and cover art when the format supports it. If embedding fails, the download still succeeds |
| D4 | Quality / format dropdown | Disabled until a link has been fetched. Shows real options only |
| D5 | Download button flow | Idle: only **Download**. Downloading: **Add to queue** and **Cancel** appear, Download is locked. Done: link and progress clear |
| D6 | During download | Small thumbnail and title stay above the progress card |
| D7 | Progress card | Thicker rounded red bar, soft glow, moving shine, line below: `63% • 12.4 MB/s • ETA 01:20 • 1.2 / 1.9 GB`, plus stage name |
| D8 | Recently downloaded | Last 5 items of that tab's type, with thumbnail, title, quality, size, Play, Open folder. No search or filters |
| D9 | Errors | Auto-hide after 4 seconds, cleared on tab switch, never reappear |
| D10 | Queue | **One shared queue**, one download at a time. Rows show thumbnail, title, type, status, remove. "Clear finished", Retry for failed. Waiting items survive restart. Hidden when empty |
| D11 | Already downloaded | Ask "Already downloaded. Download again?" |
| D12 | History vs files | History rows **never depend on the file**. Moved or deleted file shows "File missing" and a "Locate file" button. History data and thumbnails live in `%APPDATA%\YOuTUbE\history\` |
| D13 | Broken old rows | **Repair** where possible (find file, recompute size), leave the rest marked missing |
| D14 | Delete | Three options: delete file too (to **Recycle Bin**), remove from history only, cancel. Plus "Clear all history" with confirm |
| D15 | History row actions | Icon buttons with tooltips and hover/press animation. Delete turns red on hover |
| D16 | Active tab and filter | Sliding red underline for Video/Audio/History. Active filter chip filled red, smooth transition |
| D17 | Settings | Popup, no bottom Save/Cancel. Theme and update options apply instantly. Download folder: Browse, then a small Save button appears beside the path, then "Saved ✓". Path box is read-only with no cursor |
| D18 | Auto-update checkbox | ON by default. Custom red animated checkbox. "Check now" shows spinner, then result |
| D19 | Window | Dark title bar. Content centred at max width about 1100 px. Settings button fixed and given a gear icon |
| D20 | Animation | Subtle and fast (120 to 200 ms): hover glow, press shrink, success tick, spinners |
| D21 | Android | Last, optional (Phase 9) |
| D22 | Logo | Keep your current icon unless you choose to recolour the supplied logo in red and black |

---

## 4. Golden rules

| # | Rule |
|---|---|
| R1 | **No terminal, ever.** All processes start through `core/proc.py`. Build with `--noconsole`. No PowerShell or cmd windows. |
| R2 | The UI never freezes. Work runs in workers and reports through Qt signals. |
| R3 | Never trust yt-dlp's stdout for file paths or for anything with non-ASCII text. Use `--print-to-file` (UTF-8) and a file-system fallback. |
| R4 | The app only deletes files it created itself (temp folder inside app data), never by pattern in the user's Downloads. |
| R5 | A history row is built from an immutable **job snapshot** taken when the job is created, never from live widgets. |
| R6 | History survives everything: deleted files, moved files, app updates, tool updates. |
| R7 | Colours do not change (D1). Styling goes through `theme.py` tokens only. |
| R8 | One download at a time, from one shared queue. |
| R9 | No silent failures. Every `except` logs to `app.log`, and user-impacting failures show a friendly message. |
| R10 | Tests must use real yt-dlp output (contract tests against a local file server), not hand-written fake lines. |
| R11 | Every phase ends with a **Verification Gate**. The next phase does not start until it passes. |
| R12 | Shortcut is created once; a user who deletes it is not overridden. |

---

## 5. Phase map

| Phase | File | Goal |
|---|---|---|
| 1 | `PHASE_01_engine_truth.md` | Real progress, correct file paths, safe temp and cancel, contract tests |
| 2 | `PHASE_02_data_and_history_integrity.md` | Job snapshots, history service, thumbnail store, repair, safe delete |
| 3 | `PHASE_03_ui_kit_and_animation.md` | Header, title bar, buttons, checkboxes, tabs, chips, toasts, layout |
| 4 | `PHASE_04_video_audio_tabs_and_queue.md` | New flow, progress card, recently downloaded, shared queue |
| 5 | `PHASE_05_history_tab.md` | History redesign and behaviours |
| 6 | `PHASE_06_settings.md` | Settings redesign |
| 7 | `PHASE_07_install_shortcut_updates.md` | Audit and harden installer, shortcut, tools and app updates |
| 8 | `PHASE_08_qa_and_release.md` | Full test pass, clean-PC test, signing, release |
| 9 | `PHASE_09_android_optional.md` | Android app (optional) |

Order matters: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Phases 5 and 6 can swap.

---

## 6. Target changes to the code

```
app/core/
  downloader.py      (rewrite command builders + parser; use print-to-file)
  jobs.py            NEW: DownloadJob snapshot dataclass
  download_manager.py NEW: shared queue, one active job, persistence
  history_service.py NEW: save/repair/delete/relink on top of history_db
  thumbnails.py      NEW: permanent thumbnail store + re-fetch
  history_db.py      (schema version, migrations, no hard dependency on file)
app/ui/
  kit/               NEW: AnimatedButton, TabBar, Chip, Toggle, ProgressCard, Toast, ThumbLabel
  header.py          NEW: custom header (tabs, status, settings) replaces corner widget
```

---

## 7. Verification policy

Each phase file ends with a Verification Gate: automated checks, manual checks, a **no-terminal check**, and evidence saved in `docs/verification/phase_N.md`. If anything fails, fix it and rerun the **whole** gate. Each phase is divided into chunks (N.1, N.2, ...) with a "done when" line.

---

## 8. Definition of done

- [ ] Progress bar moves smoothly with speed, ETA and size, and stage names are correct.
- [ ] Every download, including titles with `|`, `:`, `/`, emoji and non-English text, ends with the correct file path and size in History.
- [ ] Deleting or moving files never removes History rows or thumbnails.
- [ ] Screens behave exactly as D4 to D20.
- [ ] Clean-PC install works, shortcut appears, updates work, no terminal ever visible.

---

## 9. Suggestions (included unless you remove them)

1. "Done" toast with an Open file button.
2. Enter to fetch and Ctrl+V auto-fetch.
3. Disk-space check before large downloads.
4. History database versioning plus automatic backup.
5. "Export log" button in Settings.
6. Clipboard watcher ("Paste copied link?"), off by default.
7. Playlists later (currently blocked with `--no-playlist`).

---

## 10. Notes and risks

1. YouTube changes often. Keep tools updatable.
2. Downloading from YouTube can violate its terms, and saving copyrighted content without permission may be illegal where you live. Keep use personal, and think carefully before distributing the app publicly.
3. A red icon with this name is close to a well-known brand. Fine for personal use; risky if distributed.
4. PyInstaller apps are often flagged by antivirus. Use `--onedir`, sign the files, test on a clean PC.
