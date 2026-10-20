"""Test that all required dependencies are installed, pinned, and importable."""

from pathlib import Path


def test_requirements_dependencies_importable():
    req_file = Path("requirements.txt")
    assert req_file.exists()
    lines = [line.strip().lower() for line in req_file.read_text().splitlines() if line.strip()]

    pkg_names = [line.split("==")[0].strip() for line in lines]
    assert "pywin32" in pkg_names
    assert "pyside6" in pkg_names
    assert "send2trash" in pkg_names

    # Verify that all dependencies are pinned (T3)
    for line in lines:
        assert "==" in line, f"Dependency line '{line}' is not pinned with =="

    # Verify imports
    import PySide6
    import send2trash
    import win32com.client

    assert PySide6 is not None
    assert send2trash is not None
    assert win32com.client is not None
