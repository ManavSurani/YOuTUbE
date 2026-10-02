"""Custom header widget with brand mark, sliding red tab underline, network badge, and settings button.

Fixes B10 by replacing the cramped QTabWidget corner widget with a full-height 52px header.
"""

from pathlib import Path
import sys
from typing import List, Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from app.ui.kit.anim import is_animations_enabled
from app.ui.kit.buttons import AnimatedButton


def get_asset_path(filename: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = Path(__file__).resolve().parents[2] / "assets"
    return base / filename


def create_gear_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Render a crisp vector gear icon using QPainter."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy = size / 2.0, size / 2.0
    r_outer = size * 0.42
    r_inner = size * 0.22

    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Center hole
    painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)

    # 6 teeth
    import math
    for i in range(6):
        angle = i * (2 * math.pi / 6)
        x1 = cx + math.cos(angle) * (r_inner + 1)
        y1 = cy + math.sin(angle) * (r_inner + 1)
        x2 = cx + math.cos(angle) * r_outer
        y2 = cy + math.sin(angle) * r_outer
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    painter.end()
    return QIcon(pix)


class AnimatedStatusDot(QWidget):
    """Network indicator dot with smooth 150 ms color transition."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._color = QColor("#2BA640")
        self._target_color = QColor("#2BA640")
        self._progress = 1.0
        self._anim: Optional[QPropertyAnimation] = None

    def _get_prog(self) -> float:
        return self._progress

    def _set_prog(self, val: float) -> None:
        self._progress = val
        self.update()

    progress = Property(float, _get_prog, _set_prog)

    def set_color(self, color_hex: str) -> None:
        self._color = QColor(color_hex)
        self._target_color = self._color
        self.update()

    def set_online(self, online: bool) -> None:
        new_color = QColor("#2BA640" if online else "#CC0000")
        self._color = new_color
        self._target_color = new_color

        if not is_animations_enabled():
            self.update()
            return

        if self._anim:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        p = self._progress
        if p < 1.0:
            r = int(self._start_color.red() * (1 - p) + self._target_color.red() * p)
            g = int(self._start_color.green() * (1 - p) + self._target_color.green() * p)
            b = int(self._start_color.blue() * (1 - p) + self._target_color.blue() * p)
            self._color = QColor(r, g, b)
        else:
            self._color = self._target_color

        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 8, 8)
        painter.end()


class Header(QWidget):
    """Application header containing brand logo, animated tab underline, and settings."""

    tab_changed = Signal(int)
    settings_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(52)
        self._current_tab = 0

        # Underline animation properties
        self._underline_x = 0.0
        self._underline_w = 0.0
        self._underline_anim: Optional[QPropertyAnimation] = None

        self._tabs: List[QPushButton] = []
        self._setup_ui()

    def _get_underline_x(self) -> float:
        return self._underline_x

    def _set_underline_x(self, val: float) -> None:
        self._underline_x = val
        self.update()

    underline_x = Property(float, _get_underline_x, _set_underline_x)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        # 1. Logo & App Title
        logo_label = QLabel(self)
        logo_path = get_asset_path("logo_512.png")
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
        layout.addWidget(logo_label)

        title_label = QLabel("YOuTUbE", self)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title_label)

        layout.addSpacing(16)

        # 2. Tabs (Video, Audio, History)
        tab_names = ["Video", "Audio", "History"]
        for idx, name in enumerate(tab_names):
            btn = QPushButton(name, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; font-size: 13px; font-weight: 600; padding: 0 12px; color: #AAAAAA; } "
                "QPushButton:hover { color: #FFFFFF; }"
            )
            btn.clicked.connect(lambda _, i=idx: self.select_tab(i))
            self._tabs.append(btn)
            layout.addWidget(btn)

        layout.addStretch(1)

        # 3. Status Badge (Online/Offline)
        self.status_dot = AnimatedStatusDot(self)
        self.status_label = QLabel("Online", self)
        self.status_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #2BA640;")

        status_container = QWidget(self)
        s_layout = QHBoxLayout(status_container)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(6)
        s_layout.addWidget(self.status_dot)
        s_layout.addWidget(self.status_label)
        layout.addWidget(status_container)

        layout.addSpacing(8)

        # 4. Settings Button (Role secondary, 36px, gear icon)
        gear_icon = create_gear_icon(16, "#FFFFFF")
        self.settings_btn = AnimatedButton("Settings", role="secondary", icon=gear_icon, parent=self)
        self.settings_btn.setFixedWidth(100)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

    def select_tab(self, index: int) -> None:
        """Switch to tab index and animate red underline."""
        if index < 0 or index >= len(self._tabs):
            return

        self._current_tab = index
        for i, btn in enumerate(self._tabs):
            if i == index:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; font-size: 13px; font-weight: 700; padding: 0 12px; color: #FFFFFF; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; font-size: 13px; font-weight: 600; padding: 0 12px; color: #AAAAAA; } "
                    "QPushButton:hover { color: #FFFFFF; }"
                )

        target_btn = self._tabs[index]
        target_x = float(target_btn.pos().x())
        target_w = float(target_btn.width())

        self._underline_w = target_w

        if not is_animations_enabled() or self._underline_x == 0.0:
            self._underline_x = target_x
            self.update()
        else:
            if self._underline_anim:
                self._underline_anim.stop()
            self._underline_anim = QPropertyAnimation(self, b"underline_x", self)
            self._underline_anim.setDuration(150)
            self._underline_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._underline_anim.setStartValue(self._underline_x)
            self._underline_anim.setEndValue(target_x)
            self._underline_anim.start()

        self.tab_changed.emit(index)

    def set_online(self, online: bool) -> None:
        """Update network badge text and dot color."""
        self.status_dot.set_online(online)
        self.status_label.setText("Online" if online else "Offline")
        self.status_label.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {'#2BA640' if online else '#CC0000'};"
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Position underline on initial show
        if self._tabs and self._underline_x == 0.0:
            target_btn = self._tabs[self._current_tab]
            self._underline_x = float(target_btn.pos().x())
            self._underline_w = float(target_btn.width())
            self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw red sliding underline under active tab
        if self._underline_w > 0:
            underline_h = 3.0
            underline_y = self.height() - underline_h
            rect = QRectF(self._underline_x + 8, underline_y, max(1.0, self._underline_w - 16), underline_h)
            path = QPainterPath()
            path.addRoundedRect(rect, 1.5, 1.5)
            painter.fillPath(path, QColor("#FF0000"))

        painter.end()
