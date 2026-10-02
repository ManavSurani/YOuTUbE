"""Toast notification sliding in at bottom right with 4-second lifetime."""

from typing import Callable, Optional
from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from app.ui.kit.anim import is_animations_enabled


class Toast(QWidget):
    """Temporary notification toast at bottom right of parent window."""

    def __init__(
        self,
        text: str,
        action_text: str = "",
        action_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        self.setStyleSheet(
            "Toast { background-color: #212121; border: 1px solid #383838; border-radius: 8px; } "
            "QLabel { color: #FFFFFF; font-size: 13px; font-weight: 500; } "
            "QPushButton { background: transparent; color: #3EA6FF; font-weight: 600; border: none; padding: 4px 8px; } "
            "QPushButton:hover { color: #65B8FF; text-decoration: underline; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self._label = QLabel(text, self)
        layout.addWidget(self._label, 1)

        if action_text and action_callback:
            self._action_btn = QPushButton(action_text, self)
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.clicked.connect(action_callback)
            self._action_btn.clicked.connect(self.close)
            layout.addWidget(self._action_btn)

        # Lifetime timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._slide_out)

    def show_toast(self, duration_ms: int = 4000) -> None:
        """Position toast in bottom right of parent and animate in."""
        if not self.parentWidget():
            self.show()
            return

        p_geom = self.parentWidget().rect()
        margin = 20
        target_x = p_geom.width() - self.width() - margin
        target_y = p_geom.height() - self.height() - margin

        start_pos = QPoint(target_x, p_geom.height() + 10)
        end_pos = QPoint(target_x, target_y)

        self.move(start_pos)
        self.show()
        self.raise_()

        if is_animations_enabled():
            self._anim = QPropertyAnimation(self, b"pos", self)
            self._anim.setDuration(180)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.setStartValue(start_pos)
            self._anim.setEndValue(end_pos)
            self._anim.start()
        else:
            self.move(end_pos)

        self._timer.start(duration_ms)

    def _slide_out(self) -> None:
        self.close()
        self.deleteLater()
