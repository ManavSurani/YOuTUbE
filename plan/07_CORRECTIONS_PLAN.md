# Plan 07: Corrections and Close-Out Plan for YOuTUbE

**Branch:** `fix/ui-pass`  
**Repository:** `c:\Vs\YOuTUbE`  
**Baseline Commit:** `62c8db1`  
**Milestone:** Multi-Lane Parallel Queue & UI Hardening (Corrections & Final Verification)  
**Status:** DRAFT (Awaiting Owner Approval)

---

## 1. Overview of the 8 Problems (Section 2)

| Problem ID | Problem Summary | Root Cause & Impact | Target Resolution |
|---|---|---|---|
| **P1** | `test_exact_command_string_unicode` fails on owner's PC | Hypothesis (not yet verified): `Path.resolve()` in `build_select_command()` asks Windows about the disk (folder casing, junctions, redirected folders), so the command text can depend on the PC. To be confirmed or rejected by the diagnostic in Chunk 3 Step A. Impact: Show in folder for names with special characters may not select the file. | Diagnose with `scratch/diag_select.py`. Replace `Path.resolve()` with `os.path.abspath(str(path))` in `build_select_command()` so the command text is pure string normalization independent of local disk state. Add test verifying path text preservation. |
| **P2** | Full-suite test counts do not add up across reports | Cause unknown until Chunk 1. Known facts: the baseline is said to have 1 failing test; the Phase A, B and C evidence lists only passes; Phase D lists 1 failure; the Phase C run used `--ignore=tests/test_check_scope.py`. Chunk 1 produces the real numbers. | Run the FULL test suite (zero `--ignore`) at baseline `62c8db1` in a clean worktree and at `HEAD`. Document a comprehensive test-by-test comparison table in `docs/verification/test_comparison.md`. |
| **P3** | Unreported scope changes in `app/ui/header.py` and `.gitignore` | `header.py` was edited in commit `4db7f12` to fix `AnimatedStatusDot` `AttributeError` without a regression test or scope exception record. `.gitignore` was modified. | Add `tests/test_header_status_dot.py` with 2 regression tests. Create `docs/verification/scope_exceptions.md` marking both files as "pending owner approval". |
| **P4** | Latent duplicate download bug in `DownloadManager.set_online(True)` | `set_online(True)` unconditionally starts a worker on `self._active_job` even if the job was already running normally online, causing two concurrent `yt-dlp` processes on the same file. | Update `set_online()` to only resume if the lane was previously offline (`was_offline`). Never revive a shutting down lane (`_is_shutting_down`). If active job worker is already running, never start a second worker. Add 3 tests in `tests/test_download_lanes.py`. |
| **P5** | Assertions in `tests/test_close_event.py` rewritten without proof of strictness | `cancel_active` and `wait(2000)` assertions were updated when multi-lane `shutdown()` was implemented. | Create `docs/verification/close_event_assertions.md` documenting old vs new assertions. Add 4 strict new tests covering both-lane shutdown, shared 2.0s deadline decreasing wait, clean close with no active jobs, and rejection ignoring close. |
| **P6** | Document statements contain incorrect function names and claims | Reports mention non-existent `_is_job_running_this_kind()` (real name is `_job_running()`), claim "permanently clickable" (it is disabled when fetching/offline), and claim "Approved" before owner sign-off. | Search and replace incorrect names and claims across `docs/reports/*`, `gemini.md`, and `docs/verification/phase_*.md`. Mark approvals as "pending owner approval" or quote actual owner replies. |
| **P7** | Evidence and plan files missing from Git tracking | Commit `5e5a9c3` untracked `plan/`, `docs/reports/`, and `baseline_tests.md`, and `.gitignore` hid them. | Restore Git tracking for `plan/`, `docs/reports/`, and `docs/verification/` (including `baseline_tests.md`). Keep only `scratch/` ignored in `.gitignore`. |
| **P8** | `tests/test_check_scope.py` excluded from full-suite run | Cause not yet verified by a real failure output (see Chunk 6). Facts found in the code: `tools/check_scope.py` reads its baseline from `docs/verification/baseline.md`, which names `51a9d98` (older than this milestone's `62c8db1`); its `PROTECTED_FILES` set lists `app/core/download_manager.py` (approved scheduling exception, rule R2) but not `app/ui/theme.py` (protected, rule R1). | Diagnose failure, report details to owner, and propose minimal update to `tools/check_scope.py` (recognizing baseline `62c8db1` and the scheduling exception for `download_manager.py`) so full suite passes with zero `--ignore`. |

---

## 2. Detailed Chunk Execution Plan (Section 6)

### Chunk 1: Baseline and Real Test Numbers (Answers P2)
- **Goal:** Run the full test suite with no `--ignore` options on a clean worktree at baseline `62c8db1` and at current `HEAD`. Record exact counts and build a comparison table.
- **Allowed Files:** `docs/verification/*` only
- **Test to Write First:** N/A (Diagnostic and verification runs).
- **Exact Steps:**
  1. Create baseline worktree: `git worktree add ..\YOuTUbE_baseline 62c8db1`
  2. In baseline worktree, execute:
     `python -m pytest -q -rf -p no:cacheprovider 2>&1 | Tee-Object ..\YOuTUbE\docs\verification\baseline_tests.md`
  3. In `c:\Vs\YOuTUbE`, execute:
     `python -m pytest -q -rf -p no:cacheprovider 2>&1 | Tee-Object docs\verification\head_tests.md`
  4. Remove worktree: `git worktree remove ..\YOuTUbE_baseline`
  5. Create `docs/verification/test_comparison.md` containing a structured markdown table:
     `| Test Name | Baseline Result | HEAD Result | Verdict (pre-existing / new failure / fixed) |`
  6. Confirm every failing test has a verdict. If any NEW failure appears (passed at baseline, fails at HEAD), STOP and notify owner immediately.
  7. Record in the header of `docs/verification/test_comparison.md`: date, Python version, pytest version, Windows version, the exact command, and passed/failed/skipped/error counts for both runs. Run both with the same Python interpreter.
  8. `docs/verification/baseline_tests.md` is ignored until Chunk 8. Stage the evidence with `git add -f docs/verification/baseline_tests.md docs/verification/head_tests.md docs/verification/test_comparison.md`, then check with `git ls-files docs/verification | findstr tests`.
- **Done When:** Both test logs are captured on disk, `test_comparison.md` is populated with verdicts, and no unexplained new failures exist.
- **Commit Message:** `fixCORR.1: record real baseline and HEAD full-suite results`

---

### Chunk 2: header.py Regression Test and Scope Exceptions (Answers P3)
- **Goal:** Add unit tests preventing regression of the `AnimatedStatusDot` `_start_color` fix, prove failure on baseline code, and document the scope exceptions.
- **Allowed Files:** `tests/test_header_status_dot.py` (new), `docs/verification/scope_exceptions.md`
- **Diff Inspection:**
  `git diff 62c8db1 HEAD -- app/ui/header.py`
  (Confirms 4-line addition initializing `self._start_color = QColor("#2BA640")` and updating in `set_online`/`set_color` and `paintEvent`).
- **Test to Write First:** `tests/test_header_status_dot.py`:
  ```python
  from app.ui.header import AnimatedStatusDot

  def test_status_dot_paints_mid_animation_without_start_color_error(qtbot):
      dot = AnimatedStatusDot()
      qtbot.addWidget(dot)
      dot._progress = 0.5      # mid-animation: paintEvent now needs _start_color
      dot.grab()               # must not raise AttributeError

  def test_status_dot_survives_online_offline_switches(qtbot):
      dot = AnimatedStatusDot()
      qtbot.addWidget(dot)
      dot.set_online(False); dot.grab()
      dot.set_online(True);  dot.grab()
  ```
- **Failing Test Proof:**
  1. Temporarily backup and restore baseline `header.py`:
     `git show 62c8db1:app/ui/header.py > scratch\header_baseline.py`
     Copy baseline content to `app/ui/header.py`.
  2. Run on the temporarily restored baseline file. Expected: test 1 fails with an AttributeError about `_start_color`. Test 2 may fail or pass depending on animation timing: record the REAL result of both tests here. After restoring the fixed file both tests must pass. Note: a plain `dot.grab()` at the default progress 1.0 passes even on the old code, which is why test 1 sets `_progress = 0.5`.
  3. Restore fixed version: `git checkout -- app/ui/header.py`.
  4. Re-run `pytest tests/test_header_status_dot.py` -> Both tests pass.
  5. The restore of the baseline `header.py` is temporary and must never be committed. After `git checkout -- app/ui/header.py` run `git diff --stat -- app/ui/header.py` (must print nothing, because HEAD already contains the fix) and `git status --short` (must not list `app/ui/header.py` as modified). Paste both outputs in the evidence.
- **Scope Exceptions Document:**
  Create `docs/verification/scope_exceptions.md`:
  ```markdown
  | File | Commit | Reason | Test | Status |
  |---|---|---|---|---|
  | app/ui/header.py | 4db7f12 | Fixed AttributeError in AnimatedStatusDot paintEvent | test_status_dot_paints_before_any_colour_change | pending owner approval |
  | .gitignore | 5e5a9c3 | Updated ignore rules | n/a (reverted in Chunk 8) | pending owner approval |
  ```
- **Done When:** Both tests pass with the fix, fail on baseline, and `scope_exceptions.md` exists marked "pending owner approval".
- **Commit Message:** `fixCORR.2: add regression test for status dot and record scope exceptions`

---

### Chunk 3: Show in Folder Command with Special Characters (Answers P1)
- **Goal:** Ensure `build_select_command()` produces an exact, stable Windows Explorer `/select` string independent of local disk state or filesystem casing.
- **Allowed Files:** `app/core/file_actions.py` (`build_select_command` only), `tests/test_file_actions.py` (add tests only), `scratch/` (uncommitted)
- **Diagnostic Step (Step A):**
  Create `scratch/diag_select.py`:
  ```python
  import os
  from pathlib import Path
  from app.core.file_actions import build_select_command
  raw = r"C:\Downloads\｜ ： ⧸ é 日本語 😀.mkv"
  p = Path(raw)
  print("resolve :", ascii(str(p.resolve())))
  print("abspath :", ascii(os.path.abspath(raw)))
  print("built   :", ascii(build_select_command(p)))
  ```
  Execute `python scratch/diag_select.py` and `python -m pytest tests/test_file_actions.py::test_exact_command_string_unicode -vv`.
- **Decision (Step B):**
  Result of Step A on this PC: paste the REAL output of `python scratch/diag_select.py` and of the pytest -vv run here (NOT YET VERIFIED until pasted). Then choose exactly one. Case 1: resolve() changed the text and abspath() did not -> apply Step C. Case 2: the test's expected text differs for another reason (source file encoding, e-acute composed vs decomposed) -> fix only the test text and explain. Case 3: the code output is wrong for another reason -> STOP and ask the owner.
- **Smallest Fix (Step C):**
  In `app/core/file_actions.py`:
  ```python
  def build_select_command(path: Union[str, Path]) -> str:
      """Build the Explorer /select parameter string (pure text work, no disk access)."""
      norm_path = os.path.abspath(str(path))
      return f'/select,"{norm_path}"'
  ```
- **Test to Add (Step D):**
  In `tests/test_file_actions.py`:
  ```python
  def test_select_command_keeps_path_text_as_given():
      assert build_select_command(r"C:\DOWNLOADS\Clip.mkv") == r'/select,"C:\DOWNLOADS\Clip.mkv"'
  ```
  (Retain existing `test_exact_command_string_spaces` and `test_exact_command_string_unicode`).
- **Step D2:** run the whole file `python -m pytest tests/test_file_actions.py -vv` (all tests, not only the new one) and `git grep -n "build_select_command" -- app tests`; list every caller and confirm each still works. Confirm `import os` is present at the top of `app/core/file_actions.py` (do not add other imports).
- **Manual Verification Step (Step E for Owner):**
  Create test file `test ｜ ： ⧸ é.mkv` in Downloads folder. Click "Show in folder" from History and Recently downloaded. Expect Explorer to open with the file highlighted.
- **Done When:** `test_exact_command_string_unicode` and `test_select_command_keeps_path_text_as_given` pass.
- **Commit Message:** `fixCORR.3: make Show in folder command independent of the disk`

---

### Chunk 4: set_online Must Never Start a Second Worker (Answers P4)
- **Goal:** Harden `DownloadManager.set_online()` against starting duplicate worker processes on already-running jobs or waking up shutting-down lanes.
- **Allowed Files:** `app/core/download_manager.py` (`set_online`, one new helper `_resume_active_job`, and two attribute lines in `__init__`; plus the `QTimer` import if missing), `tests/test_download_lanes.py`
- **Tests to Write First:**
  In `tests/test_download_lanes.py`:
  1. `test_set_online_true_while_running_starts_no_second_worker`: Mock active job + worker online, call `set_online(True)` -> assert no second `_start_worker` is called.
  2. `test_offline_then_online_resumes_exactly_once`: Call `set_online(False)` twice (pause called once), call `set_online(True)` twice -> assert `_start_worker` called exactly once.
  3. `test_set_online_does_not_revive_a_shutting_down_lane`: Call `shutdown()`, then `set_online(True)` -> assert no worker started.
  4. `test_resume_waits_until_old_worker_stopped`: `set_online(False)` with a worker whose `isRunning()` returns True; patch `QTimer.singleShot` to store callbacks; `set_online(True)` -> assert `_start_worker` NOT called; make `isRunning()` return False; run the stored callback -> assert `_start_worker` called exactly once.
  5. `test_resume_gives_up_after_20_attempts_without_starting_second_worker`: `isRunning()` stays True; run the callbacks 21 times -> assert `_start_worker` never called and one warning logged.
  6. `test_second_online_call_does_not_start_another_worker`: after a successful resume, `set_online(True)` again -> still exactly one `_start_worker` call.
  Rules kept from the original task: (a) keep every other existing behaviour of `set_online`; (b) `enqueue()` keeps clearing `_is_shutting_down`; if any existing test relied on `set_online(True)` clearing that flag, STOP and ask the owner and do not weaken that test.
- **Expected Failure:** First test fails on current code because current `set_online(True)` unconditionally executes `self._start_worker(self._active_job)`.
- **Smallest Code Fix in `app/core/download_manager.py`:**
  ```python
  # in __init__ (two new attributes)
  self._paused_worker = None
  self._resume_attempts = 0

  def set_online(self, online: bool) -> None:
      was_offline = self._is_offline
      self._is_offline = not online

      if not online:
          if not was_offline and self._active_job and self._worker:   # only on online -> offline
              get_logger().info("Offline: pausing %s lane", self.kind)
              self._paused_worker = self._worker
              self._worker.pause()
          return

      if self._is_shutting_down:
          return                                   # never revive a closing lane

      if was_offline and self._paused_worker is not None:
          self._resume_attempts = 0
          self._resume_active_job()                # offline -> online: resume exactly once
      elif not self._active_job:
          self._process_next()                     # already online: only wake an idle lane

  def _resume_active_job(self) -> None:
      """Start a new worker for the paused job only after the old thread has really stopped."""
      old, job = self._paused_worker, self._active_job
      if old is None or job is None or self._is_offline or self._is_shutting_down:
          return
      if old.isRunning():
          self._resume_attempts += 1
          if self._resume_attempts <= 20:          # about 2 seconds, never blocks the UI
              QTimer.singleShot(100, self._resume_active_job)
          else:
              get_logger().warning("Old %s worker did not stop; resume skipped", self.kind)
              # OWNER QUESTION Q5: which existing failure path should end this job?
          return
      self._paused_worker = None
      self._start_worker(job)
  ```
- **Done When:** All 3 new tests pass and full test suite introduces zero regressions.
- **Commit Message:** `fixCORR.4: set_online never starts a second worker or revives a closing lane`

---

### Chunk 5: Close-Event Tests: Prove Nothing Got Weaker (Answers P5)
- **Goal:** Prove that the multi-lane shutdown assertions in `tests/test_close_event.py` are strictly stronger than or equivalent to baseline assertions, and add missing guarantee tests.
- **Allowed Files:** `tests/test_close_event.py`, `docs/verification/close_event_assertions.md` (no edits to `main_window.py` unless bug proven).
- **Assertion Comparison Table:** generate it from the REAL diff, `git diff -U3 62c8db1 HEAD -- tests/test_close_event.py`. One row for EVERY removed or changed assertion line (do not summarise). Columns: old assertion (exact text) | new assertion (exact text, or 'none') | why the multi-lane design needs this | at least as strict (yes/no). Any row with 'none' or 'no' gets a new test in this chunk. Paste the table here; NOT YET VERIFIED until pasted.
- **Tests to Add / Strengthen:**
  1. `test_close_shuts_down_both_lanes_before_waiting`: Asserts both `v_mgr.shutdown()` and `a_mgr.shutdown()` are invoked before any worker `.wait()` starts.
  2. `test_close_uses_one_shared_deadline`: Patches `app.ui.main_window.time.monotonic` with `itertools.count(0.0, 0.75)` (`lambda: next(ticks)`, so any number of calls works) and asserts that the timeout passed to the second worker's `wait()` is smaller than the first, and that every timeout is at most 2000 ms.
  3. `test_close_with_no_active_job_shows_no_dialog_and_shuts_down_both_lanes`: Verifies prompt is bypassed when idle, but both lanes cleanly shut down.
  4. `test_close_user_rejects_calls_shutdown_on_neither_lane`: Verifies "Keep downloading" ignores the event and calls shutdown on neither lane.
- **Done When:** Table exists with 100% "Yes" ratings and all close-event tests pass.
- **Commit Message:** `fixCORR.5: document and strengthen close-event assertions`

---

### Chunk 6: check_scope Test and Tools (Answers P8)
- **Goal:** Diagnose `tests/test_check_scope.py`, determine why it failed, and propose minimal adjustments so it runs cleanly in the full suite without `--ignore`.
- **Allowed Files:** Report only first; `tools/check_scope.py` and `tests/test_check_scope.py` only after explicit owner approval.
- **Diagnosis (Step A, read-only):** run `python -m pytest tests/test_check_scope.py -vv` on this PC and paste the REAL failure output here (NOT YET VERIFIED until pasted). Tell the owner why the file was excluded from the Phase C run.
- **Facts already found in the code:** `get_baseline_commit()` reads `docs/verification/baseline.md`, which names `51a9d98`. `PROTECTED_FILES` contains `app/core/download_manager.py` but not `app/ui/theme.py`.
- **Proposed minimal edit (pending owner approval; do not edit before the owner says yes):**
  (1) add an optional `--baseline <hash>` argument to `tools/check_scope.py` (default stays as today) so this milestone runs with `--baseline 62c8db1`; do NOT rewrite `docs/verification/baseline.md`, it is the history of the earlier milestone;
  (2) make `PROTECTED_FILES` match the rules: add `app/ui/theme.py`, and treat `app/core/download_manager.py` as the approved scheduling exception (not an error);
  (3) adjust only the assertions in `tests/test_check_scope.py` that depend on those two facts, never remove one;
  (4) re-run `python -m pytest tests/test_check_scope.py -vv` and the full suite with no `--ignore`.
- **Done When:** Full test suite can be run cleanly with `pytest` without any `--ignore` flag.
- **Commit Message:** `fixCORR.6: make scope checker test pass in the full suite`

---

### Chunk 7: Correct the Documents (Answers P6)
- **Goal:** Correct all inaccurate function names, overbroad button availability claims, and false approval claims across reports and logs.
- **Allowed Files:** `docs/reports/*`, `gemini.md`, `docs/verification/phase_*.md`
- **Exact Substitutions:**
  1. Replace all occurrences of `_is_job_running_this_kind` with `_job_running()`.
  2. Replace "permanently clickable" with "clickable while a job of this tab's kind runs; disabled while fetching or offline".
  3. Replace any claim of "Committed and Approved" or "Approved" by agent with:
     `Gate result: PASS. Owner approval: pending owner approval / given on <date, quote of reply>`.
  4. Update claimed test suite counts with real numbers obtained in Chunk 1.
  5. Add an owner check status line to each phase evidence file: owner checks performed or "pending owner verification".
  6. In Plan 1's report replace 'Scope Compliance: 100% Pass' (and any similar '100% scope compliance') with 'Scope compliance: pass with 2 recorded exceptions (app/ui/header.py, .gitignore), pending owner approval; see docs/verification/scope_exceptions.md'.
  7. In Plan 1's report replace the claim that SHA-256 signatures and line counts of the protected files were identical with 'git diff against 62c8db1 showed zero changes in the 15 protected files' (no SHA-256 was ever computed).
  8. Run `git grep -n -i -E "100%|sha-256|permanently|approved"` over `docs/reports gemini.md docs/verification` and review every hit; fix wrong ones, keep correct ones, list the decisions in the evidence.
- **Done When:** `git grep` for old terms returns zero hits in documentation.
- **Commit Message:** `fixCORR.7: correct report statements and gate results`

---

### Chunk 8: Put the Evidence into Git and Fix .gitignore (Answers P7)
- **Goal:** Restore Git tracking for all planning and verification documentation so proof is publicly verifiable on GitHub, while keeping development scratch files ignored.
- **Allowed Files:** `.gitignore`, Git tracking for `plan/`, `docs/reports/`, `docs/verification/` (including `baseline_tests.md`)
- **Exact Steps:**
  1. Remove `plan/`, `docs/reports/`, and `baseline_tests.md` ignore rules from `.gitignore`. Keep `scratch/` ignored.
  2. Track directories in git:
     `git add .gitignore plan docs/reports docs/verification`
  3. Verify `git status` stages only documentation and `.gitignore`.
  4. Prove it: `git check-ignore -v plan docs/reports docs/verification/baseline_tests.md` must print nothing, and `git ls-files plan docs/reports docs/verification/baseline_tests.md docs/verification/head_tests.md docs/verification/test_comparison.md` must list the files. Also run `git status --short` and list every unexpected file for the owner before committing.
- **Done When:** All plan and verification files are staged and committed cleanly without any unwanted binary or temporary files.
- **Commit Message:** `fixCORR.8: track plan and verification evidence, restore .gitignore`

---

### Chunk 9: Final Gate (No Code)
- **Goal:** Complete comprehensive automated and manual verification gate.
- **Steps:**
  1. Run full test suite with no `--ignore`:
     `python -m pytest -q -rf -p no:cacheprovider`
     Must show zero failures other than pre-existing ones recorded in `test_comparison.md`.
  2. Scope proof:
     `git diff --name-only 62c8db1 HEAD`
     Verify zero edits to the 15 protected files:
     `git diff --stat 62c8db1 HEAD -- app/core/downloader.py app/core/proc.py app/core/info_fetcher.py app/core/jobs.py app/core/url_tools.py app/core/history_db.py app/core/history_service.py app/core/thumbnails.py app/core/errors.py app/core/network_monitor.py app/core/app_updater.py app/core/tool_manager.py app/tools.json installer/setup.iss app/ui/theme.py` (Must print nothing).
     Allowed changed files: app/core/download_manager.py, app/ui/video_tab.py, app/ui/audio_tab.py, app/ui/recent_list.py, app/ui/queue_widget.py, app/ui/main_window.py, app/ui/header.py (exception), app/core/file_actions.py (only if Chunk 3 changed it), tools/check_scope.py and tests/test_check_scope.py (only if Chunk 6 changed them), tests/, docs/, plan/, gemini.md, .gitignore. Anything else is a scope violation: stop and report. Also run `python tools/check_scope.py --final --baseline 62c8db1` if Chunk 6 added that option.
  3. Run leftover checks:
     `git grep -n "print(" -- app` (empty)
     `git grep -n "shell=True" -- app` (empty)
  4. Present the Owner Checks (each is 'do this -> expect this'):
   a) Start a video download and an audio download together -> both show live progress at the same time.
   b) Add the same link as video and as audio -> the second shows 'Waiting for the same video to finish' and starts when the first ends.
   c) During a running download switch Wi-Fi off, wait 10 seconds, switch it on -> it resumes, and Task Manager shows exactly ONE yt-dlp.exe per active download (never two for the same video).
   d) Close the app during a download -> one confirmation, then no yt-dlp.exe or ffmpeg.exe stays running.
   e) Create a file named `test ｜ ： ⧸ é.mkv` in Downloads; press Show in folder and Play in History and in Recently downloaded -> Explorer opens with the file selected and the file plays.
   f) Click Add to queue with an empty link box during a download -> a 4-second hint appears, the download keeps running, Cancel stays visible.
   g) History -> Clear all, then open Video and Audio -> Recently downloaded is gone on both, no restart.
  5. Wait for owner's explicit reply: `"approved final"`.

---

### Chunk 10: Save to GitHub (Only After "approved final")
- **Goal:** Push verified branch to GitHub and perform fast-forward merge into `main` upon explicit owner instruction.
- **Steps:**
  1. Verify clean tree: `git status`
  2. Inspect commit log: `git log --oneline 62c8db1..HEAD`
  3. Verify no secrets: `git grep -n -i -E "(api[_-]?key|secret|token|password)" -- . ":!tests" ":!gemini.md"`
     Before step 4 run `git fetch origin` and `git status -sb`; the branch must not be behind origin/fix/ui-pass. If the push is rejected as non-fast-forward, STOP and ask; never use --force. If `git pull --ff-only origin main` fails, or `git merge --ff-only fix/ui-pass` refuses, STOP and ask; do not create a merge commit or resolve conflicts alone. Do not delete any branch.
  4. Push branch: `git push origin fix/ui-pass` (normal push, no `--force`).
  5. Fetch and verify: `git fetch origin` && `git rev-parse HEAD origin/fix/ui-pass` (same hash twice).
  6. Present hash to owner and ask: *"Merge into main? (approved merge)"*.
  7. Upon reply `"approved merge"`:
     - Verify ancestor: `git merge-base --is-ancestor origin/main HEAD`
     - Checkout main: `git checkout main`
     - Pull: `git pull --ff-only origin main`
     - Merge: `git merge --ff-only fix/ui-pass`
     - Test run on main: `python -m pytest -q -rf -p no:cacheprovider`
     - Push main: `git push origin main`
     - Verify: `git rev-parse HEAD origin/main`
     - Return to branch: `git checkout fix/ui-pass`

---

## 3. Questions with Recommended Answers

### Question 1: Chunk 3
After Step A, if resolve() is shown to change the text and abspath() does not, may we replace `Path(path).resolve()` with `os.path.abspath(str(path))` in `build_select_command()` only? Recommended: yes, only if the pasted diagnostic output shows it.

### Question 2: Chunk 4
Code facts (verified): `DownloadWorker.pause()` sets `_is_paused` and kills the process tree; the worker then emits `paused` and its thread ends; `DownloadManager` has no handler for `paused`. We therefore resume with a non-blocking retry (about 2 seconds, then give up with a warning) instead of `wait(2000)` on the UI thread. Do you agree? Recommended: yes.

### Question 3: Chunk 6
May we add `--baseline` to `tools/check_scope.py`, align `PROTECTED_FILES` with the rules (add `theme.py`, treat `download_manager.py` as the approved exception), and adjust the dependent assertions in `tests/test_check_scope.py`? Recommended: yes, after the failure output is pasted.

### Question 5: Chunk 4
If the old worker has not stopped after 20 retries, which existing failure path should end the active job so the lane does not wait forever? Recommended: the path used when a worker emits `failed`; the agent names the method and the owner confirms.

### Question 4: Chunk 8 — Restoring Tracked Documentation
- **Question:** Should `plan/`, `docs/reports/`, and `docs/verification/` (including `baseline_tests.md`) be restored to Git tracking, with `scratch/` remaining the sole untracked/ignored directory?
- **Recommended Answer:** Yes. Restoring `plan/`, `docs/reports/`, and `docs/verification/` ensures all verification evidence and architecture plans are permanently recorded on GitHub, while `.gitignore` continues to exclude local scratch files.

## 4. Rules (R1 to R11)

R1  Protected files, ZERO edits, ever (you may read and call them):

      app/core/downloader.py, app/core/proc.py, app/core/info_fetcher.py, app/core/jobs.py,

      app/core/url_tools.py, app/core/history_db.py, app/core/history_service.py,

      app/core/thumbnails.py, app/core/errors.py, app/core/network_monitor.py,

      app/core/app_updater.py, app/core/tool_manager.py, app/tools.json, installer/setup.iss,

      app/ui/theme.py

R2  Approved exception: app/core/download_manager.py, for SCHEDULING ONLY (lanes, queues, persistence,

    deferral, offline handling, shutdown). Never download execution or command builders.

R3  Do not change colours, fonts, layout, sizes or any look of the app. No theme edits. No new colours.

R4  Open and edit ONLY the files that the current chunk allows (table in Section 6). If a fix seems to

    need another file: STOP and ask me.

R5  Failing test first: write the test, run it, see it fail for the right reason, make the smallest fix,

    see it pass. Never delete or weaken an existing test. Changed assertions need a table (Chunk 5).

R6  Smallest possible change. No refactors, no renames, no new classes, no drive-by edits, no extra

    comments or formatting changes in lines you did not need to touch.

R7  No terminal windows: no shell=True, os.system, print() in app code. (A scratch diagnostic script in

    scratch/ may use print; scratch/ is never committed.)

R8  One commit per chunk, message: fixCORR.<chunk>: <what changed>. No squashing. Never force-push.

R9  Never claim that I approved something. Write "pending owner approval" until I say so in this chat.

R10 Keep chat messages short. Put details, command output and tables in docs/verification/.

R11 Do not bump the version. Do not create tags.

## 5. Decisions already made (D1 to D6)

D1  header.py: keep your change. Needs a regression test and an exception record.

D2  Plan and evidence files are tracked in git from now on: plan/, docs/reports/, docs/verification/

    (including baseline_tests.md). scratch/ stays ignored.

D3  Do not delete 00_AGENT_BRIEF.md, 02_DESIGN_SYSTEM.md or gemini.md. Do not touch the android folder.

D4  If a test fails at baseline AND at HEAD in the same way, it is "pre-existing". Do not fix it unless it

    is P1. List it in the evidence.

D5  Save to GitHub: push branch fix/ui-pass first. Merge into main only after I reply "approved merge".

    origin/main (51a9d98) is an ancestor of fix/ui-pass, so the merge is fast-forward only (--ff-only).

D6  You run on my PC. Run the tests yourself. I do the manual UI checks.

## 6. Allowed files per chunk

Chunk 4 also allows two attribute lines in `__init__` and the helper `_resume_active_job` (edit E6).

Allowed files per chunk

  1  docs/verification/* only

  2  tests/test_header_status_dot.py (new), docs/verification/scope_exceptions.md

  3  app/core/file_actions.py (build_select_command only), tests/test_file_actions.py (add tests only),

     scratch/ (not committed)

  4  app/core/download_manager.py (set_online only), tests/test_download_lanes.py

  5  tests/test_close_event.py; app/ui/main_window.py ONLY if a test proves a real bug, then STOP and ask

  6  tools/check_scope.py and tests/test_check_scope.py ONLY after asking me; otherwise report only

  7  docs/reports/*, gemini.md, docs/verification/phase_*.md

  8  .gitignore, git add of plan/, docs/reports/, docs/verification/

  9  no files (checks only)

  10 git commands only

## 7. Stop-and-ask triggers

- A fix needs a protected file, or a file that the chunk does not allow.

- A new failure appears at HEAD that did not exist at baseline.

- A test fails in an unexplained way after two fix attempts.

- A step in this prompt does not match the real local code.

- Chunk 3 Case 3, Chunk 4 worker-pause question, Chunk 5 main_window bug, Chunk 6 tool edit,

  an unknown file in git status, a non-fast-forward merge.

## 8. Report formats

After each chunk:  "Chunk N: <name> | files changed | test added | result | commit hash".

At the gate:  one message with: full-suite counts, the pre-existing failures list, the scope proof

output, and the owner-check list.

## 9. Definition of 'the application is correct'

- The full suite has no failure except explicitly listed pre-existing ones, and no test was excluded.

- test_exact_command_string_unicode passes, and my manual Show in folder check works.

- set_online can never start a second worker; close-event guarantees are all tested.

- The 15 protected files show zero changes; every other changed file is explained in

  docs/verification/scope_exceptions.md or belongs to an approved phase.

- Reports contain no wrong statements and no approvals that I did not give.

- My owner checks a to g pass.

- The branch is pushed and (after "approved merge") main equals fix/ui-pass on GitHub.
