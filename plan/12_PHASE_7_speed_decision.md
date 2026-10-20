# Phase 7: C1 Speed Decision Document

## Goal
Document the empirical speed decision in `docs/verification/speed_decision.md` according to Decision D6, collating all benchmark measurements from `docs/verification/parallel_progress_speed_report.md` into alternating pairs with calculated medians and speedup percentages. Verify that `app/core/downloader.py` (`build_video_cmd` and `build_audio_cmd`) contains the exact flags specified by the decision.

## Why
Status report item C1 was marked PARTIAL because while the speed flags (`--concurrent-fragments 4` and `--http-chunk-size 10M`) were implemented in code and tested in `test_downloader.py`, the standalone decision record `docs/verification/speed_decision.md` with alternating pairs and medians was missing.

## Allowed Files
- `docs/verification/speed_decision.md`
- `app/core/downloader.py` (verification only; flags are already in place)
- `docs/verification/requirements_matrix_2.md`
- `docs/verification/autonomy_log_2.md`

## Chunks
### Chunk 7.1: Write `docs/verification/speed_decision.md`
1. Detail the background: single-stream YouTube TCP rate-limiting causing download speed to collapse down to 0.99 MB/s despite 8.42 MB/s line capacity.
2. Collate measurement pairs:
   - Pair 1: Raw connection throughput (Cloudflare CDN 50 MB: 8.42 MB/s) vs YouTube unaccelerated stream (3.08 MB/s median).
   - Pair 2: Baseline vs Concurrent fragments (`-N 4`) on 689 MB video (`aqz-KE-bpKQ`).
   - Pair 3: Sequential downloads (14.97s) vs Parallel lanes (6.85s).
   - Reliability: `--http-chunk-size 10M` preventing HTTP 403 Forbidden disconnects.
3. Decision D6:
   - Formally adopt `--concurrent-fragments 4` and `--http-chunk-size 10M` in `build_video_cmd` and `build_audio_cmd`.
   - Confirm code alignment in `app/core/downloader.py`.

## Tests First
Run `pytest tests/test_downloader.py -k "concurrent_fragments"` to verify code flags match the decision.

## Done-When
- `docs/verification/speed_decision.md` exists with all required sections, measurements, alternating pairs, and medians.
- Tests pass.
- Matrix row C1 marked PASS.

## Rollback
`rm docs/verification/speed_decision.md`.
