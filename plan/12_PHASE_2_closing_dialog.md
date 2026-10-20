# Phase 2 Plan: S2 Closing Dialog Text

## Goal
Satisfy requirement **S2b**:
- Update closing dialog text in `app/ui/main_window.py` to: `"A download is running. Quit now? It will continue the next time you open the app."`.
- Buttons and their roles remain unchanged (`Quit` / `AcceptRole`, `Keep downloading` / `RejectRole`).
- Choosing `Quit` preserves the active job in `queue_<kind>.json` and preserves its temporary directory.
- Choosing `Keep downloading` keeps the application open.

## Why
Previous wording asked `"A download is running. Quit and cancel it?"`, which falsely told users that the active download would be cancelled and lost, when in reality the app persists the active job and resumes it on the next launch.

## Allowed Files
- `app/ui/main_window.py` (closing-dialog wording only)
- `tests/test_close_event.py`
- `docs/verification/test_changes_2.md`
- `docs/verification/scope_exceptions.md`
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`
- `plan/12_PHASE_2_closing_dialog.md`

## Chunks
### Chunk 2.1: Tests First
- In `tests/test_close_event.py`:
  - Update `test_close_prompts_when_either_lane_active` to assert `dialog_text == "A download is running. Quit now? It will continue the next time you open the app."`.
  - See test fail against old wording.

### Chunk 2.2: Implementation
- In `app/ui/main_window.py`:
  - In `closeEvent()`:
    - Update `msg_box.setText("A download is running. Quit now? It will continue the next time you open the app.")`.
- See tests pass.

### Chunk 2.3: Verification & Log
- Run `python -m pytest tests/test_close_event.py`.
- Update `requirements_matrix_2.md` row S2b.
- Update `test_changes_2.md`.
- Update `scope_exceptions.md`.
- Update `autonomy_log_2.md`.
