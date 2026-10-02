# Phase 4 — History

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** every finished download is saved to a local history that works offline, with thumbnails, filter, search and actions.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

---

## Chunk 4.1 — Database

**Files you may touch (new):** `app/core/history_db.py`, `tests/test_history_db.py`.

**Do**
- SQLite table `history`: `id, title, url, type (video|audio), quality, file_path, size_bytes, duration, thumbnail_path, created_at`.
- Functions: `add`, `list(type=None, search="")`, `delete`, `get`. Create the table on first open. Newest first.

**Verify** (unit tests on a temp database)
- [ ] Add 3 rows, list returns them newest first.
- [ ] Filter by type and by search text works (case-insensitive).
- [ ] Delete removes only that row.
- [ ] Opening a brand-new database creates the table without error.

## Chunk 4.2 — Save on completion

**Files you may touch:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/core/downloader.py` (only to expose the data needed), `app/core/history_db.py` (thumbnail copy helper).

**Do**
- On `finished(file_path)`, copy the thumbnail to `thumbnails\` and add one history row (real file size from disk).
- Do nothing on cancel or failure.

**Verify**
- [ ] A finished video adds exactly one row; a cancelled one adds none.
- [ ] The thumbnail file exists in `thumbnails\`.
- [ ] Row `size_bytes` equals the real file size.

## Chunk 4.3 — History list UI

**Files you may touch (new):** `app/ui/history_tab.py`; edit `app/ui/main_window.py`.

**Do**
- Filter chips: All / Video / Audio. Search box. Rows exactly as in the design file.
- Row shows thumbnail, title, one muted line (`type • quality • size • date`).
- Empty state: one muted sentence "Nothing here yet."
- If the file no longer exists, show a small muted "File missing" tag.

**Verify**
- [ ] 20+ rows scroll smoothly.
- [ ] Filter and search update the list instantly.
- [ ] Renaming a downloaded file on disk and reopening the tab shows "File missing".
- [ ] Works with the internet off.

## Chunk 4.4 — Row actions

**Files you may touch:** `app/ui/history_tab.py`.

**Do**
- Actions (shown on hover, text buttons): **Play** (open with the default player), **Open folder** (select the file in Explorer), **Copy link**, **Re-download** (sends the link to the matching tab), **Delete** (ask: "Remove from history only" or "Also delete the file").
- Opening files/folders uses Qt's `QDesktopServices` or the Windows shell through `proc.py`. Never a visible console.

**Verify**
- [ ] Play opens the file; Open folder shows it highlighted.
- [ ] Copy link puts the clean link in the clipboard.
- [ ] Re-download fills the right tab and starts the fetch.
- [ ] "Remove from history only" keeps the file; "Also delete the file" removes it.
- [ ] No terminal flashes for any action.

---

## Phase 4 verification (all must pass)

- [ ] All chunk Verify lists are checked; `pytest` is green.
- [ ] Download one video and one audio → both appear, filters separate them.
- [ ] Close and reopen the app → history is still there.
- [ ] Offline test (disconnect Wi-Fi): History tab opens, plays, and deletes normally.
- [ ] Only files from the chunk lists changed. User said "go on".
