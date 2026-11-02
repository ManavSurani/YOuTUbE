# Plan 24 Phase 1: Buttons at Their Real Size

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- New: `tests/test_theme_polish.py` Phase 1 part (8); 7 failed first (the text-button spacing guard already passed).
- Full suite: **653 passed**; failures only the known set (scope test; `test_tab_looks` combobox / line-edit pair).

## Done
- 1.1 Kit buttons carry `kit="true"`; the stylesheet rule `QPushButton[kit="true"] { padding: 0; min-height: 0; border: none; background: transparent }` stops the global button style from inflating custom-painted buttons. Text kit buttons size themselves (text + 16 px each side). **All icon buttons are now their requested size (28×28 / 32×32)**; the snapshot check reports no clipped or non-square buttons.
- 1.2 Progress-card Pause/Resume, Open, and Show in folder are vertically centred in the header row: **no longer cut off**.
- 1.3 Paused: the stats line shows only the sizes (`302.3 MB / 690.1 MB`); the stage line says "Paused". No stale speed/ETA.
- 1.4 Done: the empty stats line is hidden (no gap).

## Also fixed here (from the unreleased 1.0.7 work)
- The aligned quality list used a custom item delegate (Python `paint`/`sizeHint`). It was replaced by plain text with thin-space padding measured to the pixel: same right-aligned size column, no custom painting (sizes are no longer drawn in muted grey).
  - Reason: a random access-violation crash during app-wide restyles appears when many widgets from earlier tests are alive (four test files together). It also happens before this phase and without the delegate, so it is a test-session artefact. A realistic stress run (one window, about 90 theme switches, Settings opened and closed, tabs switched, lists refreshed) passed 2/2 completed runs with no crash. Plain text is the safer choice anyway.
- `test_core_flow::test_dropdown_shows_size_but_job_keeps_clean_label` (from Plan 23) now checks "starts with the quality, ends with the size" instead of the old `1080p · ≈ 690.1 MB` text. This is the owner-requested alignment change.

## Snapshot review (plan24_phase1)
- Paused/Done: buttons centred next to the title in both themes; no gap at Done.
- Queue ✕/retry/copy and history/recent play/folder/⋯: square and centred.
- Quality popup: sizes in one right-aligned column.
- Remaining findings: menus in light mode (Phase 2).
