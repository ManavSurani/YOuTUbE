# Plan 23 Phase 3: Fix What's Broken (P0)

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Before: 579 passed, 1 failed (known scope test).
- After: **596 passed**, 1 failed (same known). New: `tests/test_p0_fixes.py` (17), 15 failing before the code (the left-edge test already passed after Phase 2).
- The rewritten scrollbar test was proven failing on the old tab code (stash check).

## Owner-approved test updates (2026-11-02, R6)
Four old tests locked the old behaviour. The owner approved updating them; each still checks the new behaviour exactly:
| Test | Old expectation | New expectation |
|---|---|---|
| `test_history_tab::test_history_row_shows_date_and_time` | raw `2026-10-02 14:35` (UTC) | `format_date_str(...)` friendly local text; the raw ISO text is absent |
| `test_network_monitor::test_main_window_network_transitions` | "Internet is off" popup | no popup; the `offline_note` under the link box is visible while offline, hidden online |
| `test_queue` (2 tests with a failed item) | failed counted as "Up next (1)" | "Failed (1)" header, no "Up next", "Clear failed" still present |
| `test_ui_kit::test_show_done_shows_real_file_size` | "Done. Saved to X." + "File size: 1.5 KB" | one line "Saved to X · 1.5 KB", stats empty |

## Changes (by task)
- 3.1 `format_date_str`: UTC → local, "Today, 9:51 AM" / "Yesterday, …" / "17 Oct" / "17 Oct 2025".
- 3.2 New `kit/elided_label.py` (`ElidedLabel`) for titles in queue, recent, history, and progress card; history horizontal scroll off.
- 3.3 Offline: popup removed; tabs show "You're offline. Downloads will resume automatically."
- 3.4 Header status only shown while offline.
- 3.5/3.6 Invalid link: the old card is cleared; red input border + message stay until the text changes; `reset_messages` clears both.
- 3.7 Queue: "Up next (N)" waiting only; "Failed (M)" with "Retry all" and "Clear failed".
- 3.8 Queue rows hide their (always empty) progress bar.
- 3.9 Update banner: label + stretch + text buttons (no filled blue button), compact bar.
- 3.10 Content width constant: right margin equals the scrollbar width while the scrollbar is hidden (no grey always-on bar).
- 3.11 Files under 1 KB show "Incomplete file" (recent: play hidden; history: meta tag).
- 3.12 Audio placeholder "Paste a YouTube link to save its audio"; "Best original" shows "Original (Opus)" etc. from the file type; Done text "Saved to Downloads · 688.2 MB".

## Scope note (plan amendment)
Beyond the Phase 3 list: `app/ui/kit/elided_label.py` (new widget needed for 3.2) and `app/ui/kit/progress_card.py` (elided title + Done text). Both are UI kit files, with no engine changes.

## Snapshot review (phase3)
- Dark + light: header shows no status online and an "Offline" pill offline; compact banner; queue groups without empty bars; history local relative times, "Original (Opus)", "Incomplete file"; no horizontal scroll.
- Still open for later phases: history rows are airy (Phase 5), and the info card has no surface or thumbnail slot styling (Phase 4).
