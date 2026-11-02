# Plan 25 Final: Black History Row Menu

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Result
- The History row menu (⋯ and right-click) uses the theme surface: `#F2F2F2` in light and `#212121` in dark. Before, it was fully transparent, which Windows showed as black.
- Root cause: the History list (and the Video and Audio lists and viewports) had an unscoped `background: transparent`, which reached every child, menus included. All five rules now target only their own widget. Pages are pixel-identical, apart from the progress bar's glow animation.
- The snapshot tool builds every menu from its real parent, so this class of bug shows up as a FINDING.

## Verification
- Full suite: 672 passed, 5 failed.
  - Known, pass alone: the two `test_tab_looks` cycles; `test_theme_switch_stays_fast` (slow only because of leftover test windows); `test_single_instance_detection` (fails only while a YOuTUbE instance is running; passed alone 3 of 3).
  - Known, still red: `test_scope_checker_final`.
- New `tests/test_menu_backgrounds.py`: 8 passed (6 failed before the fix).
- Snapshots: dark, light, live dark→light and light→dark at 100 %, 125 %, and 150 % (`plan25_final_1`, `_1.25`, `_1.5`; 174 images). Automatic findings: **none**. Menus, link boxes, and dropdowns checked by eye.
- Real screen: the row menu was captured on screen in light and dark; all items are readable.

## Owner check after the update
Right-click a History row and click its ⋯, in light and in dark.
