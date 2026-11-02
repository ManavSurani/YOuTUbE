"""Plan 23 Phase 6: motion tokens and delightful, honest motion."""

import re
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtWidgets import QApplication

from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob
from app.ui.kit import anim

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def motion(monkeypatch):
    """Animations on (default), with a switch to turn them off like 'Reduce motion'."""
    state = {"on": True}
    for mod in ("app.ui.kit.anim", "app.ui.kit.progress_card", "app.ui.video_tab", "app.ui.audio_tab", "app.ui.main_window"):
        monkeypatch.setattr(f"{mod}.is_animations_enabled", lambda: state["on"], raising=False)
    return state


def _settle(ms: int = 30) -> None:
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def _job() -> DownloadJob:
    info = VideoInfo(url=URL, title="T", channel="C", duration=1, duration_str="0:01", thumbnail_url="",
                     qualities=[("1080p", 1080)], filesize_approx=0)
    return DownloadJob.create(info=info, kind="video", quality_label="1080p")


# 6.1 Motion tokens -----------------------------------------------------------------

def test_motion_tokens():
    assert (anim.FAST, anim.BASE, anim.SLOW, anim.CELEBRATE) == (120, 180, 260, 300)


def test_no_raw_durations_in_ui():
    offenders = []
    for path in (ROOT / "app" / "ui").rglob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"setDuration\(\s*\d+\s*\)", line):
                offenders.append(f"{path.name}:{n}")
    assert offenders == []


def test_create_animation_default_is_base(motion):
    from PySide6.QtWidgets import QWidget
    target = QWidget()
    a = anim.create_animation(target, b"windowOpacity", 0.0, 1.0)
    assert a.duration() == anim.BASE


# 6.4 Smooth progress -----------------------------------------------------------------

def test_progress_value_exact_but_drawn_smoothly(motion):
    from app.ui.kit.progress_card import ModernProgressBar
    bar = ModernProgressBar()
    bar.setRange(0, 100)
    bar.setValue(50)
    assert bar.value() == 50  # logic sees the real value at once
    assert bar._value_anim is not None and bar._value_anim.state() == QAbstractAnimation.State.Running
    _settle(anim.BASE + 120)
    assert abs(bar.shown_value - 50) < 0.5


def test_progress_reduce_motion_is_instant(motion):
    from app.ui.kit.progress_card import ModernProgressBar
    motion["on"] = False
    bar = ModernProgressBar()
    bar.setRange(0, 100)
    bar.setValue(70)
    assert bar.shown_value == 70


def test_shimmer_stops_while_stalled(motion):
    from app.ui.kit import ProgressCard
    card = ProgressCard()
    card.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    card.show()
    card.bind_job(_job())
    card.set_progress(20.0, speed="5.0 MB/s", eta="00:30", done_bytes=10, total_bytes=50)
    assert card.highlight_anim.state() == QAbstractAnimation.State.Running
    card.set_progress(20.0, speed="", eta="", done_bytes=10, total_bytes=50)  # stall: no bytes moving
    assert card.highlight_anim.state() != QAbstractAnimation.State.Running
    card.set_progress(21.0, speed="4.0 MB/s", eta="00:29", done_bytes=11, total_bytes=50)
    assert card.highlight_anim.state() == QAbstractAnimation.State.Running


# 6.5 Done pulse ---------------------------------------------------------------------------

def test_done_pulse(motion):
    from app.ui.kit import ProgressCard
    card = ProgressCard()
    card.bind_job(_job())
    card.show_done(out_dir="C:/Downloads")
    assert card.progress_bar._pulse_anim is not None
    assert card.progress_bar._pulse_anim.duration() == anim.CELEBRATE


def test_done_pulse_off_with_reduce_motion(motion):
    from app.ui.kit import ProgressCard
    motion["on"] = False
    card = ProgressCard()
    card.bind_job(_job())
    card.show_done(out_dir="C:/Downloads")
    assert card.progress_bar._pulse_anim is None


# 6.7 Error shake ---------------------------------------------------------------------------------

def test_invalid_link_shakes_input(motion, monkeypatch):
    from app.ui.video_tab import VideoTab
    monkeypatch.setattr("app.ui.video_tab.find_duplicate", lambda *a, **kw: None)
    tab = VideoTab()
    tab.url_input.blockSignals(True)
    tab.url_input.setText("nope")
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert tab._shake_anim is not None and tab._shake_anim.duration() == anim.BASE


def test_no_shake_with_reduce_motion(motion, monkeypatch):
    from app.ui.video_tab import VideoTab
    monkeypatch.setattr("app.ui.video_tab.find_duplicate", lambda *a, **kw: None)
    motion["on"] = False
    tab = VideoTab()
    tab.url_input.blockSignals(True)
    tab.url_input.setText("nope")
    tab.url_input.blockSignals(False)
    tab.fetch_url()
    assert tab._shake_anim is None


# 6.8 Tab cross-fade ---------------------------------------------------------------------------------

def test_tab_switch_fades_in(motion, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    from app.ui.main_window import MainWindow
    monkeypatch.setattr(QSystemTrayIcon, "show", lambda self: None)
    win = MainWindow()
    try:
        win.header.select_tab(1)
        assert win._page_fade is not None and win._page_fade.duration() == anim.FAST
        _settle(anim.FAST + 120)
        assert win.audio_tab.graphicsEffect() is None  # effect removed after the fade
    finally:
        win.network_monitor.stop()
        win.close()
