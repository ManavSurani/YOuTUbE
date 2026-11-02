# Plan 25: Black History Row Menu (Light and Dark)

Date: 2026-11-02 · Branch: `fix/ui-pass` · Ships as 1.0.8 (only after the owner says yes)

## The problem (from the owner's screenshot, 1.0.7, light mode)
The History row "⋯" menu has a **black** background. "Copy link" (hovered) is readable, but "Re-download" and "Delete" are dark text on black, so you can't read them. The History "⋯" (Clear all) menu and the tray menu look correct.

## Root cause (reproduced on the real screen)
- [history_tab.py:679](../app/ui/history_tab.py#L679): `self.container_widget.setStyleSheet("background: transparent;")` has **no selector**. A widget's own stylesheet applies to the widget **and every child**, and it beats the app stylesheet.
- The row menu is created as `QMenu(row)`, and the row sits inside `container_widget`. So the menu inherits `background: transparent`. A menu is its own window and can't be see-through, so Windows fills it with black.
- Proof:
  - On screen, a menu with no parent shows `#F2F2F2` (correct), while the same menu with the real row as parent is black.
  - An offscreen grab of the real row menu also reads `#000000` instead of `#F2F2F2`.
  - The History "⋯" and tray menus have parents outside the list, so they're fine.
- Dark mode has the same bug. It shows `#000000` instead of `#212121`, so it's harder to notice.
- **Why Plan 24 missed it:** `tools/ui_snapshots.py` builds the row menu from a `HistoryRowWidget(item)` **with no parent**, so it never sat inside the list.

## Same pattern elsewhere (latent, no visible bug today)
| Place | Line | Inherited by |
|---|---|---|
| Video tab scroll viewport | `video_tab.py:474` | everything in the Video tab's scroll area |
| Video tab container | `video_tab.py:478` | same |
| Audio tab scroll viewport | `audio_tab.py:97` | everything in the Audio tab's scroll area |
| Audio tab container | `audio_tab.py:101` | same |

None of these hold a plain `QMenu` today. The link-box menu has its own menu stylesheet, and the quality popup paints itself. But any menu added there later would turn black in the same way, so this plan scopes them too (same one-line change each).

## Rules
1. **Fix the cause, not the symptom.** Scope the four or five unscoped `background: transparent` rules to the widget they're meant for. Don't add a per-menu stylesheet and don't add a `QMenu` override in the tabs.
2. **Touch only:** `app/ui/history_tab.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py` (only the lines in the table above and line 679), `tools/ui_snapshots.py`, the new `tests/test_menu_backgrounds.py`, and the phase notes.
3. **Don't touch:**
   - `theme.py` menu rules. They're correct.
   - Colours, tokens, or the logo.
   - Menu items, their order, or what they do.
   - The downloader engine.
   - Old tests.
   - The link-box menu's own stylesheet.
4. **Tests first.** Each new test must fail before the fix and pass after it.
5. Each phase ends with its tests, snapshots, a short note in `docs/verification/plan25_phaseN.md`, and a commit.
6. Nothing goes to GitHub (push, merge, release) without the owner's yes. The app must be closed for a release. The owner's Android gradle edits stay uncommitted.

---

## Phase 0: Make the audit see what the user sees
**Allowed:** `tools/ui_snapshots.py`, note.

| Task | Do | Don't |
|---|---|---|
| 0.1 | Build the row menu from a **real row inside the real History list** (`win.history_tab._rendered_rows`), not from a parentless row. | Don't remove the existing images. |
| 0.2 | Also capture the row's **right-click** menu (`contextMenuEvent` uses the same builder; capture it through that path). | — |
| 0.3 | Add the remaining right-click menus to the menu check: History search box, Settings download-folder field, and the Audio tab link box. Every menu is built from its real parent in the real window. | Don't add menus that don't exist in the app. |
| 0.4 | Add a scratch on-screen check (not committed): open each menu on the real screen in light and dark and read the pixels with a screen grab. | Don't commit scratch scripts. |

**Gate:** the tool reports a FINDING for the row menu in both themes (black instead of `surface`) and none for the other menus. This proves the tool now catches the bug.

## Phase 1: Tests
**Allowed:** `tests/test_menu_backgrounds.py` (new).

| Test | Checks |
|---|---|
| Row menu, light and dark | The menu built from a real row in the History list has a background within 12 of `surface`. |
| Right-click row menu | Same check via `contextMenuEvent`. |
| Live switch | Open History in dark, switch to light, build the row menu: the background is the light `surface`. |
| Every menu | History ⋯, tray, search box, folder field, both link boxes: the background is `surface` in both themes. These pass today and guard against regressions. |
| No leaking container rule | Walk the main window and Settings. Any widget that **has child widgets** and a stylesheet with a declaration outside `{ }` (an unscoped rule) fails the test. Today this catches the History container and the four Video/Audio lines. Leaf labels with `color:` are allowed because they have no children. |

**Gate:** the row-menu tests and the leak test fail. All the others pass.

## Phase 2: The fix
**Allowed:** the five lines listed above.

| Task | Do | Don't |
|---|---|---|
| 2.1 | History: give `container_widget` an object name (`historyList`) and set `QWidget#historyList { background: transparent; }`. | Don't change the row stylesheet or `scroll_area`. |
| 2.2 | Video and Audio: the same for the container (`videoList` / `audioList`) and the scroll viewport (`QWidget#qt_scrollarea_viewport { background: transparent; }`, or an object name). | Don't change layouts, margins, or the `QScrollArea` rule. |
| 2.3 | Compare the page snapshots before and after. They must be **pixel-identical** except the menus, so the scoping changes nothing else. | If any page changes, stop and find out why before going on. |

**Gate:** all Phase 1 tests pass; page snapshots are unchanged; the row menu is `#F2F2F2` (light) or `#212121` (dark).

## Phase 3: Full verification
1. Full suite: only the known set may fail (`test_scope_checker_final`, the two `test_tab_looks` cycles, `test_theme_switch_stays_fast` in the full run). Any of these re-run alone must pass, except the scope checker.
2. Snapshots in dark, light, live dark→light, and live light→dark at 100 %, 125 %, and 150 %. Claude checks every menu image by eye.
3. The on-screen check from 0.4: every menu, both themes, read from the real screen.
4. Final note `docs/verification/plan25_final.md`.
5. Ask the owner: release 1.0.8? (app closed, same release steps as 1.0.7).
6. Owner's check after the update: right-click a History row and click its "⋯", in light and in dark.

## Out of scope
- New menu items or icons in menus.
- Restyling the link-box menu (it already works).
- Any other Plan 23/24 deferred items.
