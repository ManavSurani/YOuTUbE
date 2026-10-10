# Baseline Test Suite Verification

- **Baseline Commit:** `62c8db12ad1d614fa12f4204446a705e2bc2624b`
- **Date:** 2026-10-09
- **Total Test Files:** 34
- **Total Collected Tests:** 241
- **Passed Tests:** 240
- **Failed Tests:** 1

---

## Known Pre-Existing Failures

| # | Test | Module | Failure Reason |
|---|---|---|---|
| 1 | `test_scope_checker_clean` | `tests/test_check_scope.py` | Legacy scope script `tools/check_scope.py --phase 11` was hardcoded for the 11-phase project against baseline `51a9d986` and flags untracked files in `plan/` as out-of-scope for Phase 11. `tools/check_scope.py --final` passes cleanly (0 protected files touched). |

---

## Test Results by Module

| # | Test File | Tests Passed / Total | Status |
|---|---|---|---|
| 1 | `tests/test_app_updater.py` | 12 / 12 | PASS |
| 2 | `tests/test_check_scope.py` | 1 / 2 | FAIL (1 known pre-existing) |
| 3 | `tests/test_close_event.py` | 3 / 3 | PASS |
| 4 | `tests/test_download_manager.py` | 3 / 3 | PASS |
| 5 | `tests/test_downloader.py` | 42 / 42 | PASS |
| 6 | `tests/test_errors.py` | 10 / 10 | PASS |
| 7 | `tests/test_file_actions.py` | 7 / 7 | PASS |
| 8 | `tests/test_history_db.py` | 6 / 6 | PASS |
| 9 | `tests/test_history_service.py` | 5 / 5 | PASS |
| 10 | `tests/test_history_tab.py` | 16 / 16 | PASS |
| 11 | `tests/test_info_fetcher.py` | 6 / 6 | PASS |
| 12 | `tests/test_jobs.py` | 2 / 2 | PASS |
| 13 | `tests/test_network_monitor.py` | 6 / 6 | PASS |
| 14 | `tests/test_phase2_integrity.py` | 2 / 2 | PASS |
| 15 | `tests/test_phase8_stress_edge_cases.py` | 4 / 4 | PASS |
| 16 | `tests/test_proc.py` | 3 / 3 | PASS |
| 17 | `tests/test_queue.py` | 8 / 8 | PASS |
| 18 | `tests/test_real_world_matrix.py` | 10 / 10 | PASS |
| 19 | `tests/test_recent_list.py` | 4 / 4 | PASS |
| 20 | `tests/test_requirements.py` | 1 / 1 | PASS |
| 21 | `tests/test_settings.py` | 4 / 4 | PASS |
| 22 | `tests/test_settings_dialog.py` | 13 / 13 | PASS |
| 23 | `tests/test_shortcut.py` | 6 / 6 | PASS |
| 24 | `tests/test_single_instance.py` | 2 / 2 | PASS |
| 25 | `tests/test_startup_repair.py` | 3 / 3 | PASS |
| 26 | `tests/test_tab_flow.py` | 16 / 16 | PASS |
| 27 | `tests/test_tab_looks.py` | 10 / 10 | PASS |
| 28 | `tests/test_tab_state_machine.py` | 4 / 4 | PASS |
| 29 | `tests/test_thumbnails.py` | 3 / 3 | PASS |
| 30 | `tests/test_tool_manager.py` | 10 / 10 | PASS |
| 31 | `tests/test_ui_kit.py` | 10 / 10 | PASS |
| 32 | `tests/test_ui_rules.py` | 2 / 2 | PASS |
| 33 | `tests/test_url_tools.py` | 5 / 5 | PASS |
| 34 | `tests/test_version_urls.py` | 1 / 1 | PASS |
