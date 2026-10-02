"""AnimatedButton component providing consistent heights, states, and smooth feedback.

Supports roles: 'primary', 'secondary', 'ghost', and 'icon'.
Handles loading spinner and flash_success states.
"""

import math
from typing import Optional

from PySide6.QtCore import (
    Property,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QPushButton,
    QWidget,
)

from app.ui.theme import DARK_TOKENS


class AnimatedButton(QPushButton):
    """Button implementing YouTube design system specifications (36px, feedback, states)."""

    def __init__(
        self,
        text: str = "",
        role: str = "secondary",
        icon: Optional[QIcon] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self._role = role.lower()
        if icon:
            self.setIcon(icon)

        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # State tracking
        self._is_loading = False
        self._is_success = False
        self._hovered = False
        self._pressed = False
        self._spinner_angle = 0

        # Success timer
        self._success_timer = QTimer(self)
        self._success_timer.setSingleShot(True)
        self._success_timer.timeout.connect(self._reset_success)

        # Spinner animation timer
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(25)
        self._spinner_timer.timeout.connect(self._rotate_spinner)

        self._update_appearance()

    @property
    def role(self) -> str:
        return self._role

    @role.setter
    def role(self, value: str) -> None:
        self._role = value.lower()
        self._update_appearance()

    def set_loading(self, loading: bool) -> None:
        """Enable or disable loading spinner state."""
        self._is_loading = loading
        self._is_success = False
        self.setEnabled(not loading)
        if loading:
            self._spinner_timer.start()
        else:
            self._spinner_timer.stop()
        self.update()

    def flash_success(self, duration_ms: int = 1000) -> None:
        """Flash a success checkmark on the button for duration_ms."""
        self._is_loading = False
        self._spinner_timer.stop()
        self._is_success = True
        self.update()
        self._success_timer.start(duration_ms)

    def _reset_success(self) -> None:
        self._is_success = False
        self.update()

    def _rotate_spinner(self) -> None:
        self._spinner_angle = (self._spinner_angle + 12) % 360
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if not self._is_loading:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def _update_appearance(self) -> None:
        # Base font setup
        font = self.font()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        font.setWeight(QFont.Weight.DemiBold if self._role in ("primary", "secondary") else QFont.Weight.Medium)
        self.setFont(font)
        self.update()

    def _get_colors(self):
        """Return (bg_color, text_color, border_color) for current state."""
        if not self.isEnabled():
            if self._role == "primary":
                return QColor("#551111"), QColor("#888888"), None
            return QColor("#181818"), QColor("#555555"), QColor("#282828")

        if self._role == "primary":
            if self._pressed:
                return QColor("#B30000"), QColor("#FFFFFF"), None
            if self._hovered:
                return QColor("#CC0000"), QColor("#FFFFFF"), None
            return QColor("#FF0000"), QColor("#FFFFFF"), None

        elif self._role == "secondary":
            if self._pressed:
                return QColor("#1F1F1F"), QColor("#FFFFFF"), QColor("#383838")
            if self._hovered:
                return QColor("#333333"), QColor("#FFFFFF"), QColor("#444444")
            return QColor("#272727"), QColor("#FFFFFF"), QColor("#383838")

        elif self._role == "ghost":
            if self._pressed:
                return QColor("#222222"), QColor("#FFFFFF"), None
            if self._hovered:
                return QColor("#1C1C1C"), QColor("#FFFFFF"), None
            return QColor(Qt.GlobalColor.transparent), QColor("#AAAAAA"), None

        elif self._role == "icon":
            if self._pressed:
                return QColor("#252525"), QColor("#FFFFFF"), None
            if self._hovered:
                return QColor("#303030"), QColor("#FFFFFF"), None
            return QColor(Qt.GlobalColor.transparent), QColor("#AAAAAA"), None

        return QColor("#272727"), QColor("#FFFFFF"), None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        radius = 8.0

        # Press effect: scale down slightly (1px shrink)
        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0) if self._pressed else QRectF(0.0, 0.0, w, h)

        bg, text_color, border_color = self._get_colors()

        # Background
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, bg)

        # Border
        if border_color:
            painter.setPen(QPen(border_color, 1.0))
            painter.drawPath(path)

        # Focus ring
        if self.hasFocus():
            painter.setPen(QPen(QColor("#3EA6FF"), 1.5))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius - 1, radius - 1)

        cx, cy = rect.center().x(), rect.center().y()

        # 1. Loading state: draw spinner
        if self._is_loading:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            spinner_r = 7.0
            spinner_rect = QRectF(cx - spinner_r, cy - spinner_r, spinner_r * 2, spinner_r * 2)

            pen = QPen(text_color, 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start_angle = int(self._spinner_angle * 16)
            span_angle = int(270 * 16)
            painter.drawArc(spinner_rect, start_angle, span_angle)
            painter.end()
            return

        # 2. Success state: draw checkmark
        if self._is_success:
            pen = QPen(text_color, 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            check_path = QPainterPath()
            check_path.moveTo(cx - 6, cy)
            check_path.lineTo(cx - 2, cy + 4)
            check_path.lineTo(cx + 6, cy - 4)
            painter.drawPath(check_path)
            painter.end()
            return

        # 3. Normal state: icon + text
        icon = self.icon()
        text = self.text()

        if not icon.isNull() and text:
            # Draw icon and text side-by-side
            icon_size = 16
            spacing = 8
            icon_rect = QRect(int(cx - 30), int(cy - icon_size / 2), icon_size, icon_size)
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

            painter.setPen(text_color)
            painter.setFont(self.font())
            text_rect = QRectF(cx - 10, rect.top(), rect.width() / 2, rect.height())
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)
        elif not icon.isNull():
            # Icon only
            icon_size = min(int(h * 0.5), 20)
            icon_rect = QRect(int(cx - icon_size / 2), int(cy - icon_size / 2), icon_size, icon_size)
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
        else:
            # Text only
            painter.setPen(text_color)
            painter.setFont(self.font())
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)

        painter.end()
