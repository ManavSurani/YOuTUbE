"""Tests for Chunk 9.2: Cancel the download when closing (U4)."""

from unittest.mock import MagicMock, patch
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
import pytest

from app.ui.main_window import MainWindow


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_close_without_running_job_closes_without_question():
    mock_mgr = MagicMock()
    mock_mgr.active_job = None

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.get_download_manager", return_value=mock_mgr), \
         patch.object(QMessageBox, "exec") as mock_exec:
        win = MainWindow()
        event = QCloseEvent()
        win.closeEvent(event)

        assert event.isAccepted()
        mock_exec.assert_not_called()
        mock_mgr.cancel_active.assert_not_called()


def test_close_with_running_job_keep_downloading_ignores_event():
    mock_mgr = MagicMock()
    mock_mgr.active_job = MagicMock(title="Running Video")

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.get_download_manager", return_value=mock_mgr):
        win = MainWindow()

        def fake_exec(*args, **kwargs):
            box = win.findChild(QMessageBox)
            if box:
                for btn in box.buttons():
                    if btn.text() == "Keep downloading":
                        box._mock_clicked = btn
                        break

        with patch("PySide6.QtWidgets.QMessageBox.exec", side_effect=fake_exec), \
             patch("PySide6.QtWidgets.QMessageBox.clickedButton", side_effect=lambda *a: getattr(win.findChild(QMessageBox), "_mock_clicked", None)):
            event = QCloseEvent()
            win.closeEvent(event)

            assert not event.isAccepted()
            mock_mgr.cancel_active.assert_not_called()


def test_close_with_running_job_quit_cancels_active():
    mock_mgr = MagicMock()
    mock_mgr.active_job = MagicMock(title="Running Video")
    fake_worker = MagicMock()
    mock_mgr._worker = fake_worker

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.get_download_manager", return_value=mock_mgr):
        win = MainWindow()

        def fake_exec(*args, **kwargs):
            box = win.findChild(QMessageBox)
            if box:
                for btn in box.buttons():
                    if btn.text() == "Quit":
                        box._mock_clicked = btn
                        break

        with patch("PySide6.QtWidgets.QMessageBox.exec", side_effect=fake_exec), \
             patch("PySide6.QtWidgets.QMessageBox.clickedButton", side_effect=lambda *a: getattr(win.findChild(QMessageBox), "_mock_clicked", None)):
            event = QCloseEvent()
            win.closeEvent(event)

            assert event.isAccepted()
            mock_mgr.cancel_active.assert_called_once()
            fake_worker.wait.assert_called_once_with(2000)

