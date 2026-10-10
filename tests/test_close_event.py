"""Tests for Chunk C.4: Safe App Close Handler with shared deadline and dual-lane shutdown."""

import time
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

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
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", return_value=mock_mgr), \
         patch.object(QMessageBox, "exec") as mock_exec:
        win = MainWindow()
        try:
            event = QCloseEvent()
            win.closeEvent(event)

            assert event.isAccepted()
            mock_exec.assert_not_called()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


@pytest.mark.parametrize("video_active,audio_active", [
    (True, False),
    (False, True),
    (True, True),
])
def test_close_prompts_when_either_lane_active(video_active, audio_active):
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock(title="Video") if video_active else None
    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock(title="Audio") if audio_active else None

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
            exec_called = []

            def fake_exec(*args, **kwargs):
                exec_called.append(True)
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

                assert len(exec_called) == 1
                assert event.isAccepted()
                v_mgr.shutdown.assert_called_once()
                a_mgr.shutdown.assert_called_once()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_ignores_when_user_rejects():
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock(title="Running Video")
    a_mgr = MagicMock()
    a_mgr.active_job = None

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
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
                v_mgr.shutdown.assert_not_called()
                a_mgr.shutdown.assert_not_called()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_shutdown_called_on_both_lanes_before_waiting():
    actions = []

    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock()
    v_mgr.shutdown.side_effect = lambda: actions.append("v_shutdown")
    v_worker = MagicMock()
    v_worker.wait.side_effect = lambda *a: actions.append("v_wait") or True
    v_mgr._worker = v_worker

    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock()
    a_mgr.shutdown.side_effect = lambda: actions.append("a_shutdown")
    a_worker = MagicMock()
    a_worker.wait.side_effect = lambda *a: actions.append("a_wait") or True
    a_mgr._worker = a_worker

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
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
                assert actions[:2] == ["v_shutdown", "a_shutdown"]
                assert set(actions[2:]) == {"v_wait", "a_wait"}
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_returns_within_shared_deadline_when_workers_stop_quickly():
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock()
    v_worker = MagicMock()
    v_worker.wait.return_value = True
    v_worker.isRunning.return_value = False
    v_mgr._worker = v_worker

    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock()
    a_worker = MagicMock()
    a_worker.wait.return_value = True
    a_worker.isRunning.return_value = False
    a_mgr._worker = a_worker

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
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
                t0 = time.monotonic()
                win.closeEvent(event)
                duration = time.monotonic() - t0

                assert event.isAccepted()
                assert duration < 1.0
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_completes_and_logs_warning_when_worker_never_stops(caplog):
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock()
    v_worker = MagicMock()
    v_worker.wait.return_value = False
    v_worker.isRunning.return_value = True
    v_mgr._worker = v_worker

    a_mgr = MagicMock()
    a_mgr.active_job = None
    a_mgr._worker = None

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
            def fake_exec(*args, **kwargs):
                box = win.findChild(QMessageBox)
                if box:
                    for btn in box.buttons():
                        if btn.text() == "Quit":
                            box._mock_clicked = btn
                            break

            with patch("PySide6.QtWidgets.QMessageBox.exec", side_effect=fake_exec), \
                 patch("PySide6.QtWidgets.QMessageBox.clickedButton", side_effect=lambda *a: getattr(win.findChild(QMessageBox), "_mock_clicked", None)), \
                 caplog.at_level("WARNING"):
                event = QCloseEvent()
                win.closeEvent(event)

                assert event.isAccepted()
                assert any("Worker did not stop within deadline" in rec.message for rec in caplog.records)
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_cancels_both_lanes():
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock(title="Video")
    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock(title="Audio")

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
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
                v_mgr.shutdown.assert_called_once()
                a_mgr.shutdown.assert_called_once()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_uses_one_shared_deadline():
    import itertools

    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock()
    v_worker = MagicMock()
    v_mgr._worker = v_worker

    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock()
    a_worker = MagicMock()
    a_mgr._worker = a_worker

    timeouts = []
    v_worker.wait.side_effect = lambda ms: timeouts.append(ms) or True
    a_worker.wait.side_effect = lambda ms: timeouts.append(ms) or True

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    ticks = itertools.count(0.0, 0.75)

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm), \
         patch("app.ui.main_window.time.monotonic", side_effect=lambda: next(ticks)):
        win = MainWindow()
        try:
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
                assert len(timeouts) == 2
                assert timeouts[1] < timeouts[0]
                assert all(t <= 2000 for t in timeouts)
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_with_no_active_jobs_does_not_ask():
    v_mgr = MagicMock()
    v_mgr.active_job = None
    a_mgr = MagicMock()
    a_mgr.active_job = None

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm), \
         patch.object(QMessageBox, "exec") as mock_exec:
        win = MainWindow()
        try:
            event = QCloseEvent()
            win.closeEvent(event)

            assert event.isAccepted()
            mock_exec.assert_not_called()
            v_mgr.shutdown.assert_called_once()
            a_mgr.shutdown.assert_called_once()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()


def test_close_rejected_leaves_both_lanes_running():
    v_mgr = MagicMock()
    v_mgr.active_job = MagicMock(title="Video")
    a_mgr = MagicMock()
    a_mgr.active_job = MagicMock(title="Audio")

    def fake_get_dm(kind):
        return v_mgr if kind == "video" else a_mgr

    with patch("app.ui.main_window.NetworkMonitor.start"), \
         patch("app.ui.main_window.UpdateCheckWorker.start"), \
         patch("app.ui.main_window.get_download_manager", side_effect=fake_get_dm):
        win = MainWindow()
        try:
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
                v_mgr.shutdown.assert_not_called()
                a_mgr.shutdown.assert_not_called()
        finally:
            if hasattr(win, "tray_icon") and win.tray_icon:
                win.tray_icon.hide()
                win.tray_icon.deleteLater()
            win.deleteLater()
            QApplication.processEvents()

