# Phase 8 — Polish: Errors, Settings, Queue, Notifications

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** failures speak plain language, the few real settings exist, many links can be queued, and finishing a download is noticed. Nothing else gets added.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

**Not in v1.0 (backlog, do not build):** playlist download, clipboard watcher, extra themes, extra languages.

---

## Chunk 8.1 — Plain-language errors

**Files you may touch (new):** `app/core/errors.py`, `tests/test_errors.py`; edit the tabs only where they display a failure.

**Do**
- `explain(raw_text, free_bytes=None)` maps raw yt-dlp output to one sentence:

| Problem | Message |
|---|---|
| Network error | "No internet connection." |
| Private / members-only | "This video is private or for members only." |
| Age-restricted | "This video is age restricted and can't be downloaded without sign-in." |
| Unavailable / removed | "This video is not available." |
| Sign-in / bot check | "YouTube asked for verification. Try again later or update tools." |
| Extraction error | After the one auto-update retry fails: "YouTube changed something. Please try again after the update." |
| ffmpeg missing | Re-download ffmpeg automatically, then retry once |
| Low disk space | "Not enough free space. Needs about X GB." |
| Invalid link | "Please paste a valid YouTube link." |
| Anything else | "Something went wrong. Copy the details and try again." |

- A small "Copy error details" text button copies the raw log lines of that attempt.

**Verify**
- [ ] One unit test per table row with a realistic raw string.
- [ ] Unknown text falls into the last row, never crashes.
- [ ] Raw text never appears in the UI except through "Copy error details".

## Chunk 8.2 — Settings dialog

**Files you may touch (new):** `app/ui/settings_dialog.py`; edit `app/ui/main_window.py` (a plain "Settings" text button), `app/core/settings.py` (only if a key is missing).

**Do**
- Fields only: download folder, container (MKV / MP4, with a note that MP4 may limit the top resolution), theme (Dark / Light), auto-update on/off, "Check for updates now".
- Changing theme re-applies the stylesheet immediately.
- An "About" line: app name, version, and credits for yt-dlp, ffmpeg and deno.

**Verify**
- [ ] Each setting survives closing and reopening the app.
- [ ] Theme switch changes live with no leftover dark parts.
- [ ] MP4 choice downloads a playable `.mp4` and the note about resolution is visible.
- [ ] Dialog contains no extra options.

## Chunk 8.3 — Queue

**Files you may touch:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/core/downloader.py`.

**Do**
- "Add to queue" next to Download. Queue runs one item at a time, in order. Simple list under the progress area with a remove button per waiting item.
- A failed item is marked failed with its plain-language reason; the queue moves on.

**Verify**
- [ ] Queue 3 links: they download one after another.
- [ ] Remove a waiting item: it is skipped.
- [ ] A bad link in the middle fails alone; the others still finish.
- [ ] Cancel stops the current item; the queue then waits for the user (does not silently continue).

## Chunk 8.4 — Finish notification

**Files you may touch:** `app/ui/main_window.py`.

**Do**
- When a download finishes while the window is not active, show one system tray toast "Download finished" (Qt `QSystemTrayIcon.showMessage`). No sound unless the OS default.
- Stage text becomes "Done. Saved to Downloads."

**Verify**
- [ ] Minimise during a download: the toast appears on completion.
- [ ] Window active: no toast, only the stage text.

---

## Phase 8 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] Walk through every error row by provoking it (or a recorded raw sample) and read the message.
- [ ] Design review against `02_DESIGN_SYSTEM.md`: only allowed colours, red only where permitted, no decoration.
- [ ] Code review: no unused functions, no dead code, no TODO comments left (`grep -rn "TODO\|FIXME" app/`).
- [ ] Only files from the chunk lists changed. User said "go on".
