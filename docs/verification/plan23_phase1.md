# Plan 23 Phase 1: Theme Foundation (kit widgets)

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Before: 561 passed, 1 failed (known scope test).
- After: **572 passed**, 1 failed (same known). New: `tests/test_theme_tokens.py` (10), all failing before the change.
- `test_ui_kit.py::test_thumb_label_fallback` caught a size bug in the new placeholder (device-pixel size). Fixed in code; the test is unchanged.

## Changes
- `theme.py`: `current_theme()`, `tok()`, `qcolor()`, `ThemeManager` (`apply`, `changed`), alias tokens `focus` / `status_offline` (existing colors), type roles `title` 18 / `section` 15 / `strong` 13 / `meta` 12 / `link`. Palette values are unchanged (tested).
- Kit: `buttons.py`, `checkbox.py`, `inline_message.py`, `toast.py`, `progress_card.py`, `thumb_label.py` use tokens only (no hex literals, tested). Painted widgets repaint on theme change. `ThumbLabel` draws a theme-aware placeholder when no thumbnail is cached (`thumbnails.py` untouched).

## Snapshot review (phase1)
- Light: secondary buttons now light surface with dark text; progress card title, percent, and track readable; thumbnail placeholders light. Screen-level labels (titles, brand, section headers) are still white-on-white, which is expected and is Phase 2's scope.
- Dark: unchanged look; buttons use the surface tokens (a 1-step tone change only).

## Scope
`app/ui/theme.py`, `app/ui/kit/{buttons,checkbox,inline_message,toast,progress_card,thumb_label}.py`, `tests/test_theme_tokens.py`, `docs/verification/plan23_phase0.md` (decision recorded), this note.
