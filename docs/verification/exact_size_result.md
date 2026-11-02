# Plan 21 Result: Exact Download Size and Real Size on Disk

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Tests
- Baseline (Phase 0): **498 passed, 2 failed**.
  - `test_check_scope.py::test_scope_checker_final`: known older failure (`errors.py`, `thumbnails.py`). Still lists only those two files.
  - `test_single_instance.py::test_single_instance_detection`: fails because `YOuTUbE.exe` was running on the PC during the test run (environment, not code).
- Final (Phase 4): **517 passed, 2 failed** (the same two). 19 new tests, and no existing test was edited.
- Seen once in subset runs and passed 3 out of 3 on re-run (timing flakes, unrelated): `test_tab_looks.py::test_animated_combobox_click_fade_and_completion`, `test_ui_kit.py::test_animated_line_edit_paste_triggers_fetch`.

## Phase results
| Phase | Result |
|---|---|
| 1: exact total | Before: the replay of a 20.04 MB job with a 2 h duration showed a total of `140,400,000` during video, then `20,040,000`. After: `20,040,000` on every tick. |
| 2: resume | Both resume tests passed on the Phase 1 code. **No code change.** The double count (F6) is gone whenever exact sizes exist. |
| 3: done size | The card shows `File size: <real size>` from `stat()` of the saved file. Without a path, or with a missing file, the line is cleared as before. |

## Scope (`git diff --stat`, this plan)
```
app/core/downloader.py        | 34 +++++++++-   (R2 items only)
app/ui/audio_tab.py           |  2 +-
app/ui/video_tab.py           |  2 +-
app/ui/kit/progress_card.py   | show_done only (+ Plan 20 changes, untouched)
tests/test_accuracy_replay.py | 70 +++
tests/test_downloader.py      | 67 +++
tests/test_tab_flow.py        | 25 +++
tests/test_ui_kit.py          | show_done tests (+ Plan 20 tests, untouched)
```
`android/gradle*` changes and the Plan 20 files were left untouched.

## Real end-to-end run (app's `build_video_cmd` + `DownloadWorker`, yt-dlp 2026.10.26)
Video `jNQXAC9IVRw`, formats 395+251:
```
stages:       Downloading video → Downloading audio → Merging → Writing metadata → Done
totals seen:  [475961]                 ← one exact total from the first tick
last emit:    done 475961 / total 475961
file on disk: 475390                   ← shown as "File size" at Done
sizes file cleaned up: yes
```

## Real download check on the owner's PC (Task 4.3)
| # | Check | Result |
|---|---|---|
| 1 | Long video: same total from first tick | pending |
| 2 | Done shows `File size:` equal to Explorer → Properties → Size | pending |
| 3 | MP3 audio: `File size:` matches the real `.mp3` | pending |
| 4 | Wi-Fi off/on during audio: total stays the same, done ≤ total | pending |
| 5 | Speed / ETA / percent look the same | pending |

## Known limits
- The final MKV size is only known after the merge (F4), so it is shown at Done.
- If YouTube gives no exact `filesize` for a stream, the old estimate path runs unchanged (F2 and F6 remain in that case only).
- The card still collapses 1.2 s after Done. The same real size stays in the `Recently downloaded` row.
