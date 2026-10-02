"""ThumbLabel widget with rounded clipping and neutral fallback icons."""

from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from app.core.thumbnails import get_rounded_pixmap


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

    def update_thumbnail(self, video_id: str, is_audio: bool = False) -> None:
        self._video_id = video_id
        self._is_audio = is_audio
        pix = get_rounded_pixmap(
            video_id=video_id,
            size=self._size,
            is_audio=is_audio,
            radius=self._radius,
            allow_network=False,
        )
        self.setPixmap(pix)
