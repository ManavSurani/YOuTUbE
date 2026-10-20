# Phase 9 Plan: Final Review, Full Verification & Report

## Goals
Verify all changes against the prompt specifications, ensure full test suite passes, verify all global constraints (G1, G2, G3, G4, G5), update the requirements matrix, and generate the comprehensive final audit report.

---

## Chunk 9.1: Comprehensive Test Suite Verification (G1)
- Run the complete pytest test suite without `--ignore`.
- Record test count, passed count, execution time.
- Verify zero regressions across all core, UI, downloader, queue, network, updater, errors, and supply chain test suites.

---

## Chunk 9.2: Global Constraints Verification (G2, G3, G4, G5)
- **G2 (Scope Protection)**:
  - Run `git diff --name-only cdfed4e..HEAD` and verify against Section 1.2 strictly forbidden files:
    - `app/core/proc.py`
    - `app/core/info_fetcher.py`
    - `app/core/jobs.py`
    - `app/core/url_tools.py`
    - `app/core/history_db.py`
    - `app/core/history_service.py`
    - `app/core/network_monitor.py`
    - `app/core/app_updater.py`
    - `app/tools.json`
    - `app/ui/theme.py`
    - `app/ui/header.py`
    - `app/ui/settings_dialog.py`
    - `app/ui/kit/buttons.py`
    - `app/ui/kit/checkbox.py`
    - `android/`
    - `app/version.py`
- **G3 (No Console Leaks / Shell Injections)**:
  - Run `grep -rn "print(" app/` -> must be 0 hits.
  - Run `grep -rn "shell=True" app/` -> must be 0 hits.
- **G4 (Zero Visual/Theme Regressions)**:
  - Check diff on `theme.py` (0 diffs), `buttons.py` (0 diffs), `header.py` (0 diffs).
  - Verify all UI changes adhered strictly to the design system (no extra colors, no layout distortion).
- **G5 (Robustness & Integrity)**:
  - Verify hidden process execution and modal dialog isolation in test harnesses.

---

## Chunk 9.3: Final Requirements Matrix & Autonomy Log Update
- Update rows G1, G2, G3, G4 in `docs/verification/requirements_matrix.md` with PASS status, evidence, and commit hashes.
- Update `docs/verification/autonomy_log.md` with Phase 9 summary.

---

## Chunk 9.4: Final Report Compilation (`docs/verification/final_report.md`)
- Compile full final report detailing:
  - Overview of resolved problems:
    - Problem A: Accurate progress numbers, whole-job total, combined formats.
    - Problem B: Parallel download of same video as video and audio concurrently.
    - Problem C: Download speed slowness resolution.
    - Problem D: Audit robustness, active job recovery, atomic queue, watchdog, plain error messages, plain-text labels, tool supply chain.
  - Requirements verification matrix (21 requirements).
  - Test suite results and performance summary.
  - Complete list of commits across the autonomous loop.
  - Instructions for the project owner.
