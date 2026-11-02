# Plan 24 Phase 4: History Never Blank on Switch

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- New (in `tests/test_theme_polish.py`): with 50 History rows, the page is fully shown within FAST + 100 ms of switching; fast switching Video → Audio → History leaves no page with a leftover fade effect. Both failed first.
- `test_theme_polish.py`: 21 passed.

## Done
- `_on_tab_changed`: the page's work (message resets, History refresh) runs first, then the fade starts.
- `_fade_in_page`: a fast switch stops the previous fade and removes its effect first.

## Outside the allowed list (needed for the gate)
- Reordering the fade wasn't enough. The page still sat at opacity 0 for about 0.9 s. The cause: `reload_history` detached old rows with `setParent(None)` while they were still visible, so Qt showed each one as its own hidden top-level window (50 windows per History open). **`app/ui/history_tab.py`: one line, `w.hide()` before `setParent(None)`.** This doesn't change how History loads. It only stops the stray windows.
- The Phase 3 title-bar hook moved from an app-wide event filter to `focusWindowChanged`. The filter saw every event and added 0.2 s to each History open. Every dialog and message box takes focus when it opens, so the result is the same (checked with a real on-screen message box: DWM light flag set). The Phase 3 dialog test now sends that focus signal, because offscreen test windows never take focus.

## Timing (50 rows, History open)
| | build | first paint |
|---|---|---|
| Before | 0.59 s | 0.90 s |
| After | 0.38 s | 0.08 s |

## Snapshot review (plan24_phase4)
- Automatic findings: **none**.
- History is filled in dark, light, and right after a live switch.

## Full suite
665 passed, 4 failed: the same known set as Phase 3. `test_theme_switch_stays_fast` fails only in the full run. Its time grows with leftover test windows (1 window 0.16 s, 10 windows 2.0 s, 30 windows 6.1 s), so a real app with one window switches in under 0.2 s. The suite itself now runs faster (8:51 vs 11:23).
