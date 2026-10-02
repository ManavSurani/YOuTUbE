# Phase 5: History Tab

**Goal:** A reliable, good-looking History that never loses items and handles every file situation.
**Fixes:** B6 (display side), B7 (delete side), B12. **Depends on:** Phases 2 to 4.
**Files:** `ui/history_tab.py`, `ui/kit/*`.

---

## Chunk 5.1: Rows and icon actions

Tasks:
1. Row layout: thumbnail (rounded), title, meta line (type, quality, size, date), then icon buttons: **Play**, **Open folder**, **Copy link**, **Re-download**, **Delete**. Tooltips on every icon.
2. Icon buttons use the kit (hover glow, press shrink, success tick after Copy link). Delete turns red on hover.
3. If the file is missing: show "File missing" (muted), hide Play, show **Locate file**.
4. Use `ThumbLabel` (re-fetches missing thumbnails, never shows a letter).
5. File existence is checked in a worker (not on the UI thread) and cached.

Done when: rows with missing files and rows with files both look correct.

---

## Chunk 5.2: Filters, tabs feel, search

Tasks:
1. Filter chips: All, Video, Audio, with an active chip filled red and a smooth colour transition.
2. Search box stays. It does **not** take focus when the tab opens (set focus to the list container, not the box).
3. Empty state: a friendly illustration-free message ("Nothing here yet") and a hint to paste a link.

Done when: opening History shows no text cursor anywhere.

---

## Chunk 5.3: Delete flow

Tasks:
1. A small custom dialog (not `QMessageBox`) with three buttons: **Delete file too** (red), **Remove from history only**, **Cancel**.
2. "Delete file too" uses `HistoryService.delete` (Recycle Bin). If it cannot move the file (open in a player), show the exact reason and keep the row.
3. A **Clear all history** ghost button in the header of the list, with a confirm dialog and an unchecked "Also delete the files" checkbox.
4. After deleting, the row animates out (fade and collapse) instead of the list jumping.

Done when: deleting works for normal, locked and missing files with the right message each time.

---

## Chunk 5.4: Re-download and Locate

Tasks:
1. Re-download switches to the right tab, fills the link, auto-fetches, and pre-selects the same quality when possible. It then waits for the user to press Download (never auto-starts).
2. **Locate file** opens a file picker, validates the chosen file, and calls `relink`.
3. Same-video duplicate rule is applied (Phase 2.4) so repeated downloads update the row.

Done when: re-download and locate work end to end.

---

## Chunk 5.5: Performance

Tasks:
1. Load rows lazily (first 50, load more on scroll) so large histories stay fast.
2. Reload only the changed row after delete or relink instead of rebuilding the whole list.

Done when: a history of 500 rows opens in under 1 second.

---

## Verification Gate: Phase 5

Evidence in `docs/verification/phase_5.md`.

### Automated
- [ ] pytest-qt tests: row states (file present, missing, thumbnail missing), filter, search, delete flows (all three buttons), locate, re-download.
- [ ] Performance test with 500 rows.

### Manual
- [ ] No text cursor in the search box on opening History.
- [ ] Delete file in Explorer: row stays, thumbnail stays, shows "File missing" and "Locate file".
- [ ] Locate file reconnects it and Play works again.
- [ ] Delete file too goes to the Recycle Bin; restore it from there and Locate works.
- [ ] Locked file shows the "open in another program" message and the row stays.
- [ ] Chip and tab animations feel smooth; icon buttons show tooltips.

### No-terminal check (mandatory)
- [ ] Open folder (Explorer select) and Play do not flash any console window.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 6.
