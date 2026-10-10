# YOuTUbE: Rules, Scope, and Architecture Reference

This document defines the engineering standards, architecture rules, file boundaries, and execution protocol for the YOuTUbE Multi-Lane Queue & UI project.

---

## 1. Golden Rules Table

| # | Rule | Requirement |
|---|---|---|
| **1** | **One Chunk at a Time** | Work through all chunks of a phase in order. Commit after each chunk. Open and edit only the files allowed for that specific chunk. |
| **2** | **Failing Test First** | Write the failing test first, run it, see it fail for the right reason, make the smallest code change, and see it pass. Never delete or weaken any existing test. |
| **3** | **Minimal Changes** | Make the smallest possible change that fixes the row. No premature refactors, no unnecessary classes, no new states, no extra code. |
| **4** | **Design System Fidelity** | Keep existing Segoe UI typography, theme color tokens, and kit widgets (`InlineMessage`, `AnimatedButton`, `IconButton`, `ModernProgressBar`). Zero new colors, zero gradients, zero shadows. |
| **5** | **Zero Terminal Flashes** | Never use `shell=True`, `os.system()`, or `print()` in application code. All processes must use `start_hidden` via `app/core/proc.py`. |
| **6** | **Protected File Boundaries** | Never modify the 15 strictly protected files. Edits to `app/core/download_manager.py` are approved strictly for scheduling. |
| **7** | **Working Style** | Work through ALL chunks of a phase in order without waiting for the owner. Commit after each chunk. Stop and ask the owner ONLY on designated trigger events or at the phase gate. |
| **8** | **Phase Gate Approval** | At the phase gate, send ONE summary message with automated results and real-PC checks. Never start the next phase until the owner replies "approved". |

---

## 2. The 15 Strictly Protected Files (Zero Edits Permitted)

The following 15 files represent proven, core engine logic and frozen assets. They must show **0 lines changed** throughout all phases:

```
1.  app/core/downloader.py
2.  app/core/proc.py
3.  app/core/info_fetcher.py
4.  app/core/jobs.py
5.  app/core/url_tools.py
6.  app/core/history_db.py
7.  app/core/history_service.py
8.  app/core/thumbnails.py
9.  app/core/errors.py
10. app/core/network_monitor.py
11. app/core/app_updater.py
12. app/core/tool_manager.py
13. app/tools.json
14. installer/setup.iss
15. app/ui/theme.py
```

### Approved Scheduling Exception
- **`app/core/download_manager.py`:** Approved for edits in Phase C strictly for multi-lane scheduling, lane queue files, persistence migration, cross-lane deferral, thread-safe wake-up, and offline pause/resume. Zero edits permitted to download execution logic or command builders.

---

## 3. Allowed Files Per Phase

| Phase | Description | Allowed Code Files | Allowed Test Files |
|---|---|---|---|
| **Phase A** | Add to queue while downloading | `app/ui/video_tab.py`<br>`app/ui/audio_tab.py` | `tests/test_tab_state_machine.py`<br>`tests/test_tab_flow.py`<br>`tests/test_tab_looks.py` |
| **Phase B** | Recently downloaded refresh | `app/ui/recent_list.py` | `tests/test_recent_list.py`<br>`tests/test_recent_sync.py` |
| **Phase C** | Two download lanes (scheduling) | `app/core/download_manager.py`<br>`app/ui/main_window.py`<br>`app/ui/video_tab.py`<br>`app/ui/audio_tab.py`<br>`app/ui/queue_widget.py` | `tests/test_download_lanes.py`<br>`tests/test_close_event.py`<br>`tests/test_download_manager.py`<br>`tests/test_queue.py`<br>`tests/test_phase8_stress_edge_cases.py`<br>`tests/test_tab_flow.py`<br>`tests/test_tab_state_machine.py`<br>`tests/test_tab_looks.py`<br>`tests/test_recent_list.py`<br>`tests/test_app_updater.py`<br>`tests/test_tool_manager.py` |
| **Phase D** | Per-item queue cards & isolation | `app/ui/queue_widget.py`<br>`app/ui/video_tab.py`<br>`app/ui/audio_tab.py` | `tests/test_per_item_cards.py`<br>`tests/test_queue.py`<br>`tests/test_tab_flow.py` |

---

## 4. Phase Order & Rationale

**Execution Sequence: Phase A ➔ Phase B ➔ Phase C ➔ Phase D**

1. **Phase A (Tab Buttons & Sticky State):** Immediately fixes the button bugs (unclickable Add to queue, disappearing Cancel, reset to IDLE on text clear) on the current tabs without waiting for backend architectural shifts.
2. **Phase B (History Tab Synchronization):** Resolves the stale "Recently downloaded" bug so the single-tab experience is completely synchronized and bug-free.
3. **Phase C (Dual-Lane Scheduling Engine):** Implements the backend parallel download lanes, persistent queue files, cross-lane deferral, thread-safe multi-path wake-ups, and shutdown methods with 100% automated test coverage.
4. **Phase D (Queue UI & Strict Tab Isolation):** Adds individual progress bars to `QueueRow` and enforces strict visual tab isolation on top of the proven dual-lane engine.

---

## 5. Standard Chunk Workflow

For every chunk in every phase, follow this exact 5-step cycle:

```
[1. Read Local Code] ➔ [2. Write Failing Test] ➔ [3. Make Smallest Fix] ➔ [4. Verify Tests Pass] ➔ [5. Commit Chunk]
```

1. **Read Local Code:** Read the current local code of the allowed file. Confirm findings and existing structures.
2. **Write Failing Test:** In the specified test file, write the new test asserting the target behavior. Run `pytest <test_file>` and verify that it fails for the exact expected reason.
3. **Make Smallest Fix:** Make the minimal required modification in the allowed file.
4. **Verify Tests Pass:** Run `pytest <test_file>` and confirm the new test passes, along with all existing tests in that file.
5. **Commit:** Commit the chunk immediately with message: `fix<Phase>.<Chunk>: description`.

---

## 6. When to Stop and Ask the Owner

Work continuously through all chunks of a phase without pausing for chat messages. Stop and ask the owner **ONLY** under these 5 conditions:

1. **Protected File Violation:** A fix appears to require editing one of the 15 protected files.
2. **Unexplained Test Failure:** A test fails in an unexplained way after two fix attempts.
3. **Code Discrepancy:** The local code structure differs fundamentally from the plan findings.
4. **SQLite Concurrency Lock:** The two-thread history concurrency test reports a SQLite database lock error (do NOT attempt to edit `history_db.py` or `history_service.py`).
5. **Phase Gate:** When all chunks of the phase are complete, reach the Verification Gate, send the single gate report, and wait for the owner's "approved".

---

## 7. Real-PC Verification Protocol

At each phase gate, the agent provides a numbered checklist for manual verification on the owner's Windows PC. Every check is formulated in the exact format:
- `Do this` ➔ `Expect this`

Example:
- `Start a video download, leave URL input empty, click 'Add to queue'` ➔ `Expect a 4-second hint 'Paste a YouTube link first, then press Add to queue.' and download continues uninterrupted.`

---

## 8. Final Scope Proof Command

To prove zero scope violations across all phases:

```bash
git diff --name-only <baseline>
```

The output must list ONLY:
- `app/core/download_manager.py` (scheduling edits only)
- `app/ui/video_tab.py`
- `app/ui/audio_tab.py`
- `app/ui/recent_list.py`
- `app/ui/queue_widget.py`
- `app/ui/main_window.py` (close event & offline handlers)
- Files under `tests/`
- Documentation files (`gemini.md`, `docs/`, `plan/`)

If `tools/check_scope.py` exists, also run:
```bash
python tools/check_scope.py --final
```
If `tools/check_scope.py` does not exist locally, rely on `git diff --name-only <baseline>`. Any protected file appearing in the diff means the work has failed and must be reverted.

---

## 9. Baseline Test Run (Before Phase A)

Before Phase A starts, the agent must run the FULL test suite at baseline `62c8db1`:
1. Run `pytest` across the entire test suite.
2. Record the raw terminal output, the total test count, and the complete list of any failing tests into `docs/verification/baseline_tests.md`.
3. If any test already fails at baseline:
   - Record each one as a **"known pre-existing failure"** along with its failure reason.
   - Report this list to the owner **BEFORE** starting Phase A.
   - Do NOT attempt to fix pre-existing failures unless explicitly instructed by the owner.
4. **Standard Phase Gate Suite Criterion:** In every phase gate (Phase A, B, C, D), the test criterion is:
   > *"Full suite passes, with no failures other than the known pre-existing ones, and the test count is higher than baseline."*

