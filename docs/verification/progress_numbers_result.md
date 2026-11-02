# Plan 20 Result: Progress Numbers

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Phase 1: 6 new tests added to `tests/test_ui_kit.py`. 5 failed for the expected reason (old output `2.5 GB / 5.0 GB`, `0.5 GB / 5.0 GB`, `500.0 KB / 95.4 MB`). The MB guard test passed.
- Phase 2: `tests/test_ui_kit.py` → **43 passed**. Full suite → **499 passed, 1 failed**.
  - The failure is `tests/test_check_scope.py::test_scope_checker_final`. It **already fails on the clean tree** (stash verified) because of older edits to `app/core/errors.py` and `app/core/thumbnails.py`. This plan did not cause it.
- No existing test was edited.

## Scope (`git diff --stat -- app tests`)
```
app/ui/kit/progress_card.py | 14 ++++++++++++-
tests/test_ui_kit.py        | 49 +++++++++++++++++++++++++++++++++++++++++++++
```
New files: `plan/20_PROGRESS_NUMBERS_PLAN.md` and this note.
Note: `android/gradle/wrapper/*` and `android/gradlew*` show as modified (a Gradle 8.11.1 → 9.7.1 wrapper upgrade). This was made outside this plan, most likely by the IDE, and was left untouched.

## Sample output (offscreen render of the real `ProgressCard`)
```
8.2 MB/s • 0.29 GB / 4.80 GB • ETA 01:20
9.7 MB/s • 1.02 GB / 4.80 GB • ETA 01:20
12.4 MB/s • 2.50 GB / 5.00 GB • ETA 01:20
3.1 MB/s • 30.0 MB / 87.3 MB • ETA 01:20
```

## Real download check (Task 3.2): pending, owner's PC
| Check | Result |
|---|---|
| Video over 1 GB shows `x.xx GB / y.yy GB`, counting up | pending |
| Video under 1 GB shows `xx.x MB / yy.y MB` | pending |
| Speed updates live | pending |
| Done state clears the line | pending |
