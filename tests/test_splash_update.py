"""Plan 22 Phase 4: app update check on the startup screen."""

import sys

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

import app.ui.splash as splash_mod
from app.core.app_updater import UpdateInfo
from app.ui.splash import SplashScreen, StartupWorker


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def env(monkeypatch):
    """Online, installed (frozen) app, no missing tools, settings in memory."""
    state = {
        "settings": {"auto_update": True, "last_tool_check": 10**12},
        "checks": 0,
        "tools_checked": False,
        "info": UpdateInfo(status="none", latest_version="1.0.2"),
    }

    def fake_check(timeout=10.0):
        state["checks"] += 1
        return state["info"]

    def fake_missing():
        state["tools_checked"] = True
        return []

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(splash_mod, "APP_VERSION", "1.0.2")
    monkeypatch.setattr(splash_mod, "check_internet", lambda *a, **kw: True)
    monkeypatch.setattr(splash_mod, "check_for_update", fake_check)
    monkeypatch.setattr(splash_mod, "missing_tools", fake_missing)
    monkeypatch.setattr(splash_mod, "update_ytdlp", lambda: None)
    monkeypatch.setattr(splash_mod, "create_desktop_shortcut", lambda: None)
    monkeypatch.setattr(splash_mod, "load_settings", lambda: dict(state["settings"]))
    monkeypatch.setattr(splash_mod, "save_settings", lambda s: state["settings"].update(s))
    monkeypatch.setattr(splash_mod.time, "sleep", lambda s: None)
    return state


def _run_worker(**kw):
    worker = StartupWorker(**kw)
    events = {"found": None, "finished": False, "status": []}
    worker.update_found.connect(lambda info: events.__setitem__("found", info))
    worker.finished.connect(lambda: events.__setitem__("finished", True))
    worker.status.connect(events["status"].append)
    worker.run()
    return events


AVAILABLE = UpdateInfo(status="available", latest_version="1.0.3", installer_url="u", sha256="s")


# ---------------------------------------------------------------------------
# StartupWorker
# ---------------------------------------------------------------------------

def test_source_run_never_checks_app_update(env, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    ev = _run_worker()
    assert env["checks"] == 0
    assert ev["finished"] and env["tools_checked"]


def test_auto_update_off_skips(env):
    env["settings"]["auto_update"] = False
    ev = _run_worker()
    assert env["checks"] == 0 and ev["finished"]


def test_offline_skips_update_check(env, monkeypatch):
    monkeypatch.setattr(splash_mod, "check_internet", lambda *a, **kw: False)
    ev = _run_worker()
    assert env["checks"] == 0 and ev["finished"]


def test_skip_flag_skips_update_check(env):
    ev = _run_worker(skip_app_update=True)
    assert env["checks"] == 0 and ev["finished"]


def test_no_update_continues_to_tools(env):
    ev = _run_worker()
    assert env["checks"] == 1
    assert "Checking for app update…" in ev["status"]
    assert ev["finished"] and env["tools_checked"]
    assert ev["found"] is None
    assert env["settings"].get("last_app_check", 0) > 0


def test_update_found_stops_before_tools(env):
    env["info"] = AVAILABLE
    ev = _run_worker()
    assert ev["found"] is AVAILABLE
    assert not ev["finished"]
    assert not env["tools_checked"]


def test_required_update_also_installs(env):
    env["info"] = UpdateInfo(status="required", latest_version="1.0.3", installer_url="u", sha256="s")
    ev = _run_worker()
    assert ev["found"] is env["info"]


def test_loop_guard_skips_same_version(env):
    env["info"] = AVAILABLE
    env["settings"]["update_attempt_version"] = "1.0.3"
    ev = _run_worker()
    assert ev["found"] is None
    assert ev["finished"] and env["tools_checked"]


def test_loop_guard_allows_newer_version(env):
    env["info"] = UpdateInfo(status="available", latest_version="1.0.4", installer_url="u", sha256="s")
    env["settings"]["update_attempt_version"] = "1.0.3"
    ev = _run_worker()
    assert ev["found"] is env["info"]


# ---------------------------------------------------------------------------
# SplashScreen
# ---------------------------------------------------------------------------

class FakeStartupWorker(QObject):
    status = Signal(str)
    progress = Signal(int)
    offline_blocked = Signal()
    finished = Signal()
    update_found = Signal(object)
    created = []

    def __init__(self, parent=None, skip_app_update=False):
        super().__init__(parent)
        self.skip_app_update = skip_app_update
        FakeStartupWorker.created.append(self)

    def start(self):
        pass


class FakeDownloadWorker(QObject):
    progress = Signal(float)
    stage = Signal(str)
    finished = Signal(str)
    failed = Signal(str)
    last = None

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.started = False
        FakeDownloadWorker.last = self

    def start(self):
        self.started = True


@pytest.fixture
def splash(env, monkeypatch):
    FakeStartupWorker.created = []
    calls = {"launch": [], "quit": 0, "launch_ok": True}
    monkeypatch.setattr(splash_mod, "StartupWorker", FakeStartupWorker)
    monkeypatch.setattr(splash_mod, "UpdateDownloadWorker", FakeDownloadWorker)

    def fake_launch(path):
        calls["launch"].append(path)
        return calls["launch_ok"]

    monkeypatch.setattr(splash_mod, "launch_silent_installer", fake_launch)
    monkeypatch.setattr(splash_mod.QApplication, "quit", staticmethod(lambda: calls.__setitem__("quit", calls["quit"] + 1)))
    s = SplashScreen()
    return s, calls


def test_update_found_starts_download(splash):
    s, _ = splash
    FakeStartupWorker.created[-1].update_found.emit(AVAILABLE)
    assert FakeDownloadWorker.last.started
    assert s.status_label.text() == "Downloading update 1.0.3…"


def test_download_progress_shown_on_splash(splash):
    s, _ = splash
    FakeStartupWorker.created[-1].update_found.emit(AVAILABLE)
    FakeDownloadWorker.last.progress.emit(45.0)
    assert s.progress_bar.value() == 45
    assert s.status_label.text() == "Downloading update 1.0.3… 45%"


def test_download_success_launches_and_quits(splash, env):
    s, calls = splash
    FakeStartupWorker.created[-1].update_found.emit(AVAILABLE)
    FakeDownloadWorker.last.finished.emit("C:/tmp/setup.exe")
    assert calls["launch"] == ["C:/tmp/setup.exe"]
    assert calls["quit"] == 1
    assert env["settings"]["update_attempt_version"] == "1.0.3"
    assert s.status_label.text() == "Installing update…"


def test_download_failure_starts_normally(splash):
    s, calls = splash
    FakeStartupWorker.created[-1].update_found.emit(AVAILABLE)
    FakeDownloadWorker.last.failed.emit("Download failed.")
    assert FakeStartupWorker.created[-1].skip_app_update is True
    assert calls["quit"] == 0


def test_launch_failure_starts_normally(splash):
    s, calls = splash
    calls["launch_ok"] = False
    FakeStartupWorker.created[-1].update_found.emit(AVAILABLE)
    FakeDownloadWorker.last.finished.emit("C:/tmp/setup.exe")
    assert calls["quit"] == 0
    assert FakeStartupWorker.created[-1].skip_app_update is True


def test_retry_button_unchanged(splash):
    s, _ = splash
    FakeStartupWorker.created[-1].offline_blocked.emit()
    assert s.retry_btn.isVisibleTo(s)
    s.retry_btn.click()
    assert FakeStartupWorker.created[-1].skip_app_update is False
