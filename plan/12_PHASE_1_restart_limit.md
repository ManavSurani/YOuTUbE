# Phase 1 Plan: S2 Active-Job Restart Limit

## Goal
Satisfy requirement **S2a**:
- An interrupted active job is restored at most 2 times.
- The third restore sends it to the failed list with the exact message: `"The app closed several times while this download was running. Press Retry."`.
- An entry saved with `restarts=0` restores and becomes `restarts=1`.
- An entry saved with `restarts=1` restores and becomes `restarts=2`.
- An entry saved with `restarts=2` goes to the failed list and is not queued.
- A missing `restart_count` key is treated as 0.
- User Cancel or completed jobs are never restored.

## Why
When the app or system repeatedly crashes during a specific video download, the app must not infinitely attempt to restart. Decision D1 sets the maximum restores to 2; on the 3rd attempt, the job must fail gracefully with the plain-language message.

## Allowed Files
- `app/core/download_manager.py`
- `tests/test_download_manager.py`
- `docs/verification/test_changes_2.md`
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`
- `plan/12_PHASE_1_restart_limit.md`

## Chunks
### Chunk 1.1: Tests First
- In `tests/test_download_manager.py`:
  - Update `test_active_job_restart_limit_moves_to_failed` to assert limit of 2 (fails when saved with `restart_count=2`).
  - Add comprehensive test `test_active_job_restart_limit_boundaries` testing:
    - `restart_count=0` -> restored, tracked count = 1.
    - `restart_count=1` -> restored, tracked count = 2.
    - `restart_count=2` -> moved to failed with message `"The app closed several times while this download was running. Press Retry."`, not in waiting queue.
    - Missing `restart_count` -> treated as 0, restored with count = 1.
    - Cancelled / finished job -> never restored.
- Verify test fails against current implementation (which allows 3 restarts).

### Chunk 1.2: Implementation
- In `app/core/download_manager.py`:
  - In `_load_persisted_queue()`:
    - Change threshold: `if restart_count < 2:` (was `< 3`).
    - Change failure reason: `reason = "The app closed several times while this download was running. Press Retry."`.
- Verify tests pass.

### Chunk 1.3: Verification & Log
- Run phase tests: `python -m pytest tests/test_download_manager.py`.
- Run full suite: `python -m pytest tests/ -q -rf -p no:cacheprovider`.
- Record test changes in `docs/verification/test_changes_2.md`.
- Record scope exception in `docs/verification/scope_exceptions.md`.
- Update `requirements_matrix_2.md` row S2a.
- Update `autonomy_log_2.md`.
