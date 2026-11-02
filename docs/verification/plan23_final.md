# Plan 23 Final Verification: UI/UX Overhaul + Repo Hygiene

Date: 2026-11-02 · Branch: `fix/ui-pass` (7 phase commits, not pushed)

## Automated
- Full suite: **634 passed**. Known failures only: `test_check_scope::test_scope_checker_final` (old) and the `test_tab_looks` combobox / line-edit-cycles pair, which fails on `c7c197f` too (before Plan 23) and passes alone.
- New tests in this plan: about 90 (`test_repo_hygiene`, `test_theme_tokens`, `test_light_mode`, `test_p0_fixes`, `test_core_flow`, `test_history_settings`, `test_motion`).
- Four old tests updated with the owner's approval (history times, offline popup, queue failed group, done text); see `plan23_phase3.md`.
- Hygiene: no keystore, `.jks`, or signing password tracked; no files under `docs/ui_audit/` tracked.
- DPI: all 10 screens rendered at `QT_SCALE_FACTOR=1.5` in both themes; no clipped text.

## Audit Top 12 (docs/ui_ux_audit.md §2)
| # | Problem | Status |
|---|---|---|
| 1 | Light mode unusable | **Fixed** (tokens everywhere, live theme switch, light title bar) |
| 2 | History shows UTC times | **Fixed** (local + "Today, 9:51 AM" / "Yesterday" / "17 Oct") |
| 3 | History horizontal scrollbar | **Fixed** (elided titles, h-scroll off) |
| 4 | Offline modal popup | **Fixed** (inline note; owner-approved test update) |
| 5 | No size before download | **Fixed** (≈ size per quality in the dropdown) |
| 6 | Stale card after an error | **Fixed** (card cleared; red input border + shake) |
| 7 | "Up next" counts failed items | **Fixed** ("Up next (N)" + "Failed (M)" with Retry all) |
| 8 | Empty bars on waiting rows | **Fixed** |
| 9 | Done state wasted | **Fixed** (4 s, Open / Show in folder, done glow) |
| 10 | Huge banner buttons | **Fixed** (compact text buttons) |
| 11 | No keyboard flow | **Fixed** (Ctrl+V, Enter, Ctrl+1/2/3, Ctrl+F, Ctrl+, , Esc, Space) |
| 12 | Uneven edges / layout shift | **Fixed** (one edge; scrollbar width reserved) |

Also: History groups, "⋯" menus, title/channel search with count, neutral chips; two-column Settings (system theme, reduce motion, download defaults, start with Windows, notifications, auto-fetch, open log folder); tray menu with pause/resume; motion tokens.

## Not done (needs an owner decision or a bigger change)
| Item | Reason |
|---|---|
| "Add to queue" always visible; action row inside the card | Old state-contract tests require the current layout/visibility |
| Undo delete instead of the confirm dialog | Old history delete-flow tests |
| Close to tray while downloading | Keeps the tested close/quit flow unchanged |
| Loading skeleton while fetching | Old test requires the card hidden while fetching |
| Card → progress morph, row slide-ins, animated splash bar | Needs list refactors / old tests read values instantly |
| Windows taskbar progress, actionable toast buttons | Out of scope (no Qt 6 API / extra packages) |

## Owner actions pending
1. Real-PC check after the release (paste/auto-fetch, sizes, pause/resume, done buttons, history times, theme switch, tray menu).
2. Merge `fix/ui-pass` → `main`, push, release (`python tools/release.py --notes ...`). Needs a yes (R11).
3. Android key rotation (decision A), on the next Android build.

## Scope
`git diff --stat main...fix/ui-pass`: 48 files, +3709 / −406. All in `app/`, `tests/`, `tools/`, `docs/`, `plan/`, `.gitignore`, `02_DESIGN_SYSTEM.md`, `android/app/build.gradle.kts` (signing block only). The owner's `android/gradle/wrapper/*` edits were never committed.
