"""Recently downloaded list component showing the last 5 completed items for a tab.

Updates immediately upon download completion and links directly to History tab.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.history_db import HistoryItem, list_items
from app.core.proc import start_hidden
from app.ui.kit.thumb_label import ThumbLabel


def _fmt_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(size_bytes)
    idx = 0
    while val >= 1024.0 and idx < len(units) - 1:
        val /= 1024.0
        idx += 1
    return f"{val:.1f} {units[idx]}"


class RecentRow(QWidget):
    """A compact 56px row displaying a recently downloaded video or audio file."""

    def __init__(self, item: HistoryItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(56)
        self.setStyleSheet("RecentRow { background-color: #1A1A1A; border-radius: 6px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Thumbnail (64x36)
        is_audio = (item.type.lower() == "audio")
        self.thumb = ThumbLabel(video_id=item.video_id or "", is_audio=is_audio, size=(64, 36), radius=4, parent=self)
        layout.addWidget(self.thumb)

        # Title & details
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        title_lbl = QLabel(item.title, self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        info_layout.addWidget(title_lbl)

        file_exists = Path(item.file_path).is_file() if item.file_path else False
        parts = [item.quality, _fmt_size(item.size_bytes)]
        if not file_exists:
            parts.append("File missing")

        meta_lbl = QLabel(" • ".join(parts), self)
        meta_lbl.setStyleSheet(f"font-size: 11px; color: {'#FF4E45' if not file_exists else '#AAAAAA'};")
        info_layout.addWidget(meta_lbl)

        layout.addLayout(info_layout, 1)

        # Action buttons: Play and Open Folder
        btn_style = (
            "QPushButton { background: transparent; border: none; font-size: 12px; color: #AAAAAA; padding: 4px 6px; } "
            "QPushButton:hover { color: #FFFFFF; text-decoration: underline; }"
        )

        if file_exists:
            play_btn = QPushButton("Play", self)
            play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_btn.setStyleSheet(btn_style)
            play_btn.clicked.connect(self._play_file)
            layout.addWidget(play_btn)

            folder_btn = QPushButton("Open folder", self)
            folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            folder_btn.setStyleSheet(btn_style)
            folder_btn.clicked.connect(self._open_folder)
            layout.addWidget(folder_btn)

    def _play_file(self) -> None:
        p = Path(self.item.file_path)
        if p.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))

    def _open_folder(self) -> None:
        p = Path(self.item.file_path)
        if p.exists():
            start_hidden(["explorer", f"/select,{p.resolve()}"])
        elif p.parent.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent.resolve())))


class RecentList(QWidget):
    """Container showing up to 5 recently downloaded files for the given type."""

    see_all_clicked = Signal()

    def __init__(self, kind: str = "video", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind.lower()
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(6)

        self.refresh()

    def refresh(self) -> None:
        """Reload last 5 items of matching type from history database."""
        # Clear existing rows
        while self._layout.count() > 0:
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        items = list_items(type_filter=self.kind)[:5]
        if not items:
            self.setVisible(False)
            return

        self.setVisible(True)

        header = QLabel(f"Recently downloaded", self)
        header.setStyleSheet("font-size: 13px; font-weight: 600; color: #AAAAAA; margin-bottom: 2px;")
        self._layout.addWidget(header)

        for item in items:
            row = RecentRow(item, self)
            self._layout.addWidget(row)

        # "See all in History" link
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.addStretch(1)

        see_all_btn = QPushButton("See all in History →", self)
        see_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        see_all_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 12px; color: #3EA6FF; } "
            "QPushButton:hover { text-decoration: underline; color: #65B8FF; }"
        )
        see_all_btn.clicked.connect(self.see_all_clicked.emit)
        footer_layout.addWidget(see_all_btn)

        self._layout.addLayout(footer_layout)
