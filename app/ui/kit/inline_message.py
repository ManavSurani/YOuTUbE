"""InlineMessage banner that automatically hides after 4 seconds and clears on tab change."""

from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class InlineMessage(QWidget):
    """Error or info banner that auto-hides after 4 seconds and clears cleanly."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self._label = QLabel(self)
        self._label.setStyleSheet("font-size: 12px; font-weight: 500;")
        layout.addWidget(self._label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear)

    def show_error(self, message: str, auto_hide_ms: int = 4000) -> None:
        """Display an error message that auto-hides after 4s."""
        self._label.setText(message)
        self._label.setStyleSheet("color: #FF4E45; font-size: 12px; font-weight: 500;")
        self.setStyleSheet("InlineMessage { background-color: #2B1818; border-radius: 6px; }")
        self.setVisible(True)
        self._timer.stop()
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def show_info(self, message: str, auto_hide_ms: int = 4000) -> None:
        """Display an informational message that auto-hides after 4s."""
        self._label.setText(message)
        self._label.setStyleSheet("color: #3EA6FF; font-size: 12px; font-weight: 500;")
        self.setStyleSheet("InlineMessage { background-color: #162436; border-radius: 6px; }")
        self.setVisible(True)
        self._timer.stop()
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def clear(self) -> None:
        """Clear message and immediately hide the banner."""
        self._timer.stop()
        self._label.setText("")
        self.setVisible(False)

    def text(self) -> str:
        return self._label.text()
