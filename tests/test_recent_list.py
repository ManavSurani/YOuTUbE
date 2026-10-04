"""Tests for RecentList and RecentRow file actions."""

from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QPushButton
import pytest

from app.core.history_db import HistoryItem
from app.ui.recent_list import RecentList, RecentRow


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_recent_row_play_and_open_folder_call_helper(tmp_path):
    dummy_file = tmp_path / "song.mp3"
    dummy_file.write_bytes(b"content")

    item = HistoryItem(
        id=1,
        title="Recent Song Title",
        url="https://youtube.com/watch?v=song1234567",
        type="audio",
        quality="MP3",
        file_path=str(dummy_file),
        size_bytes=2048,
        file_missing=0,
    )

    row = RecentRow(item)
    play_btn = None
    folder_btn = None
    for btn in row.findChildren(QPushButton):
        if btn.text() == "Play":
            play_btn = btn
        elif btn.text() == "Open folder":
            folder_btn = btn

    assert play_btn is not None
    assert folder_btn is not None

    with patch("app.ui.recent_list.open_file", return_value=(True, "")) as mock_open:
        play_btn.click()
        mock_open.assert_called_once_with(str(dummy_file))

    with patch("app.ui.recent_list.reveal_in_folder", return_value=(True, "")) as mock_reveal:
        folder_btn.click()
        mock_reveal.assert_called_once_with(str(dummy_file))

    with patch("app.ui.recent_list.open_file", return_value=(False, "Cannot play file")):
        with patch.object(row, "_show_feedback") as mock_feedback:
            play_btn.click()
            mock_feedback.assert_called_once_with("Cannot play file")
