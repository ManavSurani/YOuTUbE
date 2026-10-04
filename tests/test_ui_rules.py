"""Architecture rule tests for app/ui:
1. No plain QPushButton outside app/ui/kit/ except an explicit approved exceptions list.
2. Zero imports of start_hidden in app/ui/ (Rule R1: start_hidden must never be called on windows or in UI).
"""

from pathlib import Path


# Explicitly approved exceptions for link-style buttons or special header tab widgets
APPROVED_QPUSHBUTTON_EXCEPTIONS = {
    "app/ui/header.py": [
        "QPushButton(name, self)",  # Flat tab header items
    ],
    "app/ui/recent_list.py": [
        "QPushButton(link_text, self)",  # "See all video/audio history →" link
    ],
    "app/ui/settings_dialog.py": [
        "QPushButton(\"Open download folder\", self)",  # Blue link to open folder
    ],
    "app/ui/main_window.py": [
        "QPushButton(\"Update now\", self)",  # Update banner action button
        "QPushButton(\"Later\", self)",       # Update banner dismiss button
    ],
}


def test_no_unapproved_plain_qpushbutton_in_ui():
    """Fail if QPushButton( appears outside app/ui/kit/, except explicit approved list."""
    ui_dir = Path("app/ui")
    violations = []

    for py_file in ui_dir.rglob("*.py"):
        rel_path = py_file.as_posix()
        # Skip app/ui/kit/ (kit components are allowed to implement or wrap QPushButton)
        if "/kit/" in rel_path:
            continue

        lines = py_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            if "QPushButton(" in line:
                allowed_patterns = APPROVED_QPUSHBUTTON_EXCEPTIONS.get(rel_path, [])
                if not any(pattern in line for pattern in allowed_patterns):
                    violations.append(f"{rel_path}:{idx}: {line.strip()}")

    assert not violations, f"Found unapproved plain QPushButton usages:\n" + "\n".join(violations)


def test_no_start_hidden_imported_in_ui():
    """Fail if any file under app/ui imports start_hidden."""
    ui_dir = Path("app/ui")
    violations = []

    for py_file in ui_dir.rglob("*.py"):
        rel_path = py_file.as_posix()
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            if "start_hidden" in line and ("import" in line or "from" in line):
                violations.append(f"{rel_path}:{idx}: {line.strip()}")

    assert not violations, f"Found start_hidden imports in app/ui:\n" + "\n".join(violations)
