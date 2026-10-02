# Phase 2 — Download Engine

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** paste a link, press Download, and watch a real download run with percent, speed, ETA and stage, with **no terminal**, and with Cancel working.
**Reads first:** `00_AGENT_BRIEF.md` (especially "no terminal"), `02_DESIGN_SYSTEM.md`.

**Dev setup (one time, not part of the app):** until Phase 5 exists, put `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` and `deno.exe` by hand into `%APPDATA%\YouTube\bin\`.

---

## Chunk 2.1 — The hidden process helper

**Files you may touch (new):** `app/core/proc.py`, `tests/test_proc.py`.

**Do**
- The **only** module that imports `subprocess`.
- `start_hidden(cmd)` returns a `Popen` with `creationflags=CREATE_NO_WINDOW (0x08000000)`, `stdin=DEVNULL`, `stdout=PIPE`, `stderr=STDOUT`, `text=True`, `encoding="utf-8"`, `errors="replace"`, and a `STARTUPINFO` with `SW_HIDE`.
- `run_hidden(cmd, timeout)` returns `(exit_code, output)`.
- `kill_tree(proc)` ends the process **and its children** (ffmpeg is a child of yt-dlp).

**Verify**
- [ ] Test runs `python -c "print('hi')"` through `run_hidden` and gets `hi`.
- [ ] Running the test from a double-clicked `.pyw` shows no flashing window.
- [ ] `grep -rn "subprocess" app/` hits only `proc.py`.

## Chunk 2.2 — Link validation and cleaning

**Files you may touch (new):** `app/core/url_tools.py`, `tests/test_url_tools.py`.

**Do**
- `is_youtube_url(text)`: accepts `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `m.youtube.com`, with or without `https://`.
- `clean_url(text)`: returns `https://www.youtube.com/watch?v=<ID>` and drops `list`, `t`, `start_radio`, `index` and tracking parameters.

**Verify** (all as unit tests)
- [ ] `...watch?v=ID&list=XYZ&t=30s` → `...watch?v=ID`.
- [ ] `https://youtu.be/ID?si=abc` → `...watch?v=ID`.
- [ ] A Shorts link → a clean watch link.
- [ ] `hello`, empty string, and a non-YouTube site → rejected.

## Chunk 2.3 — Command builder and progress parser

**Files you may touch (new):** `app/core/downloader.py` (pure functions only in this chunk), `tests/test_downloader.py`.

**Do**
- `build_video_cmd(url, height=None, container="mkv", out_dir)` and `build_audio_cmd(url, fmt, out_dir)` using the format strings from the table below.
- Always include `--no-playlist --newline --ffmpeg-location <BIN_DIR> -P <out_dir>` and the progress template that prints `download:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s`.
- `parse_line(line)` returns a small object: progress values, or a stage (`[Merger]` → Merging, `[ExtractAudio]` → Converting audio), or nothing.

| Choice | Format / flags |
|---|---|
| Video, best | `-f "bv*+ba/b" --merge-output-format mkv` |
| Video, height H | `-f "bv*[height<=H]+ba/b[height<=H]"` |
| Audio, best original | `-f ba -x` |
| Audio MP3 / M4A | `-f ba -x --audio-format <fmt> --audio-quality 0` |
| Audio Opus / WAV / FLAC | `-f ba -x --audio-format <fmt>` |

**Verify**
- [ ] Unit tests cover each row of the table (the produced list contains the expected flags).
- [ ] Parser tests: a progress line, a `[Merger]` line, an `[ExtractAudio]` line, and a garbage line (ignored, no crash).
- [ ] No Qt import in this file.

## Chunk 2.4 — Download worker (thread, signals, stages, cancel)

**Files you may touch:** `app/core/downloader.py` (add the worker class).

**Do**
- `DownloadWorker(QThread)` with signals: `stage(str)`, `progress(overall_percent, speed, eta, done_bytes, total_bytes)`, `finished(file_path)`, `failed(raw_text)`.
- Stages: Fetching info → Downloading video → Downloading audio → Merging → Done.
- **Overall percent:** weight video and audio by size so the bar never jumps back to 0; merging is the last small slice.
- Read stdout line by line, feed `parse_line`, write every raw line to the log.
- `cancel()` calls `kill_tree`, then deletes leftover `*.part` and `*.ytdl` files that belong to this download.
- Final file path is read from yt-dlp (`--print after_move:filepath`), not guessed.

**Verify**
- [ ] A real 1-minute video downloads; stage labels change in the right order.
- [ ] The percent never goes backwards during a video+audio download.
- [ ] Cancel at ~30%: the process disappears from Task Manager within 2 seconds and no `.part` file is left.
- [ ] The window stays responsive (drag it) during the whole download.

## Chunk 2.5 — Minimal wiring

**Files you may touch:** `app/ui/main_window.py`, `app/ui/video_tab.py` (new).

**Do**
- Video tab: link box, Download button, Cancel button, stage label, progress bar, one line for speed/ETA/size, exactly as the layout in `02_DESIGN_SYSTEM.md`.
- Download button turns into disabled while running; Cancel enabled only while running.
- Bad link → inline message "Please paste a valid YouTube link."

**Verify**
- [ ] Paste a link, press Download, file appears in Downloads with sound.
- [ ] No black window appears at any moment (record the screen and scrub through).
- [ ] Invalid text shows the message and starts nothing.

---

## Phase 2 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] One full 4K-capable video downloads, merges and plays with audio.
- [ ] `grep -rn "subprocess\|os.system\|print(" app/` → only `proc.py`.
- [ ] Task Manager during a download shows `yt-dlp.exe` / `ffmpeg.exe` as background processes, with no console host windows.
- [ ] Only files from the chunk lists changed. User said "go on".
