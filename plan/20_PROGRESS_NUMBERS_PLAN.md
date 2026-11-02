# Plan 20: Progress Numbers — "2.50 GB / 5.00 GB" and Live Speed

## Goal

Make the numbers under the progress bar easy to read while a video downloads:

```
12.4 MB/s • 2.50 GB / 5.00 GB • ETA 01:20
            ^^^^ counts up live    ^^^^ stays fixed
```

- The downloaded amount (`2.50`) grows live as the file downloads.
- The total (`5.00 GB`) stays fixed.
- **Both numbers always use the same unit** (the unit of the total), so the left number counts up smoothly instead of jumping from `980.0 MB` to `1.0 GB`.
- The speed (`12.4 MB/s`) keeps updating live with every progress tick, as it does now.

Nothing else in the app changes: no layout, colors, fonts, order of the line, ETA, or progress bar drawing.

---

## Current Behaviour (read from code)

| Item | Where | What happens today |
|---|---|---|
| Stats line | `app/ui/kit/progress_card.py` → `_update_stats_label()` | Builds `speed • done / total • ETA` on every progress tick |
| Size formatting | `progress_card.py` → `_fmt_bytes()` | Formats **each number by itself**, so done and total can show **different units**: `512.0 MB / 5.0 GB`, then `1.0 GB / 5.0 GB` |
| Decimals | `_fmt_bytes()` | Always 1 decimal, so GB sizes move in big steps (`2.4 GB` → `2.5 GB`, about 100 MB per step), and the number looks stuck |
| Speed | `app/core/downloader.py` → `_fmt_speed()` → signal → `set_progress(speed=…)` | Already live (`12.4 MB/s`), with a sticky last value and a `-- MB/s` placeholder |
| Live updates | `video_tab.py` / `audio_tab.py` → `_on_manager_progress()` → `progress_card.set_progress()` | Already wired. Every yt-dlp tick updates the line |

**Root cause:** the only problem is how the size pair is formatted. The data flow (bytes, speed, signals) is correct already.

---

## Rules for Claude (binding for this plan)

| # | Rule |
|---|---|
| **R1** | **One code file only:** `app/ui/kit/progress_card.py`. No other application file may be opened for editing. |
| **R2** | **One test file only:** `tests/test_ui_kit.py`, and only to **add** new tests. Never delete, weaken, or rewrite an existing test or assertion. |
| **R3** | **Do not touch** `downloader.py`, `download_manager.py`, `video_tab.py`, `audio_tab.py`, `queue_widget.py`, `theme.py`, `tools/check_scope.py`, or any other file. The speed string from `downloader.py` stays exactly as it is. |
| **R4** | **Smallest change only.** Change only the size part of `_update_stats_label()` plus one small helper. No new classes, widgets, signals, settings, colors, fonts, or styles. No refactors, renames, or "while I'm here" cleanups. |
| **R5** | **Keep the line's shape:** order `speed • size • ETA`, separator ` • `, placeholders `-- MB/s`, `calculating…`, `ETA --:--`, and the `stats=` override all stay exactly as they are. |
| **R6** | **Keep `_fmt_bytes()` unchanged.** It is still used when the total is unknown (done-only display). |
| **R7** | **Failing test first:** write each new test, see it fail for the right reason, then make the code change. |
| **R8** | **All existing tests must pass unchanged.** If an existing test needs editing, stop and ask the owner. |
| **R9** | **No other docs or logs** besides this plan and one short result note in `docs/verification/` (Phase 3). |
| **R10** | **Commit only when the owner asks.** Work stays on branch `fix/ui-pass`. |
| **R11** | **Run the whole plan as one loop.** Once the owner approves the plan, run Phase 1 → Phase 2 → Phase 3 back to back without asking between phases. Treat each phase gate as a self-check: if it passes, go straight to the next phase. Stop and ask only when (a) a gate fails and the fix would break R1–R9, or (b) an existing test needs editing (R8). Send one final summary at the end. |

**Allowed files (complete list):**

```
app/ui/kit/progress_card.py                      (code)
tests/test_ui_kit.py                             (new tests only)
docs/verification/progress_numbers_result.md     (result note, Phase 3)
plan/20_PROGRESS_NUMBERS_PLAN.md                 (this plan)
```

---

## Phase 1 — Tests First

### Task 1.1: Read before writing
- Read `app/ui/kit/progress_card.py` (`_update_stats_label`, `set_progress`, `_fmt_bytes`).
- Read the existing stats tests in `tests/test_ui_kit.py` (around lines 356–489) so the new tests match their style.

### Task 1.2: Add failing tests to `tests/test_ui_kit.py`
Add these tests at the end of the file:

| Test | Input (done, total) | Expected size part |
|---|---|---|
| `test_size_pair_same_unit_gb` | 512 MiB, 5 GiB | `0.50 GB / 5.00 GB` |
| `test_size_pair_counts_up_in_gb` | 2.5 GiB, 5 GiB | `2.50 GB / 5.00 GB` |
| `test_size_pair_mb_unchanged` | 50 MiB, 100 MiB | `50.0 MB / 100.0 MB` (same as today) |
| `test_size_pair_small_done_uses_total_unit` | 500 KiB, 95.4 MiB | `0.5 MB / 95.4 MB` |
| `test_full_line_with_gb` | speed `12.4 MB/s`, ETA `01:20`, 2.5 GiB / 5 GiB | `12.4 MB/s • 2.50 GB / 5.00 GB • ETA 01:20` |
| `test_live_update_changes_done_only` | two ticks: 2.5 GiB then 2.6 GiB of 5 GiB, speeds `10.0 MB/s` then `11.2 MB/s` | done part and speed change; `5.00 GB` stays the same |

### Task 1.3: Run tests and confirm they fail
```
pytest tests/test_ui_kit.py -q
```
- The new GB tests must **fail** because the current output is `512.0 MB / 5.0 GB` and `2.5 GB / 5.0 GB`.
- The MB test (`test_size_pair_mb_unchanged`) is expected to **pass already**. It guards against regressions.
- All old tests still pass.

**Phase 1 gate:** the new tests fail for the expected reason only.

---

## Phase 2 — The Code Change (`app/ui/kit/progress_card.py` only)

### Task 2.1: Add one helper, `_fmt_pair(done, total)`
A `@staticmethod` next to `_fmt_bytes()`:
- Pick the unit from **total** (B / KB / MB / GB / TB, base 1024, the same as `_fmt_bytes`).
- Format **both** numbers in that unit.
- Decimals: **2 for GB and TB** (so the number moves every ~10 MB and visibly counts up), **1 for KB and MB** (so today's MB output stays identical).
- Return `"<done> <unit> / <total> <unit>"`.

Roughly 10–12 lines. Nothing else is added.

### Task 2.2: Use it in `_update_stats_label()`
Replace this one line:
```python
size_slot = f"{self._fmt_bytes(done)} / {self._fmt_bytes(total)}"
```
with:
```python
size_slot = self._fmt_pair(done, total)
```
No other line in the method changes. `total = max(self._last_total, done)` stays as it is, so the done value can never show bigger than the total.

### Task 2.3: Run the tests
```
pytest tests/test_ui_kit.py -q
pytest -q
```
- All new tests pass.
- All existing tests pass **unchanged** (see R8).

**Phase 2 gate:** the full test suite is green.

---

## Phase 3 — Verify Scope and the Real App

### Task 3.1: Scope check
```
git diff --stat
git status --porcelain
```
Expected: only the four allowed files appear. If any other file is listed, revert it before going further.

### Task 3.2: Real download check (owner's PC)
Run the app (`python -m app.main`) and download:
1. **A large video (over 1 GB):** the line shows `x.xx GB / y.yy GB`. The left number counts up smoothly, and the total stays fixed.
2. **A small video or audio file (under 1 GB):** the line shows `xx.x MB / yy.y MB`, exactly as it looks today.
3. **Speed:** the speed changes live while downloading and shows `-- MB/s` or the last value during a stall, the same as today.
4. **Done state:** the line clears and shows `Done. Saved to <folder>.` as it does today.

### Task 3.3: Short result note
Write `docs/verification/progress_numbers_result.md` with:
- the test command output summary (passed count)
- the `git diff --stat` output
- the results of Task 3.2 (pass or fail per item)

**Phase 3 gate:** send the owner one summary. Commit only if the owner asks (R10).

---

## Out of Scope (do NOT do)

- Changing how speed is calculated or formatted (`downloader.py` is protected).
- Showing size or speed in queue rows (`queue_widget.py`).
- Changing the progress bar look, colors, font size, layout, or the order of the line.
- Changing ETA behaviour or the stall and sticky logic.
- Any refactor, rename, or cleanup in `progress_card.py` beyond Tasks 2.1–2.2.
