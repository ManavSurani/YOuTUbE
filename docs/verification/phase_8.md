# Phase 8 Verification: Header, Title Bar, Dropdown Arrow, and Kit Scan

## Summary
- **Date:** 2026-10-04
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Tests Run:** 231 passed in 15.46s (100% passing across 33 test modules)
- **Rows Addressed:** G1, G2, X2, K1 (header and splash)

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Tests Added / Passing |
|---|---|---|---|---|
| G1 | Fixed | Redrew `create_gear_icon` in `app/ui/header.py` as a delicate vector outline gear contour matching the exact 1.3 stroke weight of History icons, replacing the harsh chunky spoke design. | `app/ui/header.py` | `test_gear_icon_outline_not_null_and_non_empty` |
| G2 | Fixed | In `apply_dark_title_bar` in `app/ui/main_window.py`, added Windows 11 DWM caption and text color attributes (`DWMWA_CAPTION_COLOR=35`, `DWMWA_TEXT_COLOR=36`) ensuring the title bar matches `#0F0F0F` / `#FFFFFF` instead of showing OS accent colors. | `app/ui/main_window.py` | `test_apply_dark_title_bar_calls_dwm_and_win11_caption_color` |
| X2 | Fixed | Bundled supplied `arrow_down_dark.png` and `arrow_down_light.png` into `assets/` and added a clean `QComboBox::down-arrow` rule in `app/ui/theme.py:build_qss()` with forward slashes and frozen path support. Zero colors changed, `::drop-down` width untouched. | `assets/`, `app/ui/theme.py` | `test_combobox_down_arrow_rule_in_both_themes` |
| K1 | Fixed | Converted plain `QPushButton` in `app/ui/splash.py` (Retry button) to `AnimatedButton`. Added architecture rule test `tests/test_ui_rules.py` verifying zero plain `QPushButton` instances outside `app/ui/kit/` (except explicit link-style exceptions) and zero `start_hidden` imports in `app/ui/`. | `app/ui/splash.py`, `tests/test_ui_rules.py` | `test_no_unapproved_plain_qpushbutton_in_ui`, `test_no_start_hidden_imported_in_ui` |

---

## Chunks Executed

1. **Chunk 8.1: Settings icon (G1)**
   - Replaced spoke-wheel geometry with a continuous 6-tooth vector outline gear path and inner hub circle with 1.3 stroke width matching history action icons.
   - Tested icon non-nullness and hollow outline annular region at 16px and 32px.
   - Screenshot captured: `docs/verification/phase8_chunk1_settings_icon.png`.
   - Commit: `f444da9` (`phase8.1: redraw settings icon as vector outline gear`).

2. **Chunk 8.2: Main title bar colour (G2)**
   - Extended `apply_dark_title_bar` in `app/ui/main_window.py` to set Windows 11 DWM attributes 35 (caption color) and 36 (text color) matching theme tokens.
   - Wrapped in try/except with logger fallback; checks `sys.getwindowsversion().build >= 22000`.
   - Tested with Windows API mocking on Windows 11 and Windows 10 builds; verified it never raises.
   - Commit: `d7da077` (`phase8.2: set Windows 11 title bar caption and text colors`).

3. **Chunk 8.3: Dropdown arrow (X2)**
   - Copied `arrow_down_dark.png` and `arrow_down_light.png` into `assets/`.
   - Added single approved rule `QComboBox::down-arrow { image: url(...); }` in `app/ui/theme.py`.
   - Tested for both themes ensuring stylesheet references existing files with forward slashes.
   - Screenshot captured: `docs/verification/phase8_chunk3_dropdown_arrows.png`.
   - Commit: `6998caf` (`phase8.3: add QComboBox down-arrow asset and stylesheet rule`).

4. **Chunk 8.4: Splash and kit scan (K1)**
   - Converted `retry_btn` in `app/ui/splash.py` to `AnimatedButton("Retry", role="secondary", parent=self)`.
   - Created `tests/test_ui_rules.py` enforcing UI architecture constraints across all `app/ui/*.py` files.
   - Commit: `2365167` (`phase8.4: convert splash button to AnimatedButton and add ui rules test`).

---

## Verification Gate: Phase 8 Checklist

### Automated Checks
- [x] All new tests pass (`test_gear_icon_outline_not_null_and_non_empty`, `test_apply_dark_title_bar_calls_dwm_and_win11_caption_color`, `test_combobox_down_arrow_rule_in_both_themes`, `test_no_unapproved_plain_qpushbutton_in_ui`, `test_no_start_hidden_imported_in_ui`).
- [x] Full test suite: **231/231 passed in 15.46s** across 33 test modules.

### Manual Checks
- [x] Settings button shows the simple outline gear.
- [x] Windows 11 title bar matches the application background (`#0F0F0F` dark, `#FFFFFF` light).
- [x] Every dropdown (Video, Audio, Settings theme) shows a down arrow in dark and light themes.
- [x] Splash Retry button uses `AnimatedButton` and reacts to hover and press.

### Scope and No-Terminal Checks
- [x] `python tools/check_scope.py --phase 8`: PASS.
- [x] `python tools/check_scope.py --final`: PASS (Zero protected files modified).
- [x] `git grep -n "print(" app/`: 0 hits.
- [x] Zero terminal windows or console popups.

---

## Sign-off
Phase 8 complete. Awaiting user approval to proceed to Phase 9 (Startup and Close).
