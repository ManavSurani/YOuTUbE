"""Tests for Phase 5 History tab overhaul: rows, icon actions, filters, search focus, delete flow, locate, and 500-row performance."""

import time
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
import pytest

from app.core.history_db import HistoryItem, add_item, init_db, list_items
from app.ui.history_tab import (
    ClearAllDialog,
    HistoryDeleteDialog,
    HistoryRowWidget,
    HistoryTab,
)


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a clean temporary database for every test."""
    db_file = tmp_path / "test_history.db"
    monkeypatch.setattr("app.core.history_db.HISTORY_DB", db_file)
    monkeypatch.setattr("app.core.paths.HISTORY_DB", db_file)
    monkeypatch.setattr("app.core.history_service.DEFAULT_DOWNLOADS", tmp_path)
    init_db(db_file)
    return db_file


def test_history_row_file_present(tmp_path):
    """Row displays correctly when file exists on disk."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.write_bytes(b"content")

    item = HistoryItem(
        id=1,
        title="Test Video Title",
        url="https://youtube.com/watch?v=abc12345678",
        type="video",
        quality="1080p",
        file_path=str(dummy_file),
        size_bytes=1024,
        file_missing=0,
    )

    row = HistoryRowWidget(item)
    assert not row.play_btn.isHidden()
    assert row.locate_btn.isHidden()
    assert "1080p" in row.meta_label.text()
    assert "File missing" not in row.meta_label.text()

    # Tooltips check
    assert row.play_btn.toolTip() == "Play file"
    assert row.folder_btn.toolTip() == "Show in folder"
    assert row.copy_btn.toolTip() == "Copy link"
    assert row.redownload_btn.toolTip() == "Re-download"
    assert row.delete_btn.toolTip() == "Delete"
    assert row.delete_btn.is_danger is True


def test_history_row_file_missing(tmp_path):
    """Row displays 'File missing' and Locate button when file is absent."""
    missing_file = tmp_path / "non_existent.mp4"

    item = HistoryItem(
        id=2,
        title="Missing Video",
        url="https://youtube.com/watch?v=xyz12345678",
        type="video",
        quality="720p",
        file_path=str(missing_file),
        size_bytes=2048,
        file_missing=1,
    )

    row = HistoryRowWidget(item)
    assert row.play_btn.isHidden()
    assert not row.locate_btn.isHidden()
    assert row.locate_btn.toolTip() == "Locate missing file"
    assert "File missing" in row.meta_label.text()


def test_history_row_copy_link(tmp_path):
    """Clicking Copy link copies URL to clipboard and flashes success."""
    item = HistoryItem(
        id=3,
        title="Copy Link Test",
        url="https://youtube.com/watch?v=testcopy123",
        type="video",
        quality="1080p",
        file_path=str(tmp_path / "vid.mp4"),
        size_bytes=100,
        file_missing=0,
    )
    row = HistoryRowWidget(item)
    row.copy_btn.click()

    assert QGuiApplication.clipboard().text() == item.url
    assert row.copy_btn._is_success is True


def test_history_row_redownload_signal(tmp_path):
    """Clicking Re-download emits url, type, and quality."""
    item = HistoryItem(
        id=4,
        title="Redownload Test",
        url="https://youtube.com/watch?v=redownload1",
        type="audio",
        quality="MP3",
        file_path=str(tmp_path / "audio.mp3"),
        size_bytes=500,
        file_missing=0,
    )
    row = HistoryRowWidget(item)

    emitted = []
    row.redownload.connect(lambda u, t, q: emitted.append((u, t, q)))
    row.redownload_btn.click()

    assert len(emitted) == 1
    assert emitted[0] == (item.url, "audio", "MP3")


def test_history_delete_dialog_options(tmp_path):
    """Custom delete dialog offers all three actions."""
    f = tmp_path / "present.mp4"
    f.write_bytes(b"data")

    item = HistoryItem(
        id=5,
        title="Delete Me",
        url="https://youtube.com/watch?v=del12345678",
        type="video",
        quality="1080p",
        file_path=str(f),
        size_bytes=4,
        file_missing=0,
    )

    # Test Delete file too
    dlg1 = HistoryDeleteDialog(item, file_exists=True)
    assert dlg1.btn_delete_file.text() == "Delete file too"
    dlg1._on_delete_file()
    assert dlg1.selected_action == HistoryDeleteDialog.ACTION_DELETE_FILE_TOO

    # Test Remove from history only
    dlg2 = HistoryDeleteDialog(item, file_exists=True)
    dlg2._on_history_only()
    assert dlg2.selected_action == HistoryDeleteDialog.ACTION_REMOVE_HISTORY_ONLY

    # Test Cancel
    dlg3 = HistoryDeleteDialog(item, file_exists=True)
    assert dlg3.selected_action == HistoryDeleteDialog.ACTION_CANCEL


def test_history_delete_locked_file_keeps_row(tmp_path, monkeypatch):
    """If file deletion fails (locked file), row is kept in history."""
    f = tmp_path / "locked.mp4"
    f.write_bytes(b"locked")

    item = HistoryItem(
        id=6,
        title="Locked Video",
        url="https://youtube.com/watch?v=locked12345",
        type="video",
        quality="1080p",
        file_path=str(f),
        size_bytes=6,
        file_missing=0,
    )
    row_id = add_item(item)
    item.id = row_id

    row = HistoryRowWidget(item)

    # Mock dialog to select ACTION_DELETE_FILE_TOO
    def mock_exec(self):
        self.selected_action = HistoryDeleteDialog.ACTION_DELETE_FILE_TOO

    monkeypatch.setattr(HistoryDeleteDialog, "exec", mock_exec)

    # Mock history_service.delete to simulate locked file failure
    monkeypatch.setattr(
        "app.core.history_service.delete",
        lambda r_id, delete_file: (False, "File is locked by media player"),
    )

    warnings_shown = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, text: warnings_shown.append((title, text)),
    )

    deleted_emitted = []
    row.deleted.connect(lambda: deleted_emitted.append(True))

    row._delete_prompt()

    # Warning shown and row NOT deleted
    assert len(warnings_shown) == 1
    assert "File is locked" in warnings_shown[0][1]
    assert len(deleted_emitted) == 0


def test_history_locate_file(tmp_path, monkeypatch):
    """Locate file successfully reconnects a moved file in-place."""
    old_path = tmp_path / "moved_away.mp4"
    new_path = tmp_path / "found_file.mp4"
    new_path.write_bytes(b"restored content")

    item = HistoryItem(
        id=None,
        title="Moved Video",
        url="https://youtube.com/watch?v=moved1234567",
        type="video",
        quality="1080p",
        file_path=str(old_path),
        size_bytes=100,
        file_missing=1,
    )
    row_id = add_item(item)
    item.id = row_id

    row = HistoryRowWidget(item)
    assert row.play_btn.isHidden()
    assert not row.locate_btn.isHidden()

    # Mock file dialog returning new_path
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(new_path), "All Files (*.*)"),
    )

    row.locate_file()

    assert item.file_missing == 0
    assert not row.play_btn.isHidden()
    assert row.locate_btn.isHidden()
    assert "File missing" not in row.meta_label.text()

    # Verify DB updated
    items = list_items()
    assert len(items) == 1
    assert items[0].file_path == str(new_path)
    assert items[0].file_missing == 0


def test_search_box_focus_policy():
    """Search box does NOT steal focus on tab switch (B12 fix)."""
    tab = HistoryTab()
    # Focus policy must be ClickFocus so opening the tab leaves focus on container
    assert tab.search_input.focusPolicy() == Qt.FocusPolicy.ClickFocus

    tab.show()
    QApplication.processEvents()

    # Verify search_input does NOT have active keyboard focus
    assert not tab.search_input.hasFocus()


def test_filter_chips_and_search(tmp_path):
    """Filter chips (All/Video/Audio) and text search properly filter rows."""
    f1 = tmp_path / "v1.mp4"
    f1.write_bytes(b"v1")
    f2 = tmp_path / "a1.mp3"
    f2.write_bytes(b"a1")

    add_item(HistoryItem(
        id=None,
        title="Python Tutorial Video",
        url="https://youtube.com/watch?v=py1",
        type="video",
        quality="1080p",
        file_path=str(f1),
        size_bytes=100,
    ))
    add_item(HistoryItem(
        id=None,
        title="Podcast Audio Episode",
        url="https://youtube.com/watch?v=pod1",
        type="audio",
        quality="MP3",
        file_path=str(f2),
        size_bytes=200,
    ))

    tab = HistoryTab()
    tab.reload_history()
    assert len(tab._all_items) == 2

    # Filter to Video
    tab.chip_video.click()
    assert len(tab._all_items) == 1
    assert tab._all_items[0].type == "video"

    # Filter to Audio
    tab.chip_audio.click()
    assert len(tab._all_items) == 1
    assert tab._all_items[0].type == "audio"

    # Back to All
    tab.chip_all.click()
    assert len(tab._all_items) == 2

    # Search filter
    tab.search_input.setText("Podcast")
    assert len(tab._all_items) == 1
    assert tab._all_items[0].title == "Podcast Audio Episode"


def test_lazy_loading_performance_500_rows(tmp_path):
    """Tab with 500 rows opens in under 1 second via lazy loading."""
    dummy_file = tmp_path / "file.mp4"
    dummy_file.write_bytes(b"test")

    # Bulk insert 500 items into SQLite
    for i in range(500):
        add_item(HistoryItem(
            id=None,
            title=f"Bulk History Item #{i:03d}",
            url=f"https://youtube.com/watch?v=bulk_{i}",
            type="video" if i % 2 == 0 else "audio",
            quality="1080p" if i % 2 == 0 else "MP3",
            file_path=str(dummy_file),
            size_bytes=1024 * (i + 1),
            file_missing=0,
        ))

    tab = HistoryTab()

    start_time = time.perf_counter()
    tab.reload_history()
    elapsed = time.perf_counter() - start_time

    # Performance requirement: under 1.0 second
    assert elapsed < 1.0, f"History tab took {elapsed:.3f}s to reload 500 items"

    # Lazy loading check: initial page renders 50 rows
    assert len(tab._all_items) == 500
    assert tab._rendered_count == 50
    assert len(tab._rendered_rows) == 50

    # Simulate scroll to load next page
    tab._render_next_page()
    assert tab._rendered_count == 100
    assert len(tab._rendered_rows) == 100
