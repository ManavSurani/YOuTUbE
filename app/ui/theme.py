"""Theme and stylesheet builder for dark and light modes."""

from typing import Dict

DARK_TOKENS: Dict[str, str] = {
    "bg": "#0F0F0F",
    "surface": "#212121",
    "surface_hover": "#272727",
    "border": "#303030",
    "text": "#F1F1F1",
    "text_muted": "#AAAAAA",
    "accent": "#FF0000",
    "accent_hover": "#CC0000",
    "info": "#3EA6FF",
    "success": "#2BA640",
    "error": "#FF4E45",
}

LIGHT_TOKENS: Dict[str, str] = {
    "bg": "#FFFFFF",
    "surface": "#F2F2F2",
    "surface_hover": "#E5E5E5",
    "border": "#E0E0E0",
    "text": "#0F0F0F",
    "text_muted": "#606060",
    "accent": "#FF0000",
    "accent_hover": "#CC0000",
    "info": "#065FD4",
    "success": "#2BA640",
    "error": "#CC0000",
}


def build_qss(theme_name: str = "dark") -> str:
    """Build Qt stylesheet strictly from theme tokens.
    
    No gradients, shadows, or border-image keywords are permitted.
    """
    c = DARK_TOKENS if theme_name.lower() == "dark" else LIGHT_TOKENS
    button_accent_text = c["text"] if theme_name.lower() == "dark" else c["bg"]

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
    width: 16px;
    height: 16px;
    border: 1px solid {c["border"]};
    border-radius: 4px;
    background-color: {c["surface"]};
}}

QCheckBox::indicator:checked {{
    background-color: {c["text"]};
    border: 1px solid {c["text"]};
}}
"""
