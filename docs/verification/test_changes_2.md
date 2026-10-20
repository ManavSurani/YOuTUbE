# Test Replacement & Change Log 2

This log records every test replacement or contract update during this completion loop, as required by Rule R2.

| Old Test | New Test | Phase | Why |
|---|---|:---:|---|
| 	est_active_job_restart_limit_moves_to_failed (asserted limit 3 and generic reason) | 	est_active_job_restart_limit_moves_to_failed (asserts limit 2 and exact D1 message) & 	est_active_job_restart_limit_boundaries | Phase 1 | Decision D1 & requirement S2a: restart limit is 2; 3rd restore fails with exact D1 message |
