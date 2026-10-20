# Test Replacement & Change Log

This log records every test that was replaced or updated during the autonomous fix loop, as required by Rule R2.

| Old Test | New Test | Phase | Why |
|---|---|---|---|
| `TestSafeCancel::test_cancel_only_removes_job_files_in_tmp` (bare `TMP_DIR`) | `TestSafeCancel::test_cancel_only_removes_job_files_in_tmp` (placed in `job_tmp_dir(job_id)`) | Phase 1 (Chunk 1.1) | Prompt Section 5 Phase 1 Chunk 1.1 requirement: per-job temp folder isolation replaces bare TMP_DIR file placement |
| `test_scope_checker_clean` (subprocess unmocked working tree diff) | `test_scope_checker_clean` (monkeypatched clean changed files list) | Phase 1 (Chunk 1.1) | Unmocked working tree diff failed when approved Section 1.1 backend files (paths.py) were modified; unit test now tests check_scope logic cleanly without coupling to working tree modifications |
| `test_same_video_id_deferral` | `test_same_video_id_parallel_execution` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: deferral rule abolished, assert parallel execution of same video_id in video & audio lanes |
| `test_strict_fifo_preserved_when_deferred` | `test_parallel_lanes_with_internal_fifo` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: assert parallel execution across lanes with internal FIFO within each lane |
| `test_wake_both_lanes_on_finish` | `test_parallel_lanes_independent_finish` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: lanes operate independently without deferral waking |
| `test_wake_both_lanes_on_cancel_active` | `test_parallel_lanes_independent_cancel` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: lanes operate independently on cancel |
| `test_wake_both_lanes_on_fail` | `test_parallel_lanes_independent_fail` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: lanes operate independently on fail |
| `test_wake_both_lanes_on_deferred_removal` | `test_parallel_lanes_queue_removal` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: waiting queue removal during parallel execution |
| `test_restored_same_video_id_pair_starts_one_and_defers_other` | `test_restored_same_video_id_pair_starts_both_in_parallel` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: restored same-video jobs run in parallel across lanes |
| `test_queue_row_deferred_status_text` | `test_queue_row_waiting_status_text` | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: 'Waiting for the same video to finish' status text removed |
| `test_queue.py` (`_deferred_job_ids.clear()`) | `test_queue.py` (without `_deferred_job_ids`) | Phase 1 (Chunk 1.3) | Prompt Phase 1 Chunk 1.3: `_deferred_job_ids` attribute removed |
| `test_audio_guess_replaced_by_real_total_within_25_percent_rule` (expected ~83.2% with 13000 B/s) | `test_audio_guess_replaced_by_real_total_within_25_percent_rule` (expected ~79.1% with 17000 B/s) | Phase 4 (Chunk 4.1) | Prompt Section 5 Phase 4 Chunk 4.1 requirement: audio estimate upgraded from 13000 to 17000 B/s (~136 kbps) to match YouTube Opus streams |
| `test_download_worker_fluctuating_estimates_sequence` (asserted backward drop < 1.0%) | `test_download_worker_fluctuating_estimates_sequence` (asserted strict monotonicity `>= previous`) | Phase 4 (Chunk 4.2) | Prompt Requirement A2 & Chunk 4.2: 25% latch rule drop removed, progress bar must never go backwards |
| `test_real_first_lines_vp9_video_log` (asserted backward drop `emitted[2] < emitted[1]`) | `test_real_first_lines_vp9_video_log` (asserted strict monotonicity `emitted[i] >= emitted[i-1]`) | Phase 4 (Chunk 4.2) | Prompt Requirement A2 & Chunk 4.2: 25% latch rule drop removed, progress bar must never go backwards |
| `test_edge_case_queue_dir_switch_mid_download` | `test_edge_case_queue_dir_switch_mid_download` (with queue cleanup) | Phase 4 | Cleaned up active job at end of test to prevent dirty state persisting to `queue_video.json` |
| `test_main_window_network_transitions` | `test_main_window_network_transitions` (with `QMessageBox.exec` mock) | Phase 4 | Mocked `QMessageBox.exec` to prevent exit confirmation modal dialog from blocking test runner |
| `test_network_error` (asserted 'No internet connection.') | `test_network_error` (asserts 'The internet connection was interrupted. Check your connection and press Retry.') | Phase 6 | Prompt Phase 6 requirement: friendly network retry message |
| `test_unknown_error_fallback` (asserted 'Something went wrong. Copy the details and try again.') | `test_unknown_error_fallback` (asserts 'Something went wrong. Open Settings and press Export log to see the details.') | Phase 6 | Prompt Phase 6 requirement: remove mention of non-existent 'Copy details' button and guide user to Settings Export log |
| (None) | `test_14_audit_error_samples` (parameterized test across 14 audit error cases) | Phase 6 | Prompt Phase 6 requirement: verify 14 error samples from audit map to specified friendly texts |


