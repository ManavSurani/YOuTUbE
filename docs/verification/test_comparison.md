# Test Comparison: Baseline (`62c8db1`) vs HEAD

- **Date:** 2026-10-10
- **Python Version:** 3.13.7
- **Pytest Version:** 9.1.1
- **Platform / OS:** Windows (win32)
- **Exact Command:** `python -m pytest -q -rf -p no:cacheprovider`

## Summary Counts

| Metric | Baseline (`62c8db1`) | Current `HEAD` | Delta |
|---|---|---|---|
| **Total Tests** | 241 | 311 | +70 |
| **Passed** | 240 | 308 | +68 |
| **Failed** | 1 | 3 | +2 |
| **Skipped** | 0 | 0 | 0 |
| **Errors** | 0 | 0 | 0 |

## Failing Tests and Verdicts

| Test Name | Baseline Result | HEAD Result | Verdict (pre-existing / new failure / fixed) |
|---|---|---|---|
| `tests/test_file_actions.py::test_exact_command_string_unicode` | FAILED | FAILED | pre-existing failure (P1) |
| `tests/test_check_scope.py::test_scope_checker_clean` | PASSED | FAILED | new failure (P8: tools/check_scope.py rejects approved scheduling exception for `download_manager.py`) |
| `tests/test_check_scope.py::test_scope_checker_final` | PASSED | FAILED | new failure (P8: tools/check_scope.py rejects approved scheduling exception for `download_manager.py`) |

## All Tests Comparison Summary by Module

| Test Module | Baseline (`62c8db1`) | HEAD | New Tests Added | Notes |
|---|---|---|---|---|
| `tests/test_app_updater.py` | 12 passed | 12 passed | 0 | Unchanged |
| `tests/test_check_scope.py` | 2 passed | 2 failed | 0 | P8 (addressed in Chunk 6) |
| `tests/test_close_event.py` | 3 passed | 3 passed | 0 | Dual-lane close logic verified |
| `tests/test_downloader.py` | 42 passed | 42 passed | 0 | Protected file caller tests pass |
| `tests/test_download_lanes.py` | 0 (did not exist) | 48 passed | +48 | Multi-lane queue & download manager tests |
| `tests/test_errors.py` | 10 passed | 10 passed | 0 | Unchanged |
| `tests/test_file_actions.py` | 1 failed, 6 passed | 1 failed, 6 passed | 0 | P1 (addressed in Chunk 3) |
| `tests/test_history_db.py` | 6 passed | 6 passed | 0 | Unchanged |
| `tests/test_history_tab.py` | 16 passed | 16 passed | 0 | Unchanged |
| `tests/test_info_fetcher.py` | 6 passed | 6 passed | 0 | Unchanged |
| `tests/test_network_monitor.py` | 6 passed | 6 passed | 0 | Unchanged |
| `tests/test_proc.py` | 3 passed | 3 passed | 0 | Protected file caller tests pass |
| `tests/test_queue.py` | 8 passed | 8 passed | 0 | Unchanged |
| `tests/test_queue_cards.py` | 0 (did not exist) | 12 passed | +12 | Phase D queue card tests |
| `tests/test_recent_list.py` | 0 (did not exist) | 10 passed | +10 | Phase B recently downloaded list tests |
| `tests/test_settings.py` | 4 passed | 4 passed | 0 | Unchanged |
| `tests/test_settings_dialog.py` | 13 passed | 13 passed | 0 | Unchanged |
| `tests/test_shortcut.py` | 6 passed | 6 passed | 0 | Unchanged |
| `tests/test_tool_manager.py` | 10 passed | 10 passed | 0 | Unchanged |
| `tests/test_url_tools.py` | 5 passed | 5 passed | 0 | Unchanged |

## Verdict Analysis (P2 Resolution)
1. **Baseline Failure (1 test):** `tests/test_file_actions.py::test_exact_command_string_unicode` failed at baseline `62c8db1` with `AssertionError: Path.resolve()` lowercasing `C:\Downloads` to `C:\downloads`. This confirms P1 was pre-existing at baseline.
2. **HEAD Failures (3 tests):**
   - `test_exact_command_string_unicode` (pre-existing P1).
   - `test_scope_checker_clean` & `test_scope_checker_final` (P8): Failed because `tools/check_scope.py` flags `app/core/download_manager.py` as an unauthorized edit, despite Rule R2 granting an approved scheduling exception for this milestone.
3. **No Unexplained Failures:** Aside from the 1 pre-existing failure (P1) and the 2 scope checker tests (P8), all 308 tests pass cleanly. Zero unexpected regressions exist.
