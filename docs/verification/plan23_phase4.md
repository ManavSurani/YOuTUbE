# Plan 23 Phase 4: Core Flow Upgrades

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Before: 596 passed, 1 failed (known scope test).
- After: **611 passed**, 2 failed: the known scope test and `test_tab_looks::test_animated_combobox_click_fade_and_completion`, which passed 3/3 in isolation (known timing flake, R14).
- New: `tests/test_core_flow.py`, failing first (import error, then per feature).

## Done
| Task | Result |
|---|---|
| 4.1 | `info_fetcher.build_quality_sizes` (approximate: best video at or below the height + best audio) → `VideoInfo.quality_sizes`. Dropdown shows `1080p · ≈ 690.1 MB`; the job still gets the clean label (`QUALITY_LABEL_ROLE`). Always marked "≈", because yt-dlp may rank a different codec of the same height. |
| 4.2 | Info card: surface card, 160×90 thumbnail slot (placeholder until loaded), title max 2 lines (full title in tooltip), "Saves to <folder> · Change" (opens Settings). |
| 4.4 | `DownloadManager.pause_active()` / `resume_active()` / `is_paused` reuse the offline pause path; a network reconnect never resumes a user pause. Pause/Resume icon button on the progress card; Space toggles it. |
| 4.5 | Done state stays 4 s (held while hovered) with **Open** and **Show in folder** (existing `file_actions`). |
| 4.6 | Window activation offers a copied YouTube link once ("Use copied link · …"). |
| 4.7 | Auto-fetch on paste already existed; covered by a test now. |
| 4.8 | Drag & drop of a YouTube link/text onto the window fills the current tab (History → Video). |
| 4.9 | Shortcuts: Ctrl+1/2/3, Ctrl+F, Ctrl+, , Ctrl+V (outside text boxes), Esc, Space (keeps Space on focused buttons/dropdowns); Enter downloads when the shown video is ready. |
| 4.10 | Progress card falls back to the job's thumbnail bytes when no cached thumbnail exists. |

## Not done (blocked by existing tests, reported to the owner at the end)
- 4.3 "Add to queue always visible": `test_tab_flow::test_tab_state_visibility_contract` and `test_tab_state_machine` (`no_job` case) require it hidden in Ready with no running job.
- 4.2 action row inside the card: moving the buttons into the card would hide Cancel/Add to queue whenever the card is hidden, which breaks the same state contract. The row stays under the card.
- 4.8 dashed drop outline and `.url` files: not added, to keep the change small.

## Scope (incl. plan exceptions)
`app/core/info_fetcher.py` (exception: `build_quality_sizes` + `quality_sizes` field only), `app/core/download_manager.py` (exception: pause/resume methods + 2 guards), `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/main_window.py`, `app/ui/kit/progress_card.py`, `app/ui/kit/thumb_label.py` (`set_image_bytes`), `app/ui/kit/buttons.py` ("pause" icon), `tests/test_core_flow.py`, this note.

## Snapshot review (phase4)
- Ready: card on `surface`, thumbnail slot with placeholder, destination line with a blue "Change" link; readable in both themes.
- Downloading: pause icon at the right of the progress card title.
- Done: "Saved to Downloads"; Open/Show in folder appear only when the file exists (covered by test; the tool does not create a file).
