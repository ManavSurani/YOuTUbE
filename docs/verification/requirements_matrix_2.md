# Requirements Matrix 2: Autonomous Completion Loop

| ID | Requirement Description | Target Phase | Status | Evidence | Fixed in Commit |
|---|---|:---:|:---:|---|---|
| **S2a** | Active-job restart limit is 2 (third restore fails with "The app closed several times while this download was running. Press Retry.") | Phase 1 | NOT STARTED | Pending Phase 1 | Pending |
| **S2b** | Closing dialog says "A download is running. Quit now? It will continue the next time you open the app." | Phase 2 | NOT STARTED | Pending Phase 2 | Pending |
| **S1** | Corrupt/empty modern queue file renamed to `<name>.corrupt` (with timestamp if exists), starts with empty queue | Phase 3 | NOT STARTED | Pending Phase 3 | Pending |
| **S3** | Resume polls 100ms; force stops at ~3s (attempt 30); fails at ~10s (attempt 100); no double worker | Phase 4 | NOT STARTED | Pending Phase 4 | Pending |
| **S4** | Watchdog default 90s, never during merging/converting, at most 3 restarts per job | Phase 5 | NOT STARTED | Pending Phase 5 | Pending |
| **A1** | Automated replay test in `tests/`: total within 5% at 5/50/95%, strictly monotonic, no audio freeze | Phase 6 | NOT STARTED | Pending Phase 6 | Pending |
| **C1** | `speed_decision.md` with alternating pairs and medians; command builder flags match decision | Phase 7 | NOT STARTED | Pending Phase 7 | Pending |
| **M6** | Failed queue row "Copy details" button or documented OPEN | Phase 8 | NOT STARTED | Pending Phase 8 | Pending |
| **M3** | Path & URL scrubbing in logs or documented OPEN | Phase 8 | NOT STARTED | Pending Phase 8 | Pending |
| **M4** | Two video qualities of same video filename audit | Phase 8 | NOT STARTED | Pending Phase 8 | Pending |
| **M11**| Identified data-loss, duplicate-worker, temp-leak, or wrong-number defects handled | Phase 8 | NOT STARTED | Pending Phase 8 | Pending |
| **T2** | Installer compile (stays UNTESTED unless ISCC.exe exists) | Phase 9 | NOT STARTED | Pending Phase 9 | Pending |
| **G1** | Full test suite passes without `--ignore` (only known baseline failure allowed) | Global | NOT STARTED | Pending Phase 9 | Pending |
| **G2** | Section 2.2 forbidden files completely untouched | Global | NOT STARTED | Pending Phase 9 | Pending |
| **G3** | Zero `print(` and zero `shell=True` in `app/` | Global | NOT STARTED | Pending Phase 9 | Pending |
| **G4** | Zero colour, theme, or layout changes (except Phase 2 dialog text) | Global | NOT STARTED | Pending Phase 9 | Pending |
