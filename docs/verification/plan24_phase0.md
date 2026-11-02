# Plan 24 Phase 0: Complete Audit Tool

Date: 2026-11-02 · Branch: `fix/ui-pass`

`tools/ui_snapshots.py` now renders 50 images per run: main screens and states (ready, error, downloading, **paused**, **done with a real file**, copied-link chip, audio, history, history search, banner + offline), the **quality popup**, the **link-box context menu**, the **History row / History more / tray menus**, Settings, the **History delete / clear / warning dialogs**, a **message box**, the splash, and **live switches dark→light and light→dark** (main, Settings, History).

Automatic checks (printed as FINDING): clipped widgets, icon buttons that are not square/requested size, menu backgrounds that don't match the theme `surface` token.
Tooltips can't be captured offscreen (Windows shows them only on screen); the tooltip style is covered by a test in Phase 2.

## Baseline findings (matches the plan)
- F1: every IconButton is 36 px tall (28×36, 32×36); the progress-card Pause/Resume button is **clipped** (`(x, 4, 28, 36)` in a 36 px row) in both themes.
- F2: History row menu, History more menu, and tray menu background `#1e1e1e` in **light** mode (should be `#F2F2F2`) → unreadable.
