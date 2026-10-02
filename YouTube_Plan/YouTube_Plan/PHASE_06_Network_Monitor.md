# Phase 6 — Network Monitor

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** the app notices when the internet goes off or comes back, locks and unlocks the right controls, and warns the user exactly once per outage.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

---

## Chunk 6.1 — Watcher

**Files you may touch (new):** `app/core/network_monitor.py`, `tests/test_network_monitor.py`.

**Do**
- A small thread checks every 4 s by connecting to `youtube.com:443` (3 s timeout), with a fallback host. Two failures in a row = offline (avoids false alarms).
- Signals: `went_offline`, `came_online`. Emit only on a **change** of state.

**Verify**
- [ ] Unit test with a fake connector: online → offline emits once; staying offline emits nothing more; offline → online emits once.
- [ ] A single failed check does not trigger offline.
- [ ] The thread stops cleanly when the app closes (no hang on exit).

## Chunk 6.2 — Status dot and one-time popup

**Files you may touch:** `app/ui/main_window.py`.

**Do**
- Replace the static dot with the live one: `Online` (success) / `Offline` (error).
- On `went_offline`: show **one** message box "Internet is off. You can still view your history." One popup per outage, none on later checks.

**Verify**
- [ ] Turn Wi-Fi off: dot turns red "Offline", exactly one popup.
- [ ] Stay offline 1 minute: no further popups.
- [ ] Turn Wi-Fi on: dot turns green "Online", no popup.
- [ ] A second outage shows a popup again (once).

## Chunk 6.3 — Locking and download resume

**Files you may touch:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/main_window.py`, `app/core/downloader.py`.

**Do**
- Offline: disable link box, Fetch, Download, and the quality/format dropdowns. History tab stays fully usable.
- If a download is running when the net drops: pause it (stop the process, keep the `.part` file), show stage "Waiting for internet…".
- When online again: restart the same download; yt-dlp continues the partial file.

**Verify**
- [ ] Offline: controls are greyed; History can play, filter, delete.
- [ ] Drop the net at ~40%: stage shows "Waiting for internet…"; on reconnect the download finishes and the file plays fully.
- [ ] Cancel while waiting works and cleans leftovers.

---

## Phase 6 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] Full cycle test: start a download, disconnect, wait 30 s, reconnect → finishes, one popup total.
- [ ] Closing the app while offline exits cleanly.
- [ ] Only files from the chunk lists changed. User said "go on".
