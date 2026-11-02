from pathlib import Path
import sys
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

DARK_TOKENS: Dict[str, str] = {
    "bg": "#0F0F0F",
    "surface": "#212121",
    "surface_hover": "#272727",
    "surface_pressed": "#1F1F1F",
    "border": "#303030",
    "text": "#F1F1F1",
    "text_muted": "#AAAAAA",
    "accent": "#FF0000",
    "accent_hover": "#CC0000",
    "accent_pressed": "#B30000",
    "info": "#3EA6FF",
    "success": "#2BA640",
    "error": "#FF4E45",
    # Aliases of colors already in use (same value in both themes)
    "focus": "#3EA6FF",
    "status_offline": "#CC0000",
}

LIGHT_TOKENS: Dict[str, str] = {
    "bg": "#FFFFFF",
    "surface": "#F2F2F2",
    "surface_hover": "#E5E5E5",
    "surface_pressed": "#DADADA",
    "border": "#E0E0E0",
    "text": "#0F0F0F",
    "text_muted": "#606060",
    "accent": "#FF0000",
    "accent_hover": "#CC0000",
    "accent_pressed": "#B30000",
    "info": "#065FD4",
    "success": "#2BA640",
    "error": "#CC0000",
    # Aliases of colors already in use (same value in both themes)
    "focus": "#3EA6FF",
    "status_offline": "#CC0000",
}

_current_theme = "dark"


def current_theme() -> str:
    """Name of the theme applied through ThemeManager ('dark' or 'light')."""
    return _current_theme


def tok(name: str) -> str:
    """Hex value of a token in the current theme."""
    return (DARK_TOKENS if _current_theme == "dark" else LIGHT_TOKENS)[name]


def qcolor(name: str) -> QColor:
    return QColor(tok(name))


class ThemeManager(QObject):
    """Applies a theme app-wide and tells painted widgets to repaint."""

    changed = Signal(str)
    _instance: Optional["ThemeManager"] = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def apply(self, theme_name: str) -> None:
        global _current_theme
        _current_theme = "light" if theme_name.lower() == "light" else "dark"
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(_current_theme))
        self.changed.emit(_current_theme)


def _get_arrow_path(theme_name: str) -> str:
    filename = "arrow_down_dark.png" if theme_name.lower() == "dark" else "arrow_down_light.png"
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = Path(__file__).resolve().parents[2] / "assets"
    return (base / filename).resolve().as_posix()


def build_qss(theme_name: str = "dark") -> str:
    """Build Qt stylesheet strictly from theme tokens.
    
    No gradients, shadows, or border-image keywords are permitted.
    """
    c = DARK_TOKENS if theme_name.lower() == "dark" else LIGHT_TOKENS
    button_accent_text = c["text"] if theme_name.lower() == "dark" else c["bg"]
    arrow_path = _get_arrow_path(theme_name)

    return f"""
* {{
    font-family: 'Segoe UI';
    font-size: 13px;
    color: {c["text"]};
}}

QMainWindow, QDialog, QMessageBox {{
    background-color: {c["bg"]};
    color: {c["text"]};
}}

QWidget#centralWidget {{
    background-color: {c["bg"]};
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
}}

QTabBar::tab {{
    background: transparent;
    color: {c["text_muted"]};
    padding: 8px 16px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {c["text"]};
    border-bottom: 2px solid {c["accent"]};
}}

QTabBar::tab:hover:!selected {{
    color: {c["text"]};
}}

QLineEdit {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    padding: 4px 12px;
    min-height: 26px;
}}

QLineEdit:focus {{
    border: 1px solid {c["text_muted"]};
}}

QComboBox {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    padding: 4px 12px;
    min-height: 26px;
}}

QComboBox:focus {{
    border: 1px solid {c["text_muted"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: url({arrow_path});
}}

QComboBox QAbstractItemView {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    selection-background-color: {c["surface_hover"]};
    selection-color: {c["text"]};
}}

QPushButton {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    padding: 6px 16px;
    min-height: 22px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {c["surface_hover"]};
}}

QPushButton[role="primary"] {{
    background-color: {c["accent"]};
    color: {button_accent_text};
    border: none;
}}

QPushButton[role="primary"]:hover {{
    background-color: {c["accent_hover"]};
}}

QPushButton[role="primary"]:disabled {{
    background-color: {c["surface"]};
    color: {c["text_muted"]};
}}

QPushButton[role="secondary"] {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
}}

QPushButton[role="secondary"]:hover {{
    background-color: {c["surface_hover"]};
}}

QPushButton:disabled {{
    color: {c["text_muted"]};
    border-color: {c["border"]};
}}

QProgressBar {{
    background-color: {c["surface"]};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    min-height: 6px;
    text-align: right;
}}

QProgressBar::chunk {{
    background-color: {c["accent"]};
    border-radius: 3px;
}}

QListWidget, QListView {{
    background-color: {c["bg"]};
    border: none;
    outline: none;
}}

QListWidget::item, QListView::item {{
    background-color: {c["surface"]};
    border-radius: 8px;
    margin-bottom: 8px;
    color: {c["text"]};
}}

QListWidget::item:hover, QListView::item:hover {{
    background-color: {c["surface_hover"]};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {c["border"]};
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c["text_muted"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {c["border"]};
    min-width: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {c["text_muted"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0px;
}}

QMessageBox {{
    background-color: {c["bg"]};
}}

QMessageBox QLabel {{
    color: {c["text"]};
    background-color: transparent;
}}

QLabel {{
    color: {c["text"]};
    background-color: transparent;
}}

QLabel[role="muted"] {{
    color: {c["text_muted"]};
}}

QLabel[role="title"] {{
    color: {c["text"]};
    font-size: 18px;
    font-weight: 600;
}}

QLabel[role="section"] {{
    color: {c["text"]};
    font-size: 15px;
    font-weight: 600;
}}

QLabel[role="strong"] {{
    color: {c["text"]};
    font-size: 13px;
    font-weight: 600;
}}

QLabel[role="meta"] {{
    color: {c["text_muted"]};
    font-size: 12px;
}}

QLabel[role="link"] {{
    color: {c["info"]};
}}

QLabel[role="info"] {{
    color: {c["info"]};
}}

QLabel[role="success"] {{
    color: {c["success"]};
}}

QLabel[role="error"] {{
    color: {c["error"]};
}}

QCheckBox {{
    color: {c["text"]};
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {c["border"]};
    border-radius: 4px;
    background-color: {c["surface"]};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {c["text_muted"]};
}}

QCheckBox::indicator:checked {{
    background-color: {c["accent"]};
    border: 1px solid {c["accent"]};
}}
"""
