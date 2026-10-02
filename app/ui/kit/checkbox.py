"""AnimatedCheckBox custom component with smooth 150 ms red fill and white checkmark.

Fixes B11 (eliminates ambiguous white-filled checkbox state).
Provides accessible focus ring and crisp painter-rendered checkmark.
"""

from typing import Optional
from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QWidget,
)

from app.ui.kit.anim import is_animations_enabled


class AnimatedCheckBox(QAbstractButton):
    """Custom checkbox drawn with clean vector graphics and animated checkmark."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._check_progress = 0.0
        self._anim: Optional[QPropertyAnimation] = None

        self.toggled.connect(self._on_toggled)

    def _get_progress(self) -> float:
        return self._check_progress

    def _set_progress(self, val: float) -> None:
        self._check_progress = val
        self.update()

    check_progress = Property(float, _get_progress, _set_progress)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._check_progress = 1.0 if checked else 0.0
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        if not is_animations_enabled():
            self._check_progress = 1.0 if checked else 0.0
            self.update()
            return

        if self._anim:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"check_progress", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self._check_progress)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:
        font = self.font()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0
        return QSize(20 + (8 if self.text() else 0) + text_w, 24)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        h = self.height()
        box_size = 18.0
        box_y = (h - box_size) / 2.0
        box_rect = QRectF(1.0, box_y, box_size, box_size)
        radius = 4.0

        p = self._check_progress

        # Colors interpolation
        # Unchecked: bg #1F1F1F, border #444444
        # Checked: bg #FF0000, border #FF0000
        bg_r = int(31 * (1.0 - p) + 255 * p)
        bg_g = int(31 * (1.0 - p) + 0 * p)
        bg_b = int(31 * (1.0 - p) + 0 * p)
        bg_color = QColor(bg_r, bg_g, bg_b)

        border_r = int(68 * (1.0 - p) + 255 * p)
        border_g = int(68 * (1.0 - p) + 0 * p)
        border_b = int(68 * (1.0 - p) + 0 * p)
        border_color = QColor(border_r, border_g, border_b)

        # Draw box
        path = QPainterPath()
        path.addRoundedRect(box_rect, radius, radius)
        painter.fillPath(path, bg_color)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawPath(path)

        # Keyboard focus ring
        if self.hasFocus():
            painter.setPen(QPen(QColor("#3EA6FF"), 1.5))
            painter.drawRoundedRect(box_rect.adjusted(-2, -2, 2, 2), radius + 2, radius + 2)

        # Draw white checkmark if progress > 0
        if p > 0.05:
            cx = box_rect.left() + box_size / 2.0
            cy = box_rect.top() + box_size / 2.0

            pen = QPen(QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            check_path = QPainterPath()
            p1 = QPointF(cx - 4.5, cy + 0.2)
            p2 = QPointF(cx - 1.2, cy + 3.8)
            p3 = QPointF(cx + 4.8, cy - 3.5)

            if p >= 0.5:
                # First leg full, second leg partial
                leg2_p = (p - 0.5) * 2.0
                curr_p3 = QPointF(p2.x() + (p3.x() - p2.x()) * leg2_p, p2.y() + (p3.y() - p2.y()) * leg2_p)
                check_path.moveTo(p1)
                check_path.lineTo(p2)
                check_path.lineTo(curr_p3)
            else:
                # First leg partial
                leg1_p = p * 2.0
                curr_p2 = QPointF(p1.x() + (p2.x() - p1.x()) * leg1_p, p1.y() + (p2.y() - p1.y()) * leg1_p)
                check_path.moveTo(p1)
                check_path.lineTo(curr_p2)

            painter.drawPath(check_path)

        # Draw text label
        text = self.text()
        if text:
            painter.setFont(self.font())
            painter.setPen(QColor("#FFFFFF" if self.isEnabled() else "#777777"))
            text_rect = QRectF(box_size + 10.0, 0, self.width() - box_size - 10.0, h)
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)

        painter.end()
