# Plan 24 Phase 3: Window Chrome and "Same as Windows"

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- New (in `tests/test_theme_polish.py`): every dialog/message box gets a title bar matching the theme (dark and light); switching theme restyles open dialogs; "system" follows a live Windows change; an explicit theme ignores it; a switch with the main window and Settings open stays under 0.5 s.
- Full suite: 663 passed, 4 failed. Three are the known ones (`test_scope_checker_final`, the two `test_tab_looks` cycles that pass alone). The fourth, `test_theme_switch_stays_fast`, took 8.3 s only in the full run, where hundreds of leftover test widgets get restyled. Alone it passes. A check with 400 open windows showed the title-bar step costs nothing (0.07–0.10 s with or without it).

## Done
- `apply_dark_title_bar` moved from `main_window.py` to `theme.py` (unchanged).
- `ThemeManager` watches every window as it is shown and gives it the theme's title bar (dialogs, message boxes, Settings), restyles open windows on a switch, and follows Windows live when the saved theme is "system" (`colorSchemeChanged`).
- `windows_prefers_light()` asks Qt first, then falls back to the registry.

## Snapshot review (plan24_phase3)
- Automatic findings: **none**.
- Pages, menus, and dialogs are unchanged from Phase 2 in both themes. Title bars aren't captured offscreen, so the tests cover them.
