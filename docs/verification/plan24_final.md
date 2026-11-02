# Plan 24 Final: Theme and Button Fix

Date: 2026-11-02 · Branch: `fix/ui-pass` · Commits `2236f1c` … `fb4c51a`

## Findings
| # | Finding | Status |
|---|---|---|
| F1 | Kit buttons inflated by the app-wide button style (Pause/Resume cut off at the bottom) | **Fixed** (Phase 1): `kit` property + QSS reset, real size hints, centred in the row. Icon buttons are exactly 28/32 px in both themes. |
| F2 | Menus not themed (row ⋯, History ⋯, tray) | **Fixed** (Phase 2): `QMenu` rules from tokens. |
| F3 | Tooltips not themed | **Fixed** (Phase 2): `QToolTip` rule from tokens (covered by test; tooltips can't be captured offscreen). |
| F4 | History blank right after switching | **Fixed** (Phase 4): fade after the page is built, and removed rows no longer pop up as stray windows. History opens in about 0.46 s instead of 1.5 s (50 rows). |
| F5 | "Same as Windows" didn't follow Windows live | **Fixed** (Phase 3): `colorSchemeChanged`. |
| F6 | Dialog and message box title bars not themed | **Fixed** (Phases 3–4): every window that opens gets the theme's title bar through `focusWindowChanged`; open windows restyle on a switch. Checked on screen with a real message box. |
| F7 | Paused showed old speed and ETA | **Fixed** (Phase 1): only `302.3 MB / 690.1 MB` while paused. |
| F8 | Gap under the Done bar | **Fixed** (Phase 1): the empty stats line is hidden. |
| F9 | Snapshot tool missed menus, dialogs, states, live switches | **Fixed** (Phase 0): 50 images plus automatic checks. |

## Verification
- Full suite: 665 passed, 4 failed. All four are the known set: `test_scope_checker_final`; the two `test_tab_looks` cycles, which pass alone; and `test_theme_switch_stays_fast`, which passes alone (in the full run, leftover test windows slow every restyle; one real window switches in 0.16–0.19 s).
- Snapshots: dark, light, live dark→light, and live light→dark at 100 %, 125 %, and 150 % (`plan24_final_1`, `_1.25`, `_1.5`, 150 images). Automatic findings: **none**. Checked by eye: Pause/Resume fully visible, paused and done cards, menus, quality list (sizes aligned, streams without size), message boxes, Settings after live switches.

## Left for the owner's PC (after release)
- Title bars of dialogs/message boxes in both themes.
- With "Same as Windows" selected, change the Windows theme while the app is open.
- Pause/Resume button fully visible at your real scaling.

## Note on scope
- One line outside Phase 4's allowed list: `history_tab.py` hides a removed row before detaching it. This was needed for the "History never blank" gate (details in `plan24_phase4.md`).
