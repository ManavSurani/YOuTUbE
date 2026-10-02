# Phase 3 — Video and Audio Tabs

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** after pasting a link, the app shows title, thumbnail and a quality list built from the video's real data; the Audio tab offers the audio formats.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

---

## Chunk 3.1 — Info fetcher

**Files you may touch (new):** `app/core/info_fetcher.py`, `tests/test_info_fetcher.py`, `tests/sample_info.json` (a saved real `-J` result).

**Do**
- `fetch_info(url)` runs `yt-dlp -J --no-playlist <url>` through `proc.py` in a worker thread; returns title, channel, duration, thumbnail URL, and the raw format list.
- Timeout 30 s; on failure, pass the raw text up (errors become plain sentences in Phase 8).

**Verify**
- [ ] Real link returns title, channel and duration within ~10 s on a normal connection.
- [ ] Window stays responsive while fetching.
- [ ] Timeout case returns a failure instead of hanging.

## Chunk 3.2 — Quality list builder

**Files you may touch:** `app/core/info_fetcher.py`, `tests/test_info_fetcher.py`.

**Do**
- `build_quality_list(formats)`: collect distinct `height` values from video formats, sort high → low, label them (2160 → "4K", 4320 → "8K", 1440 → "2K", otherwise "<h>p"). Put **"Best available (<top label>)"** first.
- No hard-coded list of resolutions anywhere.

**Verify** (unit tests with `sample_info.json` and small fake lists)
- [ ] Output is sorted high → low with "Best available" first.
- [ ] A fake format list containing 4320 produces an "8K" entry with no code change.
- [ ] Audio-only formats (no height) never appear in the list.

## Chunk 3.3 — Video tab complete

**Files you may touch:** `app/ui/video_tab.py`, `app/ui/main_window.py`.

**Do**
- Auto-fetch when a valid link is pasted (also a Fetch button).
- Show the thumbnail (radius 8), title, "Channel • duration", the quality dropdown.
- Download uses the chosen height; default = Best available.
- Free-space check before download: if the estimated size is larger than free space, show "Not enough free space. Needs about X GB." and do not start.
- Container comes from settings (`mkv` default).

**Verify**
- [ ] Paste a 4K video: dropdown lists real resolutions, default is Best available.
- [ ] Choose 720p: output file is 720p (check with the player's info) and has sound.
- [ ] Paste a new link while one is loaded: the old info is replaced, nothing stale remains.
- [ ] Layout matches the design file (no extra colours, red only on Download and progress).

## Chunk 3.4 — Audio tab

**Files you may touch (new):** `app/ui/audio_tab.py`; edit `app/ui/main_window.py`.

**Do**
- Same link/fetch/info block as the Video tab. **Reuse the Video tab's pieces; do not copy-paste logic.** If sharing requires touching `video_tab.py`, extract the smallest shared widget and report it.
- Dropdown: Best original (default), MP3, M4A, Opus, WAV, FLAC.
- Two checkboxes: "Embed cover art", "Embed metadata" (adds `--embed-thumbnail` / `--embed-metadata`).
- Small muted note: "YouTube audio is about 128 to 160 kbps. Converting to MP3 cannot improve it."

**Verify**
- [ ] Best original saves `.m4a` or `.webm/opus` without conversion.
- [ ] MP3 option produces a playable `.mp3`.
- [ ] WAV and FLAC produce playable files.
- [ ] Cover art appears in a media player when ticked.

---

## Phase 3 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] Links with `&list=` and `&t=` download one video only.
- [ ] One 4K video: merged, one file, has audio. One 720p video: same.
- [ ] Both tabs follow `02_DESIGN_SYSTEM.md`; no terminal appeared.
- [ ] Only files from the chunk lists changed. User said "go on".
