#!/usr/bin/env python3
"""Scope checker tool enforcing protected files and phase file boundaries.

Standard library only. Compares against the baseline commit recorded in docs/verification/baseline.md.
Usage:
  python tools/check_scope.py --phase N
  python tools/check_scope.py --final
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Set

PROTECTED_FILES = {
    "app/core/downloader.py",
    "app/core/download_manager.py",
    "app/core/proc.py",
    "app/core/info_fetcher.py",
    "app/core/jobs.py",
    "app/core/url_tools.py",
    "app/core/history_db.py",
    "app/core/history_service.py",
    "app/core/thumbnails.py",
    "app/core/errors.py",
    "app/core/network_monitor.py",
    "app/core/app_updater.py",
    "app/core/tool_manager.py",
    "app/tools.json",
    "installer/setup.iss",
}

PHASE_ALLOWED_FILES = {
    1: {
        "tools/check_scope.py",
        "app/version.py",
        "requirements.txt",
    },
    2: {
        "app/core/file_actions.py",
        "app/ui/history_tab.py",
        "app/ui/recent_list.py",
        "app/ui/settings_dialog.py",
    },
    3: {
        "app/ui/video_tab.py",
        "app/ui/audio_tab.py",
    },
    4: {
        "app/ui/kit/progress_card.py",
        "app/ui/queue_widget.py",
        "app/ui/recent_list.py",
    },
    5: {
        "app/ui/video_tab.py",
        "app/ui/audio_tab.py",
        "app/ui/kit/progress_card.py",
        "app/ui/queue_widget.py",
        "app/ui/recent_list.py",
    },
    6: {
        "app/ui/history_tab.py",
        "app/ui/main_window.py",
    },
    7: {
        "app/ui/settings_dialog.py",
    },
    8: {
        "app/ui/header.py",
        "app/ui/main_window.py",
        "app/ui/theme.py",
        "app/ui/splash.py",
        "assets/arrow_down_dark.png",
        "assets/arrow_down_light.png",
    },
    9: {
        "app/main.py",
        "app/ui/main_window.py",
    },
    10: {
        "app/core/tool_manager.py",
        "app/tools.json",
        "installer/setup.iss",
        "README.md",
    },
    11: {
        "app/version.py",
        "version.json",
    },
}

ALWAYS_ALLOWED_PREFIXES = (
    "tests/",
    "docs/verification/",
)

ALWAYS_ALLOWED_EXACT = {
    "gemini.md",
}


def get_baseline_commit() -> str:
    """Read baseline commit from docs/verification/baseline.md or fallback."""
    baseline_doc = Path("docs/verification/baseline.md")
    if baseline_doc.exists():
        content = baseline_doc.read_text(encoding="utf-8")
        match = re.search(r"Baseline Commit:\s*`?([0-9a-fA-F]{7,40})`?", content)
        if match:
            return match.group(1).strip()
    return "51a9d986e139bd7ec4ebc3775c9d50584bdf154d"


def get_changed_files(baseline: str) -> List[str]:
    """Get list of all files changed relative to baseline (committed + staged + unstaged)."""
    # 1. Diff against working tree (staged & unstaged vs baseline)
    res = subprocess.run(
        ["git", "diff", "--name-only", baseline],
        capture_output=True,
        text=True,
        check=True,
    )
    changed = set(filter(None, res.stdout.strip().splitlines()))

    # 2. Also check untracked files
    res_untracked = subprocess.run(
        ["git", "status", "-uall", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in res_untracked.stdout.splitlines():
        if line.startswith("?? "):
            changed.add(line[3:].strip())

    return [f.replace("\\", "/").strip() for f in sorted(changed)]


def is_always_allowed(rel_path: str) -> bool:
    norm = rel_path.lower()
    if any(norm.startswith(p.lower()) for p in ALWAYS_ALLOWED_PREFIXES):
        return True
    if norm in ALWAYS_ALLOWED_EXACT or norm.endswith("/gemini.md"):
        return True
    return False


def check_scope(phase: int | None, is_final: bool) -> bool:
    baseline = get_baseline_commit()
    print(f"Scope Check: comparing against baseline commit {baseline}")

    try:
        changed_files = get_changed_files(baseline)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Failed to run git diff: {exc}")
        return False

    if not changed_files:
        print("Scope Check PASS: No files changed since baseline.")
        return True

    print(f"Changed files detected ({len(changed_files)}):")
    for f in changed_files:
        print(f"  - {f}")

    # Final check: Fail if ANY protected file changed
    if is_final:
        violating_protected = [f for f in changed_files if f in PROTECTED_FILES]
        if violating_protected:
            print("\nScope Check FAIL (--final): The following protected files were modified:")
            for f in violating_protected:
                print(f"  [PROTECTED] {f}")
            return False
        print("\nScope Check PASS (--final): Zero protected files modified.")
        return True

    # Phase check:
    # Cumulative allowed files up to phase N
    allowed_cumulative: Set[str] = set()
    for p in range(1, (phase or 1) + 1):
        allowed_cumulative.update(PHASE_ALLOWED_FILES.get(p, set()))

    disallowed: List[str] = []
    protected_violations: List[str] = []

    for f in changed_files:
        if is_always_allowed(f):
            continue

        # Check protected file violation (Phase 10 can modify specified files if allowed)
        if f in PROTECTED_FILES and (phase != 10 or f not in PHASE_ALLOWED_FILES.get(10, set())):
            protected_violations.append(f)
            continue

        if f not in allowed_cumulative:
            disallowed.append(f)

    if protected_violations or disallowed:
        print(f"\nScope Check FAIL (--phase {phase}):")
        if protected_violations:
            print("  Protected file violations (NEVER ALLOWED):")
            for f in protected_violations:
                print(f"    [PROTECTED] {f}")
        if disallowed:
            print(f"  Disallowed files for Phase {phase}:")
            for f in disallowed:
                print(f"    [OUT OF SCOPE] {f}")
        return False

    print(f"\nScope Check PASS (--phase {phase}): All changed files are within scope.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="YOuTUbE Scope Checker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", type=int, choices=range(1, 12), help="Phase number (1-11)")
    group.add_argument("--final", action="store_true", help="Final release check against protected files")

    args = parser.parse_args()
    success = check_scope(phase=args.phase, is_final=args.final)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
