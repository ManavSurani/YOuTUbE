# Phase 6: Settings

**Goal:** A clean popup where every change feels instant and satisfying, with no Save/Cancel at the bottom.
**Fixes:** B11 (settings side). **Depends on:** Phase 3.
**Files:** `ui/settings_dialog.py`, `core/settings.py`.

---

## Chunk 6.1: Layout and cleanup

Tasks:
1. Remove the "Preferred Video Container" section and its note. Remove `container` from settings use (keep reading old values harmlessly; migrate by ignoring).
2. Remove the bottom **Save** and **Cancel** buttons. The dialog gets a small close icon and closes with Esc.
3. Sections: Download folder, Appearance, Updates, About. Consistent spacing, subtle section dividers.
4. Dialog size adapts to content (no clipped controls at 125% and 150% Windows scaling).

Done when: nothing in the dialog is cut off at 100%, 125% and 150% scaling.

---

## Chunk 6.2: Download folder with Save

Tasks:
1. Path box is **read-only**, shows no text cursor, and cannot take focus.
2. **Browse** opens the folder picker. After choosing a different folder the path updates and a small **Save** button appears beside it (animated fade-in).
3. Clicking **Save** validates the folder (exists, writable, enough free space warning), saves, shows "Saved ✓" for about 1 second, then the button hides.
4. If the folder is not writable, show a clear message and keep the old path.
5. The new folder is used by the **next** download. Finished items and History are not touched.

Done when: change, save, and a new download lands in the new folder.

---

## Chunk 6.3: Appearance and Updates

Tasks:
1. Appearance dropdown (Dark, Light) applies instantly and persists immediately.
2. "Check for updates automatically" uses the new animated checkbox, ON by default, applies instantly.
3. **Check now** button: shows a spinner while checking, then "You're up to date ✓" or "Version X.Y.Z is available" with an **Install** button. Offline shows "No internet connection".
4. All settings are written atomically (write temp file, then replace) so a crash cannot corrupt `settings.json`.

Done when: toggling each setting persists after restart without pressing any Save.

---

## Chunk 6.4: About and support

Tasks:
1. About shows name (exact "YOuTUbE" spelling), version, and the open-source credits with clickable links.
2. **Export log** button copies `app.log` to a chosen location (suggestion S5).
3. **Open download folder** link.

Done when: Export log creates a readable file.

---

## Verification Gate: Phase 6

Evidence in `docs/verification/phase_6.md`.

### Automated
- [ ] pytest-qt: folder flow (browse, save button appears, save, hidden), read-only path box, instant settings persistence, check-now states (up to date, available, offline), atomic write test.

### Manual
- [ ] Settings button opens a fully visible dialog; no container option; no bottom buttons.
- [ ] Path box shows no cursor, even after clicking it.
- [ ] Change folder: Save appears, "Saved ✓" animation plays, next download goes to the new folder.
- [ ] Theme changes instantly and stays after restart.
- [ ] Checkbox looks clearly checked, animates, persists.
- [ ] Check now shows a spinner then a clear result.
- [ ] Test at 125% and 150% Windows display scaling.

### No-terminal check (mandatory)
- [ ] Check now, Export log and Open folder show no console window.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 7.
