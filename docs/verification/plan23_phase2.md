# Plan 23 Phase 2: All Screens on Tokens + Type Scale (light mode fixed)

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Before: 572 passed, 1 failed (known scope test).
- After: **579 passed**, 1 failed (same known). New: `tests/test_light_mode.py` (8).
- R5 note: the screen code was written before these tests. To keep the failing-first proof, the Phase 2 code was stashed and the tests run on the old code: **7/8 failed** for the right reasons (hex literals, off-scale font sizes, unreadable light labels in header/video/history/settings, no live switch). The 8th (no dark blocks) already passed thanks to Phase 1. The changes were then restored.
- Suite time: the first version reloaded the queue, recent list, and history on every theme change. That was slow (5 min suite, and a DB read per switch in the app). Rows now restyle themselves in place (2.5 min suite; a real theme switch with the main window takes about 0.25–0.4 s).
- A hard crash (0xC0000409) appeared when `test_light_mode` ran right after `test_per_item_cards::test_tab_scroll_bounds_with_many_queued_items`. That test deleteLater()s a MainWindow whose network thread is still running; a nested event loop in the new test executed that deletion, which made Qt abort. The new tests now settle with `processEvents()` (no nested loop). No existing test changed.

## Changes
- `header.py`, `video_tab.py`, `audio_tab.py`, `queue_widget.py`, `recent_list.py`, `history_tab.py`, `settings_dialog.py`, `main_window.py` (banner + title bar on theme change), `splash.py` (bg token, title role): no hex literals; labels use roles; code-styled widgets restyle on `ThemeManager.changed`.
- `main.py` and Settings → Appearance use `ThemeManager.apply` (live switch, including the title bar).
- Font sizes: only 12/13 inline plus the 15/18 roles.

## Snapshot review (phase2)
- Light: all 10 screens readable (titles, brand, tabs, headings, links, inputs, buttons, progress, settings). The banner still has the big filled buttons (Phase 3 task 3.9).
- Dark: unchanged look; section headers ("Up next", "Recently downloaded") are now `text` instead of muted, so the hierarchy is clearer.

## Scope
`app/main.py`, `app/ui/{header,video_tab,audio_tab,queue_widget,recent_list,history_tab,settings_dialog,main_window,splash}.py`, `tests/test_light_mode.py`, this note.
