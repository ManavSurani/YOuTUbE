"""Unit tests for app.core.file_actions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.file_actions import (
    build_select_command,
    open_file,
    open_folder,
    reveal_in_folder,
)


def test_exact_command_string_spaces():
    p = Path(r"C:\My Videos\funny clip.mp4")
    cmd = build_select_command(p)
    assert cmd == r'/select,"C:\My Videos\funny clip.mp4"'


def test_exact_command_string_unicode():
    p = Path(r"C:\Downloads\｜ ： ⧸ é 日本語 😀.mkv")
    cmd = build_select_command(p)
    assert cmd == r'/select,"C:\Downloads\｜ ： ⧸ é 日本語 😀.mkv"'


def test_select_command_keeps_path_text_as_given():
    assert build_select_command(r"C:\DOWNLOADS\Clip.mkv") == r'/select,"C:\DOWNLOADS\Clip.mkv"'


def test_missing_file_returns_false_and_message(tmp_path):
    missing_file = tmp_path / "does_not_exist.mp4"
    with patch("app.core.file_actions.open_folder") as mock_open_folder:
        mock_open_folder.return_value = (True, "")
        ok, msg = open_file(missing_file)
        assert ok is False
        assert "File not found. You can use Locate file." in msg
        # Parent folder should have been opened as fallback
        mock_open_folder.assert_called_once_with(tmp_path)


def test_fallback_order_open_fails_then_reveal(tmp_path):
    existing_file = tmp_path / "sample.zzz"
    existing_file.write_text("dummy")

    with patch("os.startfile", side_effect=OSError("No associated application")), \
         patch("app.core.file_actions.reveal_in_folder") as mock_reveal:
        mock_reveal.return_value = (True, "")

        ok, msg = open_file(existing_file)
        assert ok is False
        assert msg == "No app is set to open this type of file."
        mock_reveal.assert_called_once_with(existing_file.resolve())


def test_fallback_order_reveal_fails_then_parent(tmp_path):
    existing_file = tmp_path / "sample.zzz"
    existing_file.write_text("dummy")

    with patch("os.startfile", side_effect=OSError("No associated application")), \
         patch("app.core.file_actions.reveal_in_folder", return_value=(False, "Failed reveal")), \
         patch("app.core.file_actions.open_folder") as mock_open_folder:
        mock_open_folder.return_value = (True, "")

        ok, msg = open_file(existing_file)
        assert ok is False
        assert msg == "No app is set to open this type of file."
        mock_open_folder.assert_called_once_with(existing_file.resolve().parent)


def test_scan_no_start_hidden():
    module_path = Path("app/core/file_actions.py")
    assert module_path.exists()
    content = module_path.read_text(encoding="utf-8")
    assert "start_hidden" not in content
    assert "CREATE_NO_WINDOW" not in content


def test_non_windows_platform():
    with patch("sys.platform", "linux"):
        ok1, msg1 = open_file("/tmp/test.mp4")
        assert ok1 is False
        assert msg1 == "Not supported on this system"

        ok2, msg2 = reveal_in_folder("/tmp/test.mp4")
        assert ok2 is False
        assert msg2 == "Not supported on this system"

        ok3, msg3 = open_folder("/tmp")
        assert ok3 is False
        assert msg3 == "Not supported on this system"
