# Plan 23 Phase 6: Motion and Delight

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Before: 623 passed (+ known failures).
- After: **634 passed**; failures: the known scope test plus `test_tab_looks` combobox / line-edit-cycles.
- New: `tests/test_motion.py` (11), all failing first.
- Flaky pair investigation: `test_ui_kit.py` + `test_tab_looks.py` run together fail 2 tests (paste-triggers-fetch reads an empty system clipboard; line-edit-cycles counts leftover context menus). The same two fail on `c7c197f` (**before Plan 23**), pass on some later commits, and always pass alone. This is an existing order/clipboard flake, not caused by this plan.

## Done
| Task | Result |
|---|---|
| 6.1 | Motion tokens in `kit/anim.py`: FAST 120 / BASE 180 / SLOW 260 / CELEBRATE 300 (+ SHIMMER_MS 1600 for the ambient loop). Every `setDuration` in `app/ui` uses a token (tested); `create_animation` defaults to BASE. Reduce motion skips all of them. |
| 6.4 | Progress bar glides to each new value (BASE) while `value()` stays exact for logic and tests; resets and reduced motion jump at once. The shimmer stops during stalls / merging (no speed) and restarts when bytes move. |
| 6.5 | One soft white glow over the bar when a download finishes (CELEBRATE). |
| 6.7 | Invalid link: the input shakes 3 × 4 px (BASE), on top of the red border from Phase 3. |
| 6.8 | Tab content cross-fades in (FAST); the opacity effect is removed when done. |
| 6.10 | `02_DESIGN_SYSTEM.md` §4 Motion rewritten with the token table; §6 keeps "no bounce/glow" except the single done glow. |

## Not done (reported at the end)
- 6.2 Loading skeleton: `test_tab_flow::test_tab_state_visibility_contract` requires the info card hidden in FETCHING.
- 6.3 Card → progress morph, 6.6 list slide-ins: the queue and recent list rebuild all rows on each change, so "new row" motion needs a larger refactor; left out to keep changes small.
- 6.9 Splash bar animation: `test_splash_update` reads the bar value right after each update.

## Scope
`app/ui/kit/anim.py`, `app/ui/kit/progress_card.py`, `app/ui/kit/checkbox.py`, `app/ui/kit/toast.py`, `app/ui/header.py`, `app/ui/history_tab.py`, `app/ui/splash.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/main_window.py`, `02_DESIGN_SYSTEM.md` (§4/§6 text only), `tests/test_motion.py`, this note.

## Snapshot review (phase6)
Still frames are unchanged from Phase 5 (bars settle at their exact values); motion verified through the tests above.
