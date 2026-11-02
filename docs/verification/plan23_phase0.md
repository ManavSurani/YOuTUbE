# Plan 23 Phase 0: Baseline, .gitignore, Secrets Out, Snapshot Tool

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Baseline: 553 passed, 1 failed (known `test_check_scope.py::test_scope_checker_final`).
- After: **561 passed**, 1 failed (same known). New: `tests/test_repo_hygiene.py` (8). It failed 8/8 before the change and passes 8/8 after.

## Changes
- `.gitignore`: Android local files and keystores, IDE folders, `.env`, coverage output, `*.part` / `*.ytdl`, `docs/ui_audit/` (local snapshots and audit images).
- `android/app/release.keystore`: no longer tracked (`git rm --cached`; the file stays on disk).
- `android/app/build.gradle.kts`: signing values are read from git-ignored `android/keystore.properties`. With no file, the release build is unsigned. No passwords remain in tracked files. The local `keystore.properties` was created with the current values, so the owner's builds keep working.
  - Not compiled here (no Android SDK in this session). Check with `gradlew assembleRelease` on the owner's PC.
- `tools/ui_snapshots.py`: renders 10 screens × dark/light into `docs/ui_audit/snapshots/<label>/` using a throwaway app-data copy. Phase 0 run: 20 PNGs, no errors.

## Open owner decision (Task 0.4)
The old key and password were public from 2026-10-02 to now. Rotate (A), new key (B), or keep (C); history purge yes/no.

## Scope
`.gitignore`, `android/app/build.gradle.kts`, `android/app/release.keystore` (untracked), `tests/test_repo_hygiene.py`, `tools/ui_snapshots.py`, `docs/ui_ux_audit.md`, `plan/23_UI_UX_PLAN.md`, this note. The owner's `android/gradle/wrapper/*` changes were left untouched and not committed.
