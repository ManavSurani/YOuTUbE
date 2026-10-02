# Phase 1 Verification: Engine Truth

**Date:** 2026-10-02  
**Result:** ✅ PASS — all gates cleared

---

## Automated Gate

| Check | Result |
|---|---|
| `test_no_subprocess_outside_proc` — R1 scan | ✅ PASS |
| Command builder tests (11 video + 8 audio) | ✅ PASS |
| Parser tests — YTPROG marker, speed, ETA, stage from vcodec/acodec | ✅ PASS |
| Parser B2 regression — old `download:` prefix not parsed | ✅ PASS |
| Path resolver — UTF-8 path file, fallback by video_id, ignores .part | ✅ PASS |
| Path resolver — Unicode filename (日本語, emoji) | ✅ PASS |
| Safe cancel — B4: .part in user Downloads untouched | ✅ PASS |
| Full suite — 93 tests | ✅ **93 passed, 0 failed** |

---

## Bugs Fixed

| Bug | Description | Fix |
|---|---|---|
| B1 | `--print` silenced all yt-dlp output | Removed `--print after_move:filepath` from both command builders |
| B2 | `download:` is a type-selector, not printed text; parser never matched | Replaced with `YTPROG\|` custom marker in `--progress-template` |
| B3 | Piped Windows stdout drops non-ASCII; file paths with `\|`, `:`, emoji broken | Added `--print-to-file after_move:filepath <utf8_file>` for path retrieval |
| B4 | `cleanup_temp_files()` scanned user's Downloads folder for `*.part` | Replaced with per-job TMP_DIR cleanup; user's Downloads folder never touched |
| B16 | Tests used hand-written fake `download:` lines that never matched real output | Tests now use real YTPROG format; B2 regression test added |

---

## Files Changed

| File | Change |
|---|---|
| `app/core/paths.py` | Added `TMP_DIR`, `HISTORY_DIR`, `purge_stale_tmp()` |
| `app/core/downloader.py` | Full rewrite — new progress template, YTPROG marker, print-to-file, safe TMP_DIR cancel |
| `app/main.py` | Added `purge_stale_tmp()` call at startup |
| `app/ui/video_tab.py` | Removed container arg, cleanup_temp_files; updated progress signal handler |
| `app/ui/audio_tab.py` | Removed embed checkboxes, cleanup_temp_files; updated progress signal handler |
| `tests/test_downloader.py` | Full rewrite — 42 real-format tests |
| `tests/conftest.py` | New — session-scoped HTTP server fixture for contract tests |
| `tests/test_network_monitor.py` | Updated B4 regression assertion |

---

## No-Terminal Check

- ✅ `grep -rn "subprocess" app/` returns hits ONLY in `app/core/proc.py`
- ✅ `--print` flag no longer in any command builder

---

## Sign-off

Phase 1 complete. Ready to proceed to Phase 2.
