"""ThumbLabel widget with rounded clipping and neutral fallback icons."""

from typing import Optional, Tuple
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from app.core.thumbnails import get_rounded_pixmap, get_thumbnail_path
from app.ui.theme import ThemeManager, qcolor


class ThumbLabel(QLabel):
    """Image label showing rounded thumbnails with neutral fallback icons."""

    def __init__(
        self,
        video_id: str = "",
        is_audio: bool = False,
        size: Tuple[int, int] = (64, 36),
        radius: int = 6,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._video_id = video_id
        self._is_audio = is_audio
        self._size = size
        self._radius = radius

        self.setFixedSize(size[0], size[1])
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_thumbnail(video_id, is_audio)
        ThemeManager.instance().changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme: str) -> None:
        self.update_thumbnail(self._video_id, self._is_audio)

    def update_thumbnail(self, video_id: str, is_audio: bool = False) -> None:
        self._video_id = video_id
        self._is_audio = is_audio
        if not video_id or get_thumbnail_path(video_id) is None:
            self.setPixmap(self._placeholder())
            return
        pix = get_rounded_pixmap(
            video_id=video_id,
            size=self._size,
            is_audio=is_audio,
            radius=self._radius,
            allow_network=False,
        )
        self.setPixmap(pix)

    def _placeholder(self) -> QPixmap:
        """Rounded surface tile with a muted play (video) or note (audio) glyph."""
        w, h = self._size
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tile = QPainterPath()
        tile.addRoundedRect(QRectF(0, 0, w, h), self._radius, self._radius)
        painter.fillPath(tile, qcolor("surface"))
        cx, cy, s = w / 2.0, h / 2.0, min(w, h) * 0.18
        glyph = QPainterPath()
        if self._is_audio:
            glyph.addEllipse(QPointF(cx - s * 0.4, cy + s * 0.6), s * 0.55, s * 0.45)
            glyph.addRect(QRectF(cx + s * 0.05, cy - s * 1.1, s * 0.22, s * 1.7))
        else:
            glyph.moveTo(cx - s * 0.7, cy - s)
            glyph.lineTo(cx + s, cy)
            glyph.lineTo(cx - s * 0.7, cy + s)
            glyph.closeSubpath()
        painter.fillPath(glyph, qcolor("text_muted"))
        painter.end()
        return pix
