"""Test that all required dependencies are installed and importable."""

from pathlib import Path


def test_requirements_dependencies_importable():
    req_file = Path("requirements.txt")
    assert req_file.exists()
    lines = [line.strip().lower() for line in req_file.read_text().splitlines() if line.strip()]

    assert "pywin32" in lines
    assert "pyside6" in lines
    assert "send2trash" in lines

    # Verify imports
    import PySide6
    import send2trash
    import win32com.client

    assert PySide6 is not None
    assert send2trash is not None
    assert win32com.client is not None
