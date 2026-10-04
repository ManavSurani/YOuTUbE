# Phase 2 Verification: Open File and Folder (Dead Buttons)

## Summary
- **Date:** 2026-10-04
- **Branch:** `fix/ui-pass`
- **Baseline Commit:** `51a9d986e139bd7ec4ebc3775c9d50584bdf154d`
- **Current Head:** `3cb2e38`
- **Tests Run:** 184 passed in 19.53s (100% passing)

---

## Rows Fixed

| Issue ID | Status | Description | File Changed | Test Name |
|---|---|---|---|---|
| X1 | Fixed | "Show in folder" calls Explorer via hidden process or incorrect quotation | `app/core/file_actions.py` | `tests/test_file_actions.py::test_exact_command_string_spaces`, `test_exact_command_string_unicode` |
| H1 | Fixed | History "Play" and "Show in folder" dead buttons / silent failures | `app/ui/history_tab.py` | `tests/test_history_tab.py::test_history_row_play_and_open_folder_use_helper` |
| R5 | Fixed | Recently downloaded "Play" and "Open folder" dead buttons | `app/ui/recent_list.py` | `tests/test_recent_list.py::test_recent_row_play_and_open_folder_call_helper` |
| S4 | Fixed | Settings "Open download folder" launched via hidden process | `app/ui/settings_dialog.py` | `tests/test_settings_dialog.py::test_open_download_folder_calls_helper` |

---

## Chunks Executed

1. **Chunk 2.1: The Helper (`app/core/file_actions.py`)**
   - Implemented `open_file(path)`, `reveal_in_folder(path)`, and `open_folder(path)`.
   - Uses `os.startfile` and `ShellExecuteW(None, "open", "explorer.exe", param, None, 1)` with `SW_SHOWNORMAL` (no console flashes, Explorer shown in visible window state).
   - Handles spaces and Unicode characters `｜ ： ⧸ é 日本語 😀`.
   - Fallback order: file open -> reveal file in folder -> open parent folder -> "File not found. You can use Locate file.".
   - Zero imports of `start_hidden`.
   - Commit: `4617a13` (`phase2.1: create file_actions helper`).

2. **Chunk 2.2: History Tab Wiring (H1)**
   - Replaced `_play_file` and `_open_folder` in `HistoryRowWidget` with `open_file` and `reveal_in_folder`.
   - Displays friendly `Toast` feedback on failure.
   - Removed `start_hidden(["explorer", ...])` completely from `app/ui/history_tab.py`.
   - Commit: `00b9a67` (`phase2.2: wire file_actions into history_tab`).

3. **Chunk 2.3: Recently Downloaded Wiring (R5)**
   - Replaced `_play_file` and `_open_folder` in `RecentRow` with `open_file` and `reveal_in_folder`.
   - Displays friendly `Toast` feedback on failure.
   - Removed `start_hidden(["explorer", ...])` completely from `app/ui/recent_list.py`.
   - Commit: `5b3cd4e` (`phase2.3: wire file_actions into recent_list`).

4. **Chunk 2.4: Settings "Open Download Folder" (S4)**
   - Replaced `_on_open_download_folder` in `SettingsDialog` with `open_folder`.
   - Preserves "Folder Missing" warning if path does not exist on disk.
   - Removed `start_hidden(["explorer", ...])` completely from `app/ui/settings_dialog.py`.
   - Commit: `fe57a40` (`phase2.4: wire open_folder into settings_dialog`).

---

## Verification Gate: Phase 2 Checklist

### Automated
- [x] `tests/test_file_actions.py` passes (7/7 passed).
- [x] Tests for the three call sites pass (`test_history_tab.py`, `test_recent_list.py`, `test_settings_dialog.py`).
- [x] Full test suite: **184/184 passed in 19.53s**.
- [x] `git grep -n "explorer" app/` returns hits ONLY in `app/core/file_actions.py:53`.

### Scope and No-Terminal
- [x] `python tools/check_scope.py --phase 2` passes with zero violations.
- [x] `python tools/check_scope.py --final` confirms zero changes to protected engine files.
- [x] No console window appeared while running tests or opening windows.

---

## Manual Verification Checklist for Real Windows PC

1. **Play Action:**
   - In History tab: click Play on a downloaded `.mkv`, `.opus`, and `.mp3` -> verifies default player launches cleanly.
   - In Recently downloaded: click Play on a downloaded item -> verifies default player launches cleanly.
2. **Show in Folder:**
   - In History tab: click "Show in folder" on a file with spaces and on a file with special Unicode characters (`｜ ： ⧸`) -> verifies File Explorer opens with the exact file selected and focused.
3. **Unassociated Extension (.zzz):**
   - Rename a downloaded file to `.zzz`, then click Play -> verifies toast says "No app is set to open this type of file." and Explorer opens revealing the file.
4. **Deleted / Missing File:**
   - Delete a downloaded file from Explorer, then click Play in History -> verifies "File not found. You can use Locate file." and row offers Locate option.
5. **Settings Folder Link:**
   - In Settings dialog: click "Open download folder" -> verifies File Explorer opens showing the download folder.

---

## Known Issues
- None. Phase 2 completed cleanly.
