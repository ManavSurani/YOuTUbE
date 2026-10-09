"""End-to-end history sync tests verifying RecentList auto-refresh across tabs.

Qt Event Propagation Rule:
Never send a QShowEvent directly to a tab object (VideoTab or AudioTab).
RecentList installs its event filter on its direct parent container widget
(self.parent()), which is an internal layout container, NOT the outer tab itself.
Delivering an event directly to the tab object does not reach filters installed on
internal child containers. Therefore, tests must trigger show propagation via
`tab.hide(); tab.show()` or send QShowEvent directly to `tab.recent_list.parent()`.
"""

from pathlib import Path
from PySide6.QtCore import QEvent
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
import pytest

from app.core import history_service
from app.core.history_db import HistoryItem, add_item, init_db
from app.ui.audio_tab import AudioTab
from app.ui.recent_list import RecentRow
from app.ui.video_tab import VideoTab


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a clean temporary database for every test."""
    db_file = tmp_path / "test_recent_sync.db"
    monkeypatch.setattr("app.core.history_db.HISTORY_DB", db_file)
    monkeypatch.setattr("app.core.paths.HISTORY_DB", db_file)
    init_db(db_file)
    return db_file


def _seed_item(title: str, item_type: str, dummy_file: Path) -> int:
    item = HistoryItem(
        id=None,
        title=title,
        url="https://youtube.com/watch?v=12345678901",
        type=item_type,
        quality="1080p" if item_type == "video" else "MP3",
        file_path=str(dummy_file),
        size_bytes=1024,
        file_missing=0,
    )
    return add_item(item)


def test_recent_sync_clear_all(tmp_path):
    dummy_file = tmp_path / "dummy.mp4"
    dummy_file.write_bytes(b"content")

    _seed_item("Video 1", "video", dummy_file)
    _seed_item("Video 2", "video", dummy_file)
    _seed_item("Audio 1", "audio", dummy_file)
    _seed_item("Audio 2", "audio", dummy_file)

    vtab = VideoTab()
    atab = AudioTab()

    # Initial show propagation reaches internal container
    vtab.show()
    atab.show()
    assert vtab.recent_list.isVisible()
    assert atab.recent_list.isVisible()

    # Clear all history records without deleting files
    deleted_count, errors = history_service.clear_all(delete_files=False)
    assert deleted_count == 4
    assert not errors

    # Trigger show propagation via hide/show and container event;
    # NEVER deliver QShowEvent directly to tab object because eventFilter is on parent container.
    vtab.hide()
    vtab.show()
    QApplication.sendEvent(vtab.recent_list.parent(), QShowEvent())
    assert not vtab.recent_list.isVisible()

    atab.hide()
    atab.show()
    QApplication.sendEvent(atab.recent_list.parent(), QShowEvent())
    assert not atab.recent_list.isVisible()


def test_recent_sync_single_delete(tmp_path):
    dummy_file = tmp_path / "dummy.mp4"
    dummy_file.write_bytes(b"content")

    row1_id = _seed_item("Video A", "video", dummy_file)
    row2_id = _seed_item("Video B", "video", dummy_file)

    vtab = VideoTab()
    vtab.show()

    # Initial show: 2 rows shown
    assert vtab.recent_list.isVisible()
    rows = vtab.recent_list.findChildren(RecentRow)
    assert len(rows) == 2

    # Delete single item (strictly calling history_service.delete, not delete_item)
    ok, err = history_service.delete(row1_id, delete_file=False)
    assert ok
    assert not err

    # Trigger show propagation to container; never directly to outer tab
    vtab.hide()
    vtab.show()
    QApplication.sendEvent(vtab.recent_list.parent(), QShowEvent())

    assert vtab.recent_list.isVisible()
    remaining_rows = vtab.recent_list.findChildren(RecentRow)
    assert len(remaining_rows) == 1
    assert remaining_rows[0].item.id == row2_id


def test_recent_sync_consecutive_tab_switches(tmp_path):
    dummy_file = tmp_path / "dummy.mp4"
    dummy_file.write_bytes(b"content")

    _seed_item("Video Single", "video", dummy_file)

    vtab = VideoTab()
    vtab.show()

    # First switch / show
    vtab.hide()
    vtab.show()
    QApplication.sendEvent(vtab.recent_list.parent(), QShowEvent())

    header_labels_1 = [lbl for lbl in vtab.recent_list.findChildren(QLabel) if lbl.text() == "Recently downloaded"]
    see_all_btns_1 = [btn for btn in vtab.recent_list.findChildren(QPushButton) if "See all" in btn.text()]
    assert len(header_labels_1) == 1
    assert len(see_all_btns_1) == 1

    # Second switch / show
    vtab.hide()
    vtab.show()
    QApplication.sendEvent(vtab.recent_list.parent(), QShowEvent())

    header_labels_2 = [lbl for lbl in vtab.recent_list.findChildren(QLabel) if lbl.text() == "Recently downloaded"]
    see_all_btns_2 = [btn for btn in vtab.recent_list.findChildren(QPushButton) if "See all" in btn.text()]
    assert len(header_labels_2) == 1
    assert len(see_all_btns_2) == 1
