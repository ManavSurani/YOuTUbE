# Plan 25 Phase 1: Tests

Date: 2026-11-02 · Branch: `fix/ui-pass`

New `tests/test_menu_backgrounds.py`. A real main window shows 3 History rows, and every menu is built from its real parent.

| Test | Before the fix |
|---|---|
| Row ⋯ menu, dark and light | **fail**: background `#00000000` (fully transparent, shown black by Windows) |
| Row right-click menu, dark and light | **fail**: same |
| Row menu after a live dark → light switch | **fail**: same |
| History ⋯, tray, search box, Video and Audio link boxes, Settings folder field (both themes) | pass (regression guard) |
| No container stylesheet leaks into children | **fail**: finds the History list, the Video and Audio containers, and their two scroll viewports (5 rules) |

6 failed, 2 passed, as planned.
