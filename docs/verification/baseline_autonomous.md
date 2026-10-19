# Autonomous Baseline Test Report

**Start Commit:** `cdfed4e` (`cdfed4e1dde0fa66fd9adb2fdbdd58bcd4529ef2`)  
**Date:** 2026-10-20  
**Environment:** Windows (win32), Python 3.13.7, PySide6 6.8.0.2, pytest-9.1.1  

## Test Results

1. **Working Tree (`c:\Vs\YOuTUbE`):**
   - Command: `python -m pytest -q -rf -p no:cacheprovider`
   - Total Collected: 429
   - Passed: 429
   - Failed: 0
   - Execution Time: 70.65s

2. **Clean Worktree (`..\YOuTUbE_base` at commit `cdfed4e`):**
   - Command: `python -m pytest -q -rf -p no:cacheprovider`
   - Total Collected: 429
   - Passed: 429
   - Failed: 0
   - Execution Time: 66.96s

## Pre-existing Failures Check
- Rule R8 mentions `tests/test_file_actions.py::test_exact_command_string_unicode`.
- Verified at baseline: Passed cleanly (`tests/test_file_actions.py . [100%]`).
- No pre-existing test failures exist at baseline. Every subsequent test failure must be resolved.
