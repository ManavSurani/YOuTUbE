# Plan 25 Phase 2: The Fix

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Done
- `history_tab.py`: the list container is named `historyList`, and its rule is now `QWidget#historyList { background: transparent; }`.
- `video_tab.py` / `audio_tab.py`:
  - The scroll viewport rule is scoped to `QWidget#qt_scrollarea_viewport`.
  - The container is named `videoList` / `audioList`.
  - Its rule covers the container, its link box (`QLineEdit`), and its dropdown (`QComboBox`).

## Page comparison (task 2.3)
- First try (container only): the Video and Audio link boxes and the quality dropdown turned grey-filled, because they had been see-through only through the leaking rule. That's a colour change, so I stopped and found the cause. Naming the link box and dropdown in the scoped rule keeps them exactly as before.
- Final: 44 of 58 images are pixel-identical. The 14 that differ:
  - 4 are the fixed row menus (light and dark, ⋯ and right-click), as intended.
  - 10 differ only in the red progress bar, by 1–6 shades of red: the glow animation caught at a different moment, not a style change.

## Tests and checks
- `tests/test_menu_backgrounds.py`: 8 passed (6 failed before the fix).
- Snapshot findings: **none**.
- Real screen: the row menu is `#F2F2F2` in light and `#212121` in dark, with all three items readable.
