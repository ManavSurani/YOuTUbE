# Plan 21: Exact Download Size and Real Size on Disk

## Goal

The numbers under the progress bar must match the real file:

| Moment | Today (owner's screenshot) | After this plan |
|---|---|---|
| Downloading video | `… / 720.0 MB` (a guess) | `… / 690.1 MB` (exact, from the first tick) |
| Downloading audio | `685.0 MB / 690.1 MB` | `685.0 MB / 690.1 MB` (no change, already exact) |
| Done | line cleared, size never shown | `File size: 688.0 MB` (the real file on disk) |

- **During download** the total is the exact number of bytes that will be downloaded. It is fixed from the first tick and never jumps.
- **When done** the card shows the real size of the saved file, read from disk. This number matches Windows Explorer → Properties → "Size".

Nothing else changes: no layout, colors, fonts, order of the stats line, ETA, speed, or percent rules.

---

## Findings (checked in code and with the app's own yt-dlp `2026.10.26`)

### Why the total is wrong today

| # | Where | What happens | Effect |
|---|---|---|---|
| **F1** | `app/core/downloader.py` → `DownloadWorker.run()` → `remaining_estimate = duration_seconds * 17000` | While the **video** stream downloads, the audio size is **guessed** as 17,000 B/s × duration. | Main cause of `720 MB`. The guess is wrong for every video, and longer videos are off by more. |
| **F2** | `downloader.py` → `parse_line()` | If yt-dlp only knows `total_bytes_estimate` for a stream, the parser uses that estimate. | A second, smaller source of drift. |
| **F3** | `downloader.py` → audio stage → `overall_total = _finished_bytes + audio total` | Once audio starts, real video bytes plus real audio total are used. | This is why it "corrects" to `690.1 MB`. This part is already right. |
| **F4** | yt-dlp `--merge-output-format mkv` + `--embed-metadata` | After download, ffmpeg **remuxes** the two streams into one MKV. Container overhead changes, so the final file is a little smaller or bigger than the downloaded bytes. | `690.1 MB` downloaded becomes `688 MB` on disk. **No tool can know this number before the merge finishes.** It can only be read from disk afterwards. |
| **F5** | `progress_card.py` → `show_done()` | Clears the stats line. The real size is never shown on the card. | The owner and user never see the true size on the card. (`Recently downloaded` does show the real size, because `history_service.py` reads it with `stat()`.) |
| **F6** | Resume during audio → `download_manager` passes `initial_done_bytes = last overall_done` (video + partial audio) → becomes `_finished_bytes` | yt-dlp `--continue` then reports audio bytes that **include** the partial part again. | Suspected double count of the partial audio after a pause or offline resume. The fix in Phase 1 removes this path whenever exact sizes are known. Phase 2 proves it with a test. |

### Proof that exact sizes are available before the download starts

Probe on a small public video (format `395+251`), run in the scratchpad:

```
--print-to-file "video:%(requested_formats.0.filesize)s|%(requested_formats.1.filesize)s" sizes.txt
→ sizes.txt = 223779|252182          (exact video + exact audio = 475,961 B)
  progress lines still printed: 18   (progress is not silenced, unlike --print / B1)
  downloaded bytes reported:   223,779 + 252,182 = 475,961   ← matches exactly
  final zoo.mkv on disk:       475,390 B (with --embed-metadata) ← F4: remux changes size
```

Also checked:
- `%(info.requested_formats…)s` inside `--progress-template` returns `NA`. The progress template **cannot** carry the sizes, so `--print-to-file` is the only way.
- The top-level `filesize_approx` (475,961 here) is only an approximation in general, so it is **not** used.
- With the single-file fallback (`/b`) or audio-only, `requested_formats` is `NA`. Those cases already get the exact total from the stream itself, so the current logic stays for them.

### What "100% accurate" can honestly mean

| Number | Can it be exact? | How |
|---|---|---|
| Bytes to download (the total during download) | **Yes**, whenever YouTube reports an exact `filesize` for both chosen streams (the normal case) | Phase 1 |
| Size of the final file on disk | **Yes, but only once the file exists** | Phase 3 |
| Final file size *before* the merge | **No**, because ffmpeg decides it during the merge | Shown after Done instead |

If YouTube does not give an exact `filesize` for a stream (rare: some live or HLS formats), the app falls back to today's behaviour unchanged.

Units: the app uses 1024-based units (`MB` = MiB), the **same as Windows Explorer**. Compare with Properties → **Size**, not "Size on disk", which is rounded up to disk clusters.

---

## Rules for Claude (binding for this plan)

| # | Rule |
|---|---|
| **R1** | **Only the files in the Allowed list may change.** Every other file must show 0 lines changed. |
| **R2** | **`app/core/downloader.py` exception:** earlier plans protect this file. This plan allows it **only** for: one new template constant, one extra `--print-to-file` pair in `build_video_cmd()`, one helper `read_stream_sizes()`, one new attribute `_sizes_file`, the exact-size branch in the "whole-job done and total" block, and one `unlink` in `_cleanup_job_tmp()`. Nothing else in that file changes. |
| **R3** | **Build on what exists.** Reuse `_safe_int`, `TMP_DIR`, the `--print-to-file` pattern used for `.path`, the "read last non-empty line" idea from `resolve_final_path()`, and `ProgressCard._fmt_bytes()`. Do not add new classes, signals, settings, threads, widgets, colors, or styles. |
| **R4** | **Smallest change only.** No refactors, renames, reformatting, comment rewrites, or "while I'm here" cleanups. When exact sizes are missing, the old code path runs **unchanged** (no edits inside it). |
| **R5** | **Do not change** the signal signatures (`progress = Signal(float, str, str, int, int)`), the progress template `_PROG_TEMPLATE`, `parse_line()`, the percent caps (95 / 99.9), the monotonic rule, the stall watchdog, the audio command, or `build_audio_cmd()`. |
| **R6** | **Failing test first:** write each new test, run it, see it fail for the right reason, then change the code. |
| **R7** | **Tests are add-only.** Never delete, weaken, or rewrite an existing test or assertion. If an existing test must change, **stop and ask the owner**. |
| **R8** | **Known red test:** `tests/test_check_scope.py::test_scope_checker_final` already fails on the clean tree (see `docs/verification/progress_numbers_result.md`). Do not edit `tools/check_scope.py` to fix it. It must not get *worse*: no new failure messages caused by this plan except the expected `downloader.py` line, which is approved by R2. |
| **R9** | **Leave others' work alone:** the uncommitted Plan 20 changes (`progress_card.py`, `tests/test_ui_kit.py`, its plan and note) and the `android/gradle*` changes stay exactly as they are. Do not stash, revert, or commit them. |
| **R10** | **No extra docs** besides this plan and one result note: `docs/verification/exact_size_result.md`. |
| **R11** | **Commit only when the owner asks.** Stay on branch `fix/ui-pass`. |
| **R12** | **Loop rule:** once the owner approves this plan, run Phase 0 → 1 → 2 → 3 → 4 back to back. Each phase ends with its own **gate** (its tests plus the full suite). If the gate passes, go straight to the next phase. Stop and ask only if (a) a gate fails and the fix would break R1–R10, or (b) an existing test needs changing (R7). Send **one** summary at the end. |

**Allowed files (complete list):**

```
app/core/downloader.py                 (Phase 1: R2 exception only)
app/ui/kit/progress_card.py            (Phase 3: show_done only)
app/ui/video_tab.py                    (Phase 3: one argument in _on_manager_finished)
app/ui/audio_tab.py                    (Phase 3: one argument in _on_manager_finished)
tests/test_downloader.py               (new tests only)
tests/test_accuracy_replay.py          (new tests only)
tests/test_ui_kit.py                   (new tests only)
tests/test_tab_flow.py                 (new tests only)
docs/verification/exact_size_result.md (Phase 4 note)
plan/21_EXACT_SIZE_PLAN.md             (this plan)
```

---

## Phase 0 — Baseline (no code changes)

### Task 0.1: Record the starting point
```
git status --porcelain
pytest -q
```
- Expected: 499 passed, 1 failed (`test_scope_checker_final`, the known failure from R8). Write the numbers down for the Phase 4 note.
- If the numbers differ, write down the new baseline and continue, unless a failure is in a file this plan touches. In that case, stop and ask.

### Task 0.2: Read before writing
- `app/core/downloader.py`: `build_video_cmd`, `DownloadWorker.__init__`, `run()` (the "Calculate whole-job done and total" block), `_cleanup_job_tmp`, `resolve_final_path`.
- `tests/test_downloader.py` (command tests near lines 30–130, path-file tests near 300–440) and `tests/test_accuracy_replay.py` (the fixture replay style).

**Phase 0 gate:** baseline recorded. Go to Phase 1.

---

## Phase 1 — Exact Download Total From the First Tick (`downloader.py`)

### Task 1.1: Failing tests

**`tests/test_downloader.py`** (add at the end):

| Test | Checks |
|---|---|
| `test_video_cmd_prints_stream_sizes_file` | `build_video_cmd(..., job_id="j1")` contains a `--print-to-file` pair whose template has `requested_formats.0.filesize` and `requested_formats.1.filesize` and whose target ends with `j1.sizes` |
| `test_video_cmd_keeps_path_print` | the existing `after_move:filepath` pair is still present (guard) |
| `test_audio_cmd_has_no_sizes_print` | `build_audio_cmd` has no `.sizes` target (audio command is unchanged) |
| `test_read_stream_sizes_exact` | file `"18000000\|2040000\n"` → `(18000000, 2040000)` |
| `test_read_stream_sizes_uses_last_line` | file with two lines (a resume appends) → the values from the last non-empty line |
| `test_read_stream_sizes_na_or_missing` | `"NA\|2040000"`, `"NA\|NA"`, empty file, missing file → `(0, 0)` |
| `test_cleanup_removes_sizes_file` | `_cleanup_job_tmp()` deletes `TMP_DIR/<job>.sizes` (same style as the existing `.path` cleanup test, with `TMP_DIR` monkeypatched) |

**`tests/test_accuracy_replay.py`** (add at the end, reusing `MockFixtureProcess` and `fixtures/progress_dual.txt`):

| Test | Setup | Expected |
|---|---|---|
| `test_exact_sizes_total_fixed_from_first_tick` | write `18000000\|2040000` to a tmp sizes file and set `worker._sizes_file` to it; `duration_seconds=7200` (so the old 17,000 B/s guess would add about 122 MB) | **every** emit with `total > 0` has `total == 20_040_000`; percent never decreases; the last download emit has `done == 20_040_000` |
| `test_no_sizes_file_keeps_old_totals` | same fixture, `worker._sizes_file` points to a missing file | the emitted totals equal what the current code produces (record the list once from the unchanged code in this task, then assert it) |

Run:
```
pytest tests/test_downloader.py tests/test_accuracy_replay.py -q
```
The new tests must fail only because `.sizes` / `read_stream_sizes` / `_sizes_file` do not exist yet. The guard tests pass.

### Task 1.2: Code (in `app/core/downloader.py`, R2 scope)

1. **Constant** next to `_POST_TEMPLATE`:
   ```python
   # Exact stream sizes, written before the download starts (video+audio jobs)
   _SIZES_TEMPLATE = "video:%(requested_formats.0.filesize)s|%(requested_formats.1.filesize)s"
   ```
2. **`build_video_cmd()`**: directly after the existing `"--print-to-file", "after_move:filepath", str(path_file),` line, add:
   ```python
   "--print-to-file", _SIZES_TEMPLATE, str(TMP_DIR / f"{job_id or 'tmp'}.sizes"),
   ```
3. **Helper** `read_stream_sizes(sizes_file: Path) -> tuple[int, int]` next to `resolve_final_path()`: read the last non-empty line, split on `|`, and `_safe_int` the first two parts. Return them only if **both** are `> 0`, otherwise `(0, 0)`. Any read error → `(0, 0)`. About 10 lines.
4. **`__init__`**: `self._sizes_file = TMP_DIR / f"{self.job_id}.sizes"` next to `self._path_file`.
5. **`run()`**:
   - Before the `while` loop: `exact_video = exact_audio = 0`.
   - In the progress branch, before "Calculate whole-job done and total": if `self.is_dual_stream and not exact_video`, set `exact_video, exact_audio = read_stream_sizes(self._sizes_file)`. This only reads until it succeeds, then stops.
   - Wrap the **existing** dual-stream block in one new condition, leaving the old lines untouched in the `else`:
     ```python
     if self.is_dual_stream and exact_video and exact_audio:
         overall_total = exact_video + exact_audio
         overall_done = p.done_bytes if p.stage == "Downloading video" else exact_video + p.done_bytes
     elif self.is_dual_stream:
         ...existing code, unchanged...
     else:
         ...existing code, unchanged...
     ```
   - The existing "Never total < done" line, the percent formula, the caps, the audio interpolation, and the monotonic rule all stay as they are.
6. **`_cleanup_job_tmp()`**: add `self._sizes_file.unlink(missing_ok=True)` inside the same `try` as the `.path` unlink (or one identical `try` block right after it).

### Task 1.3: Run
```
pytest tests/test_downloader.py tests/test_accuracy_replay.py -q
pytest -q
```

**Phase 1 gate:** all new tests pass; the full suite matches the Phase 0 baseline plus the new tests (the only failure is still the R8 one). Go to Phase 2.

---

## Phase 2 — Resume Must Not Double Count (tests first; code only if a test fails)

### Task 2.1: Failing-or-guard tests in `tests/test_accuracy_replay.py`

| Test | Setup | Expected |
|---|---|---|
| `test_resume_mid_audio_with_exact_sizes` | sizes file `18000000\|2040000`; `initial_done_bytes=19_000_000`, `floor_percent=96.0`; replay only audio lines that start at `1000000` (as `--continue` reports them) up to `2040000` + `finished` | every emit has `done <= total == 20_040_000`; final `done == 20_040_000`; percent never decreases and never drops below 96 |
| `test_resume_appended_sizes_line` | sizes file has two identical lines (yt-dlp appends on each restart) | same totals as above |

### Task 2.2: Decide
- If both pass on the Phase 1 code (expected), **make no code change**. Record that F6 is fixed by Phase 1 whenever exact sizes exist.
- If one fails, make the smallest fix **inside the Phase 1 exact-size branch only** (R2, R4), then re-run.
- The old path without exact sizes is **not** changed in this plan (R4). Write F6 down as "remains only when exact sizes are missing" in the Phase 4 note.

### Task 2.3: Run
```
pytest tests/test_accuracy_replay.py -q
pytest -q
```

**Phase 2 gate:** green, same rules as Phase 1. Go to Phase 3.

---

## Phase 3 — Show the Real Size on Disk When Done

### Task 3.1: Failing tests

**`tests/test_ui_kit.py`** (add at the end):

| Test | Checks |
|---|---|
| `test_show_done_shows_real_file_size` | write a tmp file of 1,536 bytes → `card.show_done(out_dir=str(tmp_path), final_path=str(file))` → `stats_label.text() == "File size: 1.5 KB"`; stage text is still `Done. Saved to <folder>.` |
| `test_show_done_without_path_clears_stats` | `card.show_done(out_dir="C:/Downloads")` → `stats_label.text() == ""` (today's behaviour, guard) |
| `test_show_done_missing_file_clears_stats` | `final_path` points to a missing file → `stats_label.text() == ""` |

**`tests/test_tab_flow.py`** (add at the end, using the file's existing tab fixture style):

| Test | Checks |
|---|---|
| `test_video_tab_done_passes_final_path` | `_on_manager_finished(job, "C:/x/file.mkv")` calls `progress_card.show_done` with `final_path="C:/x/file.mkv"` |
| `test_audio_tab_done_passes_final_path` | same for the audio tab |

### Task 3.2: Code

1. **`app/ui/kit/progress_card.py` → `show_done()`**: change the signature to `show_done(self, out_dir: str = "", final_path: str = "")`. Replace `self.stats_label.setText("")` with:
   ```python
   size = Path(final_path).stat().st_size if final_path and Path(final_path).is_file() else 0
   self.stats_label.setText(f"File size: {self._fmt_bytes(size)}" if size else "")
   ```
   `Path` is already imported. No other line changes. `_fmt_bytes` is reused, so the format is the same as in `Recently downloaded` and History.
2. **`app/ui/video_tab.py` → `_on_manager_finished()`**: `self.progress_card.show_done(out_dir=job.output_dir, final_path=final_path)`.
3. **`app/ui/audio_tab.py` → `_on_manager_finished()`**: the same one-argument change.

Note: the card still collapses after 1.2 s (`_collapse_timer`, unchanged). The same real size stays visible in the `Recently downloaded` row, which already uses `stat()`.

### Task 3.3: Run
```
pytest tests/test_ui_kit.py tests/test_tab_flow.py -q
pytest -q
```

**Phase 3 gate:** green, same rules. Go to Phase 4.

---

## Phase 4 — Full Verification

### Task 4.1: Full suite
```
pytest -q
```
Expected: the Phase 0 baseline plus all new tests pass. The only failure is the R8 one.

### Task 4.2: Scope check
```
git diff --stat
git status --porcelain
```
- Only files from the Allowed list, plus the untouched Plan 20 / gradle changes (R9), may appear.
- Review `git diff app/core/downloader.py`: every changed line must be one of the R2 items.
- Any other file → revert it before continuing.

### Task 4.3: Real download check (owner's PC, `python -m app.main`)

| # | Action | Pass when |
|---|---|---|
| 1 | Download a long video (the one from the screenshot) | The total shows the **same** value (for example `690.1 MB`) from the first tick of "Downloading video" through "Downloading audio". It never shows a bigger number first. |
| 2 | Same download, at Done | The card shows `File size: X MB`, and X equals Explorer → Properties → Size of the saved `.mkv` (to 0.1 MB). The `Recently downloaded` row shows the same X. |
| 3 | Download audio as MP3 | The stats line works as before. At Done, `File size:` matches the real `.mp3` in Explorer (the converted size, which differs from the download size). |
| 4 | Start a video, turn Wi-Fi off during **audio**, then back on (resume) | The total stays the same, `done` never goes above the total, and the bar never goes back. |
| 5 | Speed / ETA / percent | Same look and behaviour as before. |

### Task 4.4: Result note
Write `docs/verification/exact_size_result.md` with:
- the baseline and final `pytest` counts
- `git diff --stat`
- the Phase 2 decision (code change or none)
- the Task 4.3 table (pass, fail, or pending per row)
- known limits: (a) the final MKV size is known only after the merge (F4); (b) when YouTube gives no exact `filesize`, the old estimate path runs (F2 and F6 stay in that case only)

**Phase 4 gate:** send the owner one summary. Commit only if the owner asks (R11).

---

## Out of Scope (do NOT do)

- Predicting the post-merge MKV size before the merge (not possible, F4).
- Changing the single-stream or audio-only total logic, `parse_line()`, the estimate threshold, or `_PROG_TEMPLATE`.
- Fixing F6 in the old no-exact-size path.
- Showing sizes in queue rows, changing the collapse timer, the stats line order, units, colors, or fonts.
- Using `filesize_approx` anywhere (it is an estimate, not exact).
- Editing `tools/check_scope.py`, `download_manager.py`, `info_fetcher.py`, `jobs.py`, or any history file.
