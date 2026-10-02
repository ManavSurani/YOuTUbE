import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.app_updater import (
    parse_version,
    check_manifest_dict,
    check_for_update,
    should_check_update,
    UpdateInfo,
    UpdateDownloadWorker,
    launch_silent_installer,
)

_app = QApplication.instance() or QApplication(sys.argv)


def test_parse_version():
    assert parse_version("1.10.0") == (1, 10, 0)
    assert parse_version("1.9.0") == (1, 9, 0)
    assert parse_version("1.10.0") > parse_version("1.9.0")
    assert parse_version("v2.0.1") == (2, 0, 1)
    assert parse_version("1.0") == (1, 0)


def test_manifest_version_comparisons():
    # Newer version -> available
    manifest = {
        "latest_version": "1.10.0",
        "installer_url": "https://example.com/setup.exe",
        "sha256": "abcdef123456",
    }
    res = check_manifest_dict(manifest, current_version="1.9.0")
    assert res.status == "available"
    assert res.latest_version == "1.10.0"

    # Equal version -> none
    res_equal = check_manifest_dict(manifest, current_version="1.10.0")
    assert res_equal.status == "none"

    # Older manifest -> none
    res_older = check_manifest_dict(manifest, current_version="2.0.0")
    assert res_older.status == "none"


def test_manifest_required_min_supported_version():
    manifest = {
        "latest_version": "1.5.0",
        "min_supported_version": "1.2.0",
        "installer_url": "https://example.com/setup.exe",
        "sha256": "abcdef123456",
    }
    # Current version 1.0.0 < 1.2.0 -> required
    res = check_manifest_dict(manifest, current_version="1.0.0")
    assert res.status == "required"

    # Current version 1.2.0 >= 1.2.0 -> available
    res_avail = check_manifest_dict(manifest, current_version="1.2.0")
    assert res_avail.status == "available"


def test_manifest_required_force_update():
    manifest = {
        "latest_version": "1.1.0",
        "installer_url": "https://example.com/setup.exe",
        "sha256": "abcdef123456",
        "force_update": True,
    }
    res = check_manifest_dict(manifest, current_version="1.0.0")
    assert res.status == "required"


def test_manifest_bad_data_and_network_failure():
    # Missing fields
    assert check_manifest_dict({}, current_version="1.0.0").status == "none"
    assert check_manifest_dict({"latest_version": "1.1.0"}, current_version="1.0.0").status == "none"

    # Network error / bad URL
    res = check_for_update("http://127.0.0.1:9999/nonexistent.json", current_version="1.0.0", timeout=0.5)
    assert res.status == "none"


def test_should_check_update():
    now = 1000000.0

    # auto_update False -> False
    assert not should_check_update({"auto_update": False, "last_app_check": 0}, now=now)

    # Checked 1 hour ago -> False
    assert not should_check_update({"auto_update": True, "last_app_check": now - 3600}, now=now)

    # Checked 25 hours ago -> True
    assert should_check_update({"auto_update": True, "last_app_check": now - 90000}, now=now)

    # Never checked -> True
    assert should_check_update({"auto_update": True, "last_app_check": 0}, now=now)


def test_update_download_worker_hash_match_and_mismatch(tmp_path, monkeypatch):
    content = b"fake-installer-executable-content"
    correct_hash = hashlib.sha256(content).hexdigest()
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    class MockResponse:
        def __init__(self, data):
            self.data = data
            self.headers = {"Content-Length": str(len(data))}
            self._offset = 0

        def read(self, chunk_size):
            if self._offset >= len(self.data):
                return b""
            chunk = self.data[self._offset : self._offset + chunk_size]
            self._offset += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=15.0: MockResponse(content))
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    # Test 1: Correct hash -> target kept
    info_ok = UpdateInfo(
        status="available",
        latest_version="9.9.9",
        installer_url="https://example.com/setup.exe",
        sha256=correct_hash,
    )
    worker_ok = UpdateDownloadWorker(info_ok)
    finished_files = []
    failed_msgs = []
    worker_ok.finished.connect(lambda p: finished_files.append(p))
    worker_ok.failed.connect(lambda m: failed_msgs.append(m))

    worker_ok.run()

    assert len(finished_files) == 1
    assert len(failed_msgs) == 0
    target_path = Path(finished_files[0])
    assert target_path.exists()
    assert target_path.read_bytes() == content

    # Test 2: Wrong hash -> target deleted
    info_bad = UpdateInfo(
        status="available",
        latest_version="9.9.9",
        installer_url="https://example.com/setup.exe",
        sha256=wrong_hash,
    )
    worker_bad = UpdateDownloadWorker(info_bad)
    finished_bad = []
    failed_bad = []
    worker_bad.finished.connect(lambda p: finished_bad.append(p))
    worker_bad.failed.connect(lambda m: failed_bad.append(m))

    worker_bad.run()

    assert len(finished_bad) == 0
    assert len(failed_bad) == 1
    assert "could not be verified" in failed_bad[0]
    assert not (tmp_path / f"YOuTUbE_Setup_9.9.9.exe.part").exists()


def test_launch_silent_installer(tmp_path, monkeypatch):
    import app.core.app_updater as updater_mod

    exe_file = tmp_path / "YOuTUbE_Setup_1.2.0.exe"
    exe_file.write_text("stub")

    mock_start_hidden = MagicMock()
    monkeypatch.setattr(updater_mod, "start_hidden", mock_start_hidden)

    ok = launch_silent_installer(exe_file)
    assert ok is True
    mock_start_hidden.assert_called_once()
    called_cmd = mock_start_hidden.call_args[0][0]
    assert str(exe_file) in called_cmd[0]
    assert "/SILENT" in called_cmd
    assert "/CLOSEAPPLICATIONS" in called_cmd
    assert "/RESTARTAPPLICATIONS" in called_cmd


def test_main_window_banner_available():
    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    try:
        assert not win.update_banner.isVisible()

        info = UpdateInfo(
            status="available",
            latest_version="1.2.0",
            installer_url="https://example.com/setup.exe",
            sha256="abc",
        )
        win.apply_update_info(info)
        assert win.update_banner.isVisible()
        assert "Version 1.2.0 is available" in win.update_banner.msg_label.text()
        assert win.update_banner.later_btn.isVisible()

        # Click later
        win.update_banner.later_btn.click()
        assert not win.update_banner.isVisible()
    finally:
        win.network_monitor.stop()
        win.network_monitor.wait(500)
        win.close()


def test_main_window_banner_required_locking():
    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    try:
        info = UpdateInfo(
            status="required",
            latest_version="2.0.0",
            min_supported_version="1.5.0",
            installer_url="https://example.com/setup.exe",
            sha256="abc",
        )
        win.apply_update_info(info)
        assert win.update_banner.isVisible()
        assert "required" in win.update_banner.msg_label.text().lower()
        assert not win.update_banner.later_btn.isVisible()

        # Main controls are locked
        assert not win.video_tab.url_input.isEnabled()
        assert not win.video_tab.download_btn.isEnabled()
        assert not win.audio_tab.url_input.isEnabled()
        assert not win.audio_tab.download_btn.isEnabled()

        # History tab stays fully usable
        assert win.history_tab.isEnabled()
    finally:
        win.network_monitor.stop()
        win.network_monitor.wait(500)
        win.close()

