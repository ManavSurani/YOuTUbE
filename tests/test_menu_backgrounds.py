"""Plan 25: every menu is painted with the theme surface, built from its real parent in the real window."""

import re
import time

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QContextMenuEvent
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

import app.ui.theme as theme

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(scope="module")
def win():
    from app.core.history_db import HistoryItem
    from app.ui import history_tab
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    items = [HistoryItem(id=i, title=f"Video {i}", url=URL, type="video", quality="1080p", file_path="",
                         size_bytes=5000, duration=60, created_at="2026-11-01 10:00:00") for i in range(3)]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(history_tab, "list_items", lambda *a, **kw: list(items))
        mp.setattr(QSystemTrayIcon, "show", lambda self: None)
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.resize(1000, 800)
        window.show()
        window.header.select_tab(2)
        _settle()
        yield window
        window.network_monitor.stop()
        window.close()
    theme.ThemeManager.instance().apply("dark")
    app.processEvents()


def _settle(ms: int = 60) -> None:
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def _bg(menu) -> QColor:
    menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    menu.popup(QPoint(0, 0))
    _settle(80)
    img = menu.grab().toImage()
    menu.close()
    return img.pixelColor(img.width() // 2, 3)


def _assert_surface(bg: QColor, what: str) -> None:
    want = QColor(theme.tok("surface"))
    diff = max(abs(bg.red() - want.red()), abs(bg.green() - want.green()), abs(bg.blue() - want.blue()))
    assert bg.alpha() == 255 and diff <= 12, f"{what}: background {bg.name(QColor.NameFormat.HexArgb)} vs surface {want.name()}"


def _row(win):
    rows = list(win.history_tab._rendered_rows.values())
    assert rows, "no History rows rendered"
    return rows[0]


def _right_click_menu(row):
    caught = []
    build = row.build_more_menu

    def build_caught():
        menu = build()
        menu.exec = lambda *a, **kw: caught.append(menu)
        return menu

    row.build_more_menu = build_caught
    try:
        row.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5), QPoint(0, 0)))
    finally:
        del row.build_more_menu
    return caught[0]


def _line_edit_menu(line_edit):
    line_edit.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Keyboard, QPoint(5, 5), QPoint(0, 0)))
    return line_edit._current_menu


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_history_row_menu_is_surface(win, theme_name):
    theme.ThemeManager.instance().apply(theme_name)
    _assert_surface(_bg(_row(win).build_more_menu()), f"{theme_name} row menu")


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_history_row_right_click_menu_is_surface(win, theme_name):
    theme.ThemeManager.instance().apply(theme_name)
    _assert_surface(_bg(_right_click_menu(_row(win))), f"{theme_name} row right-click menu")


def test_row_menu_after_live_switch(win):
    theme.ThemeManager.instance().apply("dark")
    _settle()
    theme.ThemeManager.instance().apply("light")
    _assert_surface(_bg(_row(win).build_more_menu()), "row menu after dark -> light")


@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_every_other_menu_is_surface(win, theme_name):
    from app.ui.settings_dialog import SettingsDialog
    theme.ThemeManager.instance().apply(theme_name)
    _assert_surface(_bg(win.history_tab.build_more_menu()), "History more menu")
    _assert_surface(_bg(win.tray_icon.contextMenu()), "tray menu")
    for name, line_edit in (("search box", win.history_tab.search_input),
                            ("video link box", win.video_tab.url_input),
                            ("audio link box", win.audio_tab.url_input)):
        menu = _line_edit_menu(line_edit)
        assert menu is not None, name
        img = menu.grab().toImage()
        menu.close()
        _assert_surface(img.pixelColor(img.width() // 2, img.height() // 2), name)
    dlg = SettingsDialog(win)
    try:
        _assert_surface(_bg(dlg.folder_input.createStandardContextMenu()), "Settings folder field")
    finally:
        dlg.close()


_SCOPED_BLOCK = re.compile(r"[^{}]*\{[^{}]*\}")


def _leaking_widgets(root: QWidget):
    """Widgets with child widgets whose own stylesheet has a rule outside any selector block.

    Such a rule applies to every child, including menus parented inside, and beats the app stylesheet."""
    found = []
    for w in [root, *root.findChildren(QWidget)]:
        sheet = w.styleSheet().strip()
        if not sheet or not w.findChildren(QWidget):
            continue
        if ":" in _SCOPED_BLOCK.sub("", sheet):
            found.append(f"{type(w).__name__}({w.objectName() or '-'}): {sheet!r}")
    return found


def test_no_container_stylesheet_leaks_into_children(win):
    from app.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(win)
    try:
        leaks = _leaking_widgets(win) + _leaking_widgets(dlg)
    finally:
        dlg.close()
    assert not leaks, "unscoped stylesheet rules on containers:\n" + "\n".join(leaks)
