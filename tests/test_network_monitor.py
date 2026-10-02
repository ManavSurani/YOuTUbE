import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.network_monitor import NetworkMonitor  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def test_network_monitor_debouncing_and_transitions():

    # Flow:
    # 0: True (initially online)
    # 1: False (1st fail - ignored)
    # 2: False (2nd fail - triggers went_offline)
    # 3: False (3rd fail - staying offline, no additional emit)
    # 4: True (recovers - triggers came_online)
    # 5: True (staying online, no additional emit)
    results = [True, False, False, False, True, True]
    idx = 0

    def mock_check():
        nonlocal idx
        val = results[idx] if idx < len(results) else results[-1]
        idx += 1
        return val

    monitor = NetworkMonitor(check_fn=mock_check, check_interval=0.03)

    offline_events = []
    online_events = []
    state_events = []

    monitor.went_offline.connect(lambda: offline_events.append(1), Qt.DirectConnection)
    monitor.came_online.connect(lambda: online_events.append(1), Qt.DirectConnection)
    monitor.state_changed.connect(lambda s: state_events.append(s), Qt.DirectConnection)

    monitor.start()
    time.sleep(0.3)
    monitor.stop()
    assert monitor.wait(1000)

    # Went offline once, came online once
    assert len(offline_events) == 1
    assert len(online_events) == 1
    assert state_events == [False, True]
    assert monitor.is_online() is True


def test_single_failure_does_not_trigger_offline():
    # Flow:
    # 0: True
    # 1: False (1st fail)
    # 2: True (recovers before 2nd fail)
    # 3: True
    results = [True, False, True, True]
    idx = 0

    def mock_check():
        nonlocal idx
        val = results[idx] if idx < len(results) else True
        idx += 1
        return val

    monitor = NetworkMonitor(check_fn=mock_check, check_interval=0.03)
    offline_events = []

    monitor.went_offline.connect(lambda: offline_events.append(1), Qt.DirectConnection)
    monitor.start()
    time.sleep(0.2)
    monitor.stop()
    assert monitor.wait(1000)

    # 1 failure never triggered offline
    assert len(offline_events) == 0
    assert monitor.is_online() is True


def test_network_monitor_clean_exit():
    def mock_check():
        return True

    monitor = NetworkMonitor(check_fn=mock_check, check_interval=0.03)
    monitor.start()
    time.sleep(0.05)
    assert monitor.isRunning()
    monitor.stop()
    clean_exit = monitor.wait(1000)
    assert clean_exit is True
    assert not monitor.isRunning()


def test_video_tab_offline_controls_and_cancel(tmp_path):
    from app.ui.video_tab import VideoTab

    tab = VideoTab()
    assert tab.url_input.isEnabled()
    assert tab.download_btn.isEnabled()

    # Disconnect
    tab.set_online(False)
    assert not tab.url_input.isEnabled()
    assert not tab.fetch_btn.isEnabled()
    assert not tab.quality_combo.isEnabled()
    assert not tab.download_btn.isEnabled()

    # Reconnect
    tab.set_online(True)
    assert tab.url_input.isEnabled()
    assert tab.fetch_btn.isEnabled()
    assert tab.quality_combo.isEnabled()
    assert tab.download_btn.isEnabled()

    # Simulate download in progress when net drops
    part_file = tmp_path / "video.mkv.part"
    part_file.write_text("partial_download_bytes")

    tab._is_downloading = True
    tab._saved_cmd = ["dummy_cmd"]
    tab._saved_out_dir = str(tmp_path)

    tab.set_online(False)
    assert tab._paused_for_offline is True
    assert tab.stage_label.text() == "Waiting for internet…"
    assert tab.cancel_btn.isEnabled() is True
    assert not tab.download_btn.isEnabled()
    assert part_file.exists()  # Kept on pause!

    # Cancel while waiting cleans leftovers
    tab.cancel_download()
    assert tab.stage_label.text() == "Cancelled."
    assert not tab.cancel_btn.isEnabled()
    assert not part_file.exists()  # Removed on cancel!


def test_audio_tab_offline_controls():
    from app.ui.audio_tab import AudioTab

    tab = AudioTab()
    assert tab.url_input.isEnabled()
    assert tab.download_btn.isEnabled()
    assert tab.format_combo.isEnabled()
    assert tab.embed_cover_check.isEnabled()
    assert tab.embed_meta_check.isEnabled()

    tab.set_online(False)
    assert not tab.url_input.isEnabled()
    assert not tab.fetch_btn.isEnabled()
    assert not tab.format_combo.isEnabled()
    assert not tab.embed_cover_check.isEnabled()
    assert not tab.embed_meta_check.isEnabled()
    assert not tab.download_btn.isEnabled()

    tab.set_online(True)
    assert tab.url_input.isEnabled()
    assert tab.fetch_btn.isEnabled()
    assert tab.format_combo.isEnabled()
    assert tab.embed_cover_check.isEnabled()
    assert tab.embed_meta_check.isEnabled()
    assert tab.download_btn.isEnabled()


def test_main_window_network_transitions(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from app.ui.main_window import MainWindow

    popup_calls = []

    def mock_info(parent, title, text):
        popup_calls.append((title, text))

    monkeypatch.setattr(QMessageBox, "information", mock_info)

    win = MainWindow()
    try:
        # Initially online
        assert win.status_label.text() == "Online"
        assert win.video_tab.url_input.isEnabled()

        # Trigger went offline
        win._on_went_offline()
        assert win.status_label.text() == "Offline"
        assert win.status_dot._color.name().upper() == "#CC0000"
        assert not win.video_tab.url_input.isEnabled()
        assert not win.audio_tab.url_input.isEnabled()
        # History tab stays fully usable
        assert win.history_tab.isEnabled()
        assert len(popup_calls) == 1
        assert "Internet is off" in popup_calls[0][1]

        # Trigger came online
        win._on_came_online()
        assert win.status_label.text() == "Online"
        assert win.status_dot._color.name().upper() == "#2BA640"
        assert win.video_tab.url_input.isEnabled()
        assert win.audio_tab.url_input.isEnabled()
        assert len(popup_calls) == 1  # No popup on coming back online

        # Second outage triggers popup again
        win._on_went_offline()
        assert len(popup_calls) == 2
    finally:
        win.network_monitor.stop()
        win.network_monitor.wait(1000)
        win.close()


