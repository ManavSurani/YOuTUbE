"""Plan 24: theme polish (button sizes, menus, tooltips, window chrome, tab fade)."""

import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import app.ui.theme as theme
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def back_to_dark():
    yield
    theme.ThemeManager.instance().apply("dark")


def _settle(ms: int = 40) -> None:
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def _show(widget, w=None, h=None):
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    if w and h:
        widget.resize(w, h)
    widget.show()
    _settle()
    return widget


def _job() -> DownloadJob:
    info = VideoInfo(url=URL, title="A long title " * 8, channel="C", duration=1, duration_str="0:01",
                     thumbnail_url="", qualities=[], filesize_approx=0)
    return DownloadJob.create(info=info, kind="video", quality_label="1080p")


# Phase 1: buttons at their real size ------------------------------------------------

@pytest.mark.parametrize("theme_name", ["dark", "light"])
@pytest.mark.parametrize("size", [28, 32])
def test_icon_button_keeps_requested_size(theme_name, size):
    from app.ui.kit import IconButton
    theme.ThemeManager.instance().apply(theme_name)
    btn = _show(IconButton("pause", size=size))
    assert (btn.width(), btn.height()) == (size, size)


def test_text_kit_button_has_breathing_room():
    from app.ui.kit import AnimatedButton
    btn = _show(AnimatedButton("Retry all", role="ghost"))
    text_w = btn.fontMetrics().horizontalAdvance("Retry all")
    assert btn.height() == 36
    assert btn.width() >= text_w + 24


def test_pause_button_inside_progress_header():
    from app.ui.kit import ProgressCard
    card = _show(ProgressCard(), 900, 120)
    card.bind_job(_job())
    _settle()
    g, row = card.pause_btn.geometry(), card.header_widget.rect()
    assert row.contains(g), f"pause button {g.getRect()} outside header {row.getRect()}"


def test_paused_shows_paused_not_old_speed():
    from app.ui.kit import ProgressCard
    card = ProgressCard()
    card.bind_job(_job())
    card.set_progress(46.0, "8.4 MB/s", "01:12", 317_000_000, 723_600_000)
    card.set_paused(True)
    text = card.stats_label.text()
    assert text == "302.3 MB / 690.1 MB" and "MB/s" not in text and "ETA" not in text
    card.set_paused(False)
    card.set_progress(47.0, "8.0 MB/s", "01:10", 320_000_000, 723_600_000)
    assert card.stats_label.text().startswith("8.0 MB/s")


def test_done_hides_empty_stats_line():
    from app.ui.kit import ProgressCard
    card = _show(ProgressCard(), 900, 120)
    card.bind_job(_job())
    card.show_done(out_dir="C:/Downloads")
    assert not card.stats_label.isVisibleTo(card)
    card.bind_job(_job())
    assert card.stats_label.isVisibleTo(card)


# Phase 2: menus and tooltips follow the theme -------------------------------------

def _menu_bg(theme_name=None):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu
    if theme_name:
        theme.ThemeManager.instance().apply(theme_name)
    menu = QMenu()
    for text in ("Copy link", "Re-download", "Delete"):
        menu.addAction(text)
    menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    menu.popup(QPoint(0, 0))
    _settle(80)
    img = menu.grab().toImage()
    menu.close()
    return img.pixelColor(img.width() // 2, 3)


def _close(a, b, tol=12):
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= tol


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_menu_background_is_theme_surface(theme_name):
    from PySide6.QtGui import QColor
    bg = _menu_bg(theme_name)
    assert _close(bg, QColor(theme.tok("surface"))), f"{theme_name}: menu bg {bg.name()} vs surface {theme.tok('surface')}"


def test_menu_follows_live_switch():
    from PySide6.QtGui import QColor
    _menu_bg("dark")
    theme.ThemeManager.instance().apply("light")
    assert _close(_menu_bg(), QColor(theme.LIGHT_TOKENS["surface"]))


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_qss_has_menu_and_tooltip_rules_from_tokens(theme_name):
    qss = theme.build_qss(theme_name)
    tokens = theme.DARK_TOKENS if theme_name == "dark" else theme.LIGHT_TOKENS
    menu = qss.split("QMenu {", 1)[1].split("}", 1)[0]
    assert tokens["surface"] in menu and tokens["text"] in menu and tokens["border"] in menu
    selected = qss.split("QMenu::item:selected {", 1)[1].split("}", 1)[0]
    assert tokens["surface_hover"] in selected
    tip = qss.split("QToolTip {", 1)[1].split("}", 1)[0]
    assert tokens["surface"] in tip and tokens["text"] in tip
