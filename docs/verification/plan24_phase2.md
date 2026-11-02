# Plan 24 Phase 2: Menus and Tooltips Follow the Theme

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- New (in `tests/test_theme_polish.py`): menu background equals `surface` in dark and light; menus follow a live switch; the stylesheet has `QMenu`, `QMenu::item:selected`, and `QToolTip` rules built from tokens. 4 failed first (light menu + rules); dark only passed by chance before (native dark menu).
- Theme/light-mode/tab-looks suites: 54 passed.

## Done
- `build_qss`: `QMenu` (surface, text, 1 px border, radius 8, padding), `::item` padding/radius, `::item:selected` (surface_hover), `::item:disabled` (text_muted), `::separator` (border), and `QToolTip` (surface, text, border). This covers the History row ⋯, History ⋯ (Clear all), tray menu, and future menus.

## Snapshot review (plan24_phase2)
- Automatic findings: **none** (no clipping, no non-square icon buttons, menu backgrounds match the theme).
- Light: row menu, history more menu, tray menu readable (dark text on #F2F2F2); link-box menu unchanged and readable.
- Dark: same menus on #212121 with light text.
- Tooltips can't be captured offscreen; covered by the stylesheet test.
