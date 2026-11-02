"""Plan 23 Phase 2: every screen follows the theme; light mode is readable."""

import ast
import re
import time
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QLineEdit

import app.ui.theme as theme
from app.core.info_fetcher import VideoInfo
from app.ui.theme import LIGHT_TOKENS

ROOT = Path(__file__).resolve().parent.parent
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")

INFO = VideoInfo(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="A readable title", channel="Channel",
    duration=212, duration_str="3:32", thumbnail_url="", qualities=[("1080p", 1080)], filesize_approx=0,
)


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def light_then_dark(monkeypatch):
    monkeypatch.setattr("app.ui.video_tab.find_duplicate", lambda *a, **kw: None, raising=False)
    theme.ThemeManager.instance().apply("light")
    yield
    theme.ThemeManager.instance().apply("dark")


def _settle(ms: int = 50) -> None:
    # processEvents (not a nested event loop): a nested loop would also run deleteLater()
    # of widgets left by earlier tests, e.g. a MainWindow whose network thread is still running.
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def _show(widget):
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    widget.resize(880, 700)
    widget.show()
    _settle()
    return widget


def _luminance(c: QColor) -> float:
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def _contrast(a: QColor, b: QColor) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_ui_has_no_hex_literals():
    offenders = []
    for path in sorted((ROOT / "app" / "ui").rglob("*.py")):
        if path.name == "theme.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and HEX.search(node.value):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_font_sizes_on_scale():
    sizes = set()
    for path in (ROOT / "app" / "ui").rglob("*.py"):
        sizes.update(int(m) for m in re.findall(r"font-size:\s*(\d+)px", path.read_text(encoding="utf-8")))
    assert sizes <= {12, 13, 15, 18}, sizes


def _make_screen(name: str):
    from app.ui.header import Header
    from app.ui.history_tab import HistoryTab
    from app.ui.settings_dialog import SettingsDialog
    from app.ui.video_tab import VideoTab

    if name == "video_ready":
        vt = VideoTab()
        vt._on_info_fetched(INFO)
        return vt
    return {"header": Header, "history": HistoryTab, "settings": SettingsDialog}[name]()


@pytest.mark.parametrize("name", ["header", "video_ready", "history", "settings"])
def test_light_labels_readable(name):
    widget = _show(_make_screen(name))
    white = QColor(LIGHT_TOKENS["bg"])
    bad = []
    for lbl in widget.findChildren(QLabel):
        if not lbl.isVisibleTo(widget) or not lbl.text().strip():
            continue
        lbl.ensurePolished()
        fg = lbl.palette().color(lbl.foregroundRole())
        if _contrast(fg, white) < 3.0:
            bad.append(f"{lbl.text()[:30]!r} {fg.name()}")
    widget.close()
    assert bad == []


def test_light_no_dark_blocks():
    from app.ui.kit import AnimatedButton
    from app.ui.video_tab import VideoTab

    vt = _show(VideoTab())
    vt._on_info_fetched(INFO)
    _settle()
    limit = _luminance(QColor("#BBBBBB"))
    dark = []
    # Filled buttons: sample their own rendering just inside the left edge
    for btn in vt.findChildren(AnimatedButton):
        if btn.role in ("primary", "icon", "ghost"):
            continue
        px = btn.grab().toImage().pixelColor(6, btn.height() // 2)
        if _luminance(px) < limit:
            dark.append(f"{btn.text()} {px.name()}")
    # Inputs: render onto a page-colored image and sample inside the field
    for field in vt.findChildren(QLineEdit) + vt.findChildren(QComboBox):
        img = QImage(field.size(), QImage.Format.Format_ARGB32)
        img.fill(QColor(LIGHT_TOKENS["bg"]))
        field.render(img)
        px = img.pixelColor(8, field.height() // 2)
        if _luminance(px) < limit:
            dark.append(f"{type(field).__name__} {px.name()}")
    vt.close()
    assert dark == []


def test_theme_switch_live():
    from app.ui.header import Header

    header = _show(Header())
    tab = header._tabs[1]
    assert LIGHT_TOKENS["text_muted"] in tab.styleSheet()
    theme.ThemeManager.instance().apply("dark")
    assert theme.DARK_TOKENS["text_muted"] in tab.styleSheet()
    header.close()
