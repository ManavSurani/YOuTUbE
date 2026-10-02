import sys
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.video_tab import VideoTab, VideoQueueItem
from app.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication(sys.argv)


def test_video_queue_sequential_and_remove(tmp_path, monkeypatch):
    tab = VideoTab()
    monkeypatch.setattr(tab, "_start_worker", lambda initial_percent=0.0: None)
    monkeypatch.setattr(tab, "fetch_url", lambda: None)

    # Queue 3 links with valid 11-char IDs
    tab.url_input.setText("https://www.youtube.com/watch?v=item1123456")
    tab.add_to_queue()
    tab.url_input.setText("https://www.youtube.com/watch?v=item2123456")
    tab.add_to_queue()
    tab.url_input.setText("https://www.youtube.com/watch?v=item3123456")
    tab.add_to_queue()

    assert len(tab._queue) == 3
    assert tab._queue[0].status == "downloading"
    assert tab._queue[1].status == "waiting"
    assert tab._queue[2].status == "waiting"

    # Remove waiting item 2
    tab._remove_queue_item(tab._queue[1])
    assert len(tab._queue) == 2
    assert tab._queue[1].url == "https://www.youtube.com/watch?v=item3123456"

    # Finish item 1 -> item 3 automatically starts
    tab._on_finished(str(tmp_path / "item1.mkv"))
    assert tab._queue[0].status == "done"
    assert tab._queue[1].status == "downloading"

    # Finish item 3 -> queue completes
    tab._on_finished(str(tmp_path / "item3.mkv"))
    assert tab._queue[1].status == "done"
    assert not tab._is_downloading


def test_video_queue_error_in_middle_moves_on(tmp_path, monkeypatch):
    tab = VideoTab()
    monkeypatch.setattr(tab, "_start_worker", lambda initial_percent=0.0: None)
    monkeypatch.setattr(tab, "fetch_url", lambda: None)

    tab.url_input.setText("https://www.youtube.com/watch?v=good1123456")
    tab.add_to_queue()
    tab.url_input.setText("https://www.youtube.com/watch?v=bad21234567")
    tab.add_to_queue()
    tab.url_input.setText("https://www.youtube.com/watch?v=good3123456")
    tab.add_to_queue()

    assert tab._queue[0].status == "downloading"

    # Finish item 1
    tab._on_finished(str(tmp_path / "good1.mkv"))
    assert tab._queue[0].status == "done"
    assert tab._queue[1].status == "downloading"

    # Item 2 fails with private video error
    tab._on_failed("ERROR: Private video. Sign in to view.")
    assert tab._queue[1].status == "failed"
    assert "private" in tab._queue[1].error_reason.lower()

    # Queue automatically moved on to item 3!
    assert tab._queue[2].status == "downloading"

    # Item 3 finishes
    tab._on_finished(str(tmp_path / "good3.mkv"))
    assert tab._queue[2].status == "done"


def test_queue_cancel_stops_and_waits(tmp_path, monkeypatch):
    tab = VideoTab()
    monkeypatch.setattr(tab, "_start_worker", lambda initial_percent=0.0: None)
    monkeypatch.setattr(tab, "fetch_url", lambda: None)

    tab.url_input.setText("https://www.youtube.com/watch?v=link1123456")
    tab.add_to_queue()
    tab.url_input.setText("https://www.youtube.com/watch?v=link2123456")
    tab.add_to_queue()

    assert tab._queue[0].status == "downloading"
    assert tab._queue[1].status == "waiting"

    # Cancel while item 1 is downloading
    tab.cancel_download()
    assert tab._queue[0].status == "cancelled"
    # Queue does not automatically start item 2
    assert tab._queue[1].status == "waiting"
    assert not tab._is_downloading


def test_finish_notification_on_inactive_window(monkeypatch):
    monkeypatch.setattr("app.ui.main_window.NetworkMonitor.start", lambda self: None)
    monkeypatch.setattr("app.ui.main_window.UpdateCheckWorker.start", lambda self: None)
    win = MainWindow()
    win.show()
    try:
        mock_show_message = MagicMock()
        monkeypatch.setattr(win.tray_icon, "showMessage", mock_show_message)

        # 1. When window is inactive -> toast shown
        monkeypatch.setattr(win, "isActiveWindow", lambda: False)
        win._on_download_finished_notification("My Video")
        mock_show_message.assert_called_once()
        assert "Download finished" in mock_show_message.call_args[0][1]

        # 2. When window is active -> no toast
        mock_show_message.reset_mock()
        monkeypatch.setattr(win, "isActiveWindow", lambda: True)
        win._on_download_finished_notification("My Video")
        mock_show_message.assert_not_called()
    finally:
        win.tray_icon.hide()
        win.close()
        _app.processEvents()
