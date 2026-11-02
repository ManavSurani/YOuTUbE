"""Plan 23 Phase 1: theme token API and theme-aware kit widgets."""

import ast
import re
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

import app.ui.theme as theme
from app.ui.theme import DARK_TOKENS, LIGHT_TOKENS

ROOT = Path(__file__).resolve().parent.parent
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")

# Palette as it was before Plan 23 (R1: values must never change)
ORIGINAL_DARK = {
    "bg": "#0F0F0F", "surface": "#212121", "surface_hover": "#272727", "surface_pressed": "#1F1F1F",
    "border": "#303030", "text": "#F1F1F1", "text_muted": "#AAAAAA", "accent": "#FF0000",
    "accent_hover": "#CC0000", "accent_pressed": "#B30000", "info": "#3EA6FF", "success": "#2BA640",
    "error": "#FF4E45",
}
ORIGINAL_LIGHT = {
    "bg": "#FFFFFF", "surface": "#F2F2F2", "surface_hover": "#E5E5E5", "surface_pressed": "#DADADA",
    "border": "#E0E0E0", "text": "#0F0F0F", "text_muted": "#606060", "accent": "#FF0000",
    "accent_hover": "#CC0000", "accent_pressed": "#B30000", "info": "#065FD4", "success": "#2BA640",
    "error": "#CC0000",
}


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def back_to_dark():
    yield
    theme.ThemeManager.instance().apply("dark")


def test_token_values_unchanged():
    for key, value in ORIGINAL_DARK.items():
        assert DARK_TOKENS[key] == value
    for key, value in ORIGINAL_LIGHT.items():
        assert LIGHT_TOKENS[key] == value


def test_alias_tokens_reuse_existing_colors():
    for tokens in (DARK_TOKENS, LIGHT_TOKENS):
        assert tokens["focus"] == "#3EA6FF"
        assert tokens["status_offline"] == "#CC0000"


def test_tok_follows_theme():
    tm = theme.ThemeManager.instance()
    tm.apply("light")
    assert theme.current_theme() == "light"
    assert theme.tok("text") == "#0F0F0F"
    tm.apply("dark")
    assert theme.tok("text") == "#F1F1F1"
    assert theme.qcolor("accent") == QColor("#FF0000")


def test_apply_emits_changed_and_sets_stylesheet(qapp):
    seen = []
    tm = theme.ThemeManager.instance()
    tm.changed.connect(seen.append)
    tm.apply("light")
    assert seen[-1] == "light"
    assert LIGHT_TOKENS["bg"] in qapp.styleSheet()


def test_qss_has_type_roles():
    qss = theme.build_qss("dark")
    for role, size in (("title", 18), ("section", 15), ("strong", 13), ("meta", 12)):
        assert f'QLabel[role="{role}"]' in qss
        block = qss.split(f'QLabel[role="{role}"]', 1)[1].split("}", 1)[0]
        assert f"font-size: {size}px" in block


def test_kit_has_no_hex_literals():
    offenders = []
    for path in sorted((ROOT / "app" / "ui" / "kit").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and HEX.search(node.value):
                offenders.append(f"{path.name}:{node.lineno} {node.value[:40]!r}")
    assert offenders == []


def _render(widget) -> QImage:
    widget.resize(widget.sizeHint().expandedTo(widget.minimumSizeHint()))
    widget.ensurePolished()
    return widget.grab().toImage()


def test_secondary_button_light_surface():
    from app.ui.kit import AnimatedButton
    theme.ThemeManager.instance().apply("light")
    btn = AnimatedButton("Fetch", role="secondary")
    btn.resize(120, 36)
    img = btn.grab().toImage()
    assert img.pixelColor(10, 18).name().upper() == LIGHT_TOKENS["surface"]


def test_theme_change_repaints_buttons():
    from app.ui.kit import AnimatedButton
    tm = theme.ThemeManager.instance()
    tm.apply("dark")
    btn = AnimatedButton("Fetch", role="secondary")
    btn.resize(120, 36)
    dark_px = btn.grab().toImage().pixelColor(10, 18).name()
    tm.apply("light")
    light_px = btn.grab().toImage().pixelColor(10, 18).name()
    assert dark_px != light_px
    assert light_px.upper() == LIGHT_TOKENS["surface"]


def test_progress_track_follows_theme():
    from app.ui.kit.progress_card import ModernProgressBar
    tm = theme.ThemeManager.instance()
    tm.apply("light")
    bar = ModernProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.resize(200, 6)
    px = bar.grab().toImage().pixelColor(100, 3).name().upper()
    assert px == LIGHT_TOKENS["surface_hover"]


def test_thumb_placeholder_follows_theme():
    from app.ui.kit import ThumbLabel
    theme.ThemeManager.instance().apply("light")
    thumb = ThumbLabel(video_id="no_such_video_id_x", size=(64, 36))
    img = thumb.pixmap().toImage()
    assert img.pixelColor(4, 18).name().upper() == LIGHT_TOKENS["surface"]
