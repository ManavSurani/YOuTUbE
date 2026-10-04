"""Tests for RecentList and RecentRow file actions."""

from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
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


def test_recent_list_refresh_no_duplicate_see_all(monkeypatch):
    mock_items = [
        HistoryItem(
            id=i,
            title=f"Video {i}",
            url=f"https://youtube.com/watch?v=vid{i}123456",
            type="video",
            quality="1080p",
            file_path="/path/to/vid",
            size_bytes=1024,
            file_missing=0,
        )
        for i in range(1, 4)
    ]
    monkeypatch.setattr("app.ui.recent_list.list_items", lambda type_filter: mock_items)

    recent_vid = RecentList(kind="video")
    recent_vid.refresh()
    recent_vid.refresh()
    recent_vid.refresh()

    see_all_btns = [btn for btn in recent_vid.findChildren(QPushButton) if "See all" in btn.text()]
    assert len(see_all_btns) == 1
    assert see_all_btns[0].text() == "See all video history →"


def test_recent_list_audio_label_and_signal(monkeypatch):
    mock_items = [
        HistoryItem(
            id=i,
            title=f"Audio {i}",
            url=f"https://youtube.com/watch?v=aud{i}123456",
            type="audio",
            quality="MP3",
            file_path="/path/to/aud",
            size_bytes=1024,
            file_missing=0,
        )
        for i in range(1, 8)
    ]
    monkeypatch.setattr("app.ui.recent_list.list_items", lambda type_filter: mock_items)

    recent_aud = RecentList(kind="audio")
    recent_aud.refresh()

    see_all_btns = [btn for btn in recent_aud.findChildren(QPushButton) if "See all" in btn.text()]
    assert len(see_all_btns) == 1
    assert see_all_btns[0].text() == "See all audio history →"

    # At most 5 rows
    assert len(recent_aud.findChildren(RecentRow)) == 5

    # Signal carries "audio"
    received = []
    recent_aud.see_all_clicked.connect(lambda k: received.append(k))
    see_all_btns[0].click()
    assert received == ["audio"]


def test_recent_row_missing_file_no_play_btn_and_shows_file_missing(tmp_path):
    missing_path = tmp_path / "deleted_video.mp4"
    assert not missing_path.exists()

    item = HistoryItem(
        id=99,
        title="Missing Video",
        url="https://youtube.com/watch?v=missing12345",
        type="video",
        quality="1080p",
        file_path=str(missing_path),
        size_bytes=0,
        file_missing=1,
    )

    row = RecentRow(item)

    play_btns_all = [btn for btn in row.findChildren(QPushButton) if btn.text() == "Play"]
    assert len(play_btns_all) == 0

    folder_btns = [btn for btn in row.findChildren(QPushButton) if btn.text() == "Open folder"]
    assert len(folder_btns) == 1

    labels = [lbl.text() for lbl in row.findChildren(QLabel)]
    assert any("File missing" in text for text in labels)
    assert not any("0 B" in text for text in labels)

    meta_labels = [lbl for lbl in row.findChildren(QLabel) if "File missing" in lbl.text()]
    assert len(meta_labels) == 1
    assert "#FF4E45" not in meta_labels[0].styleSheet()
    assert "#AAAAAA" in meta_labels[0].styleSheet()

