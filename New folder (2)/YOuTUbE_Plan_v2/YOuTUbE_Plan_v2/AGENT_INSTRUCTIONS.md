# Agent Instructions: Read This First

You are improving **YOuTUbE**, an existing Windows desktop app (Python 3.11 + PySide6) that downloads YouTube video and audio with yt-dlp. The code already exists. Your job is to fix verified bugs, redesign screens as specified, and ship. Read this file, then `00_MASTER_PLAN.md`, then the phase file you are about to work on.

---

## 1. Understand the product

A person installs one `Setup.exe`. A desktop shortcut appears. They paste a link, press Download, see a smooth progress bar with speed and ETA, and the finished item appears under "Recently downloaded" and in History. They never see a terminal, never install tools by hand, never update by hand.

### Screen behaviour (the contract)

**Video and Audio tabs**
1. **Idle (no link):** link box and Fetch. The quality/format dropdown is disabled. Only the **Download** button is visible, and it is disabled until a valid link is fetched. Entering Download with an empty or invalid link shows a friendly error that auto-hides after 4 seconds.
2. **After fetch:** the info card (thumbnail, title, channel, duration) appears. The dropdown unlocks with real options only (Video: Best available plus real resolutions. Audio: Best original, MP3, M4A, Opus, WAV, FLAC).
3. **Downloading:** the Download button is locked. **Add to queue** and **Cancel** appear. A progress card shows stage, percent, speed, ETA and size. The small thumbnail and title stay above it.
4. **Done:** the link box clears, the info card and progress card hide, a toast appears, and the item shows under **Recently downloaded** (last 5 of that tab's type, no search or filters).
5. **Queue:** one shared queue for both tabs, one download at a time. Hidden when empty.

**History tab:** filter chips (All, Video, Audio), search box, rows with thumbnail, title, type, quality, size, date, and icon actions (Play, Open folder, Copy link, Re-download, Delete). A row never depends on its file existing.

**Settings:** popup. Download folder (read-only box, Browse, small Save appears when the path changed), Appearance, Updates (custom checkbox, Check now), About. No bottom Save/Cancel.

### yt-dlp facts you must respect (verified)

- `--print` makes yt-dlp **quiet**: no progress, no stage lines. Do not use `--print` for paths.
- In `--progress-template "download:TEMPLATE"`, `download:` is a **type selector** and is not printed. Put your own marker in the template (for example `YTPROG|`) and parse for that marker.
- Piped stdout on Windows uses the system code page and **drops non-ASCII characters**. Never trust stdout for file paths. Use `--print-to-file after_move:filepath <utf8 file>`.
- Progress and post-process templates can read fields with `%(info.vcodec)s`, `%(progress.downloaded_bytes)s`, `%(progress.total_bytes)s`, `%(progress.postprocessor)s`.

---

## 2. Hard rules

1. **No terminal, ever.** Start processes only through `core/proc.py`. No `shell=True`, no `os.system`, no PowerShell/cmd windows. Build with `--noconsole`.
2. Never block the UI thread. Use workers and signals.
3. Never delete files by pattern in the user's Downloads folder. Use an app-owned temp folder (`-P temp:<appdata>\tmp`) and delete only that.
4. Build a history row from an immutable **DownloadJob snapshot**, never from live widgets.
5. History must survive deleted or moved files, app updates and tool updates.
6. **Do not change colours.** Use `theme.py` tokens and add only hover/pressed shades.
7. One download at a time from the shared queue.
8. No silent `except: pass`. Log to `app.log` and show a friendly message where the user is affected.
9. Tests use real yt-dlp output (contract tests with a local file server and the generic extractor), not invented output lines.
10. Do not skip verification gates.

---

## 3. Design specification

- Keep the current red and black look. Read the colour tokens in `app/ui/theme.py` and reuse them.
- Minimalist and satisfying: every clickable thing reacts (hover, press, success). Subtle and fast, 120 to 200 ms. No heavy effects.
- **Buttons:** one system. Primary (red fill), secondary (dark), ghost (text/icon only). Same heights. Press shrinks slightly. Loading state shows a small spinner. Success shows a tick for about 1 second.
- **Tabs:** sliding red underline, brighter active text.
- **Filter chips:** active chip filled red with a smooth colour transition.
- **Checkbox:** custom, rounded, red when checked, white tick, animated.
- **Progress card:** thicker rounded bar, soft glow, moving shine, text line `63% • 12.4 MB/s • ETA 01:20 • 1.2 / 1.9 GB`, stage name above.
- **Thumbnails:** rounded corners, always shown. If missing, re-fetch from `https://i.ytimg.com/vi/<id>/hqdefault.jpg`; last fallback is a neutral play/music icon, never a letter.
- **Text:** short, friendly, plain English. No jargon (no "yt-dlp", "stderr").
- **Layout:** content centred, max width about 1100 px. Minimum window size 760 × 520.
- **Title bar:** dark (Windows dark title bar attribute).

---

## 4. How to work

1. Read the whole phase file, including its Verification Gate, before coding.
2. Work **one chunk at a time**. After each chunk run its "done when" check.
3. Small commits: `phaseN.chunk: summary`.
4. Write tests with the code.
5. At the end of a phase run the full gate, including the no-terminal check, and save evidence in `docs/verification/phase_N.md`.
6. If anything fails, fix it and rerun the **whole** gate.

### Report after each chunk
```
Chunk N.X: <name>
Done: <what changed>
Checked: <how verified>
Next: <next chunk>
Problems: <none or list>
```

### Report after each phase
```
Phase N complete
Gate: <automated pass/fail, manual list>
No-terminal check: PASS
Evidence: docs/verification/phase_N.md
Known issues: <none or list>
```

---

## 5. Do not

- Add features that are not in the plan without asking.
- Hard-code user paths such as `C:\Users\Jay`.
- Use `time.sleep` in the UI thread or touch widgets from worker threads.
- Mark a phase done because "it looks fine".
- Imitate any existing brand's logo.

---

## 6. Test approach (important)

Contract tests run the real `yt-dlp` against a local HTTP file server (`python -m http.server`) with a generated `.mp4`. Assert on the real output: progress lines parse, the path file exists, filenames with `｜ ： ⧸ é 日本語 😀` resolve to a real file with the correct size. Also simulate the Windows code page with `PYTHONIOENCODING=cp1252` to prove the path logic does not depend on stdout.
