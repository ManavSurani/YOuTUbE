# Test Replacement & Change Log

This log records every test that was replaced or updated during the autonomous fix loop, as required by Rule R2.

| Old Test | New Test | Phase | Why |
|---|---|---|---|
| `TestSafeCancel::test_cancel_only_removes_job_files_in_tmp` (bare `TMP_DIR`) | `TestSafeCancel::test_cancel_only_removes_job_files_in_tmp` (placed in `job_tmp_dir(job_id)`) | Phase 1 (Chunk 1.1) | Prompt Section 5 Phase 1 Chunk 1.1 requirement: per-job temp folder isolation replaces bare TMP_DIR file placement |
| `test_scope_checker_clean` (subprocess unmocked working tree diff) | `test_scope_checker_clean` (monkeypatched clean changed files list) | Phase 1 (Chunk 1.1) | Unmocked working tree diff failed when approved Section 1.1 backend files (paths.py) were modified; unit test now tests check_scope logic cleanly without coupling to working tree modifications |
