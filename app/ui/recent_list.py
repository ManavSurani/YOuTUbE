"""Recently downloaded list component showing the last 5 completed items for a tab.

Updates immediately upon download completion and links directly to History tab.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.file_actions import open_file, reveal_in_folder
from app.core.history_db import HistoryItem, list_items
from app.ui.kit.buttons import IconButton
from app.ui.kit.elided_label import ElidedLabel
from app.ui.kit.thumb_label import ThumbLabel
from app.ui.kit.toast import Toast
from app.ui.theme import ThemeManager, tok


# Files below this size are leftovers of a failed download, not a usable video or song
INCOMPLETE_BYTES = 1024

_AUDIO_CODECS = {".opus": "Opus", ".webm": "Opus", ".m4a": "M4A", ".mp3": "MP3", ".flac": "FLAC", ".wav": "WAV", ".ogg": "Vorbis"}


def display_quality(item: HistoryItem) -> str:
    """'Best original' becomes 'Original (Opus)' etc. from the saved file's type; other labels are unchanged."""
    if item.quality == "Best original" and item.file_path:
        codec = _AUDIO_CODECS.get(Path(item.file_path).suffix.lower())
        if codec:
            return f"Original ({codec})"
    return item.quality


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

        self.title_lbl = ElidedLabel(item.title, self)
        self.title_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.title_lbl.setProperty("role", "strong")
        info_layout.addWidget(self.title_lbl)

        file_exists = Path(item.file_path).is_file() if item.file_path else False
        incomplete = file_exists and item.size_bytes < INCOMPLETE_BYTES
        if not file_exists:
            size_str = "File missing"
        elif incomplete:
            size_str = "Incomplete file"
        else:
            size_str = _fmt_size(item.size_bytes)
        parts = [p for p in (display_quality(item), size_str) if p]

        self.meta_lbl = QLabel(" • ".join(parts), self)
        self.meta_lbl.setTextFormat(Qt.TextFormat.PlainText)
        info_layout.addWidget(self.meta_lbl)

        layout.addLayout(info_layout, 1)

        # Action buttons: Play and Show in folder via IconButton
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(6)

        self.play_btn = IconButton("play", size=32, tooltip="Play", parent=self)
        self.play_btn.setText("Play")
        self.play_btn.clicked.connect(self._play_file)
        self.actions_layout.addWidget(self.play_btn)

        self.folder_btn = IconButton("folder", size=32, tooltip="Show in folder", parent=self)
        self.folder_btn.setText("Open folder")
        self.folder_btn.clicked.connect(self._open_folder)
        self.actions_layout.addWidget(self.folder_btn)

        layout.addLayout(self.actions_layout)

        self.play_btn.setVisible(file_exists and not incomplete)
        self.folder_btn.setVisible(bool(item.file_path))

        self._restyle()
        ThemeManager.instance().changed.connect(self._restyle)

    def _restyle(self, *_) -> None:
        self.setStyleSheet(
            "RecentRow { background-color: transparent; border-radius: 8px; } "
            f"RecentRow:hover {{ background-color: {tok('surface')}; }}"
        )
        self.meta_lbl.setStyleSheet(f"font-size: 12px; color: {tok('text_muted')};")

    def _show_feedback(self, message: str) -> None:
        parent = self.window() if self.window() else self
        toast = Toast(message, parent=parent)
        toast.show_toast(4000)

    def _play_file(self) -> None:
        ok, msg = open_file(self.item.file_path)
        if not ok and msg:
            self._show_feedback(msg)

    def _open_folder(self) -> None:
        ok, msg = reveal_in_folder(self.item.file_path)
        if not ok and msg:
            self._show_feedback(msg)


class RecentList(QWidget):
    """Container showing up to 5 recently downloaded files for the given type."""

    see_all_clicked = Signal(str)

    def __init__(self, kind: str = "video", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind.lower()
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(6)

        parent_widget = self.parent()
        if parent_widget is not None:
            parent_widget.installEventFilter(self)

        self._see_all_btn: Optional[QPushButton] = None
        ThemeManager.instance().changed.connect(self._style_see_all)
        self.refresh()

    def eventFilter(self, watched, event):
        if watched == self.parent() and event.type() == QEvent.Type.Show:
            self.refresh()
        return super().eventFilter(watched, event)

    def _clear_layout(self, layout: Optional[QLayout]) -> None:
        """Recursively clear layout and deleteLater all widgets."""
        if layout is None:
            return
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)

    def _style_see_all(self, *_) -> None:
        if self._see_all_btn is not None:
            self._see_all_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; font-size: 12px; color: {tok('info')}; }} "
                "QPushButton:hover { text-decoration: underline; }"
            )

    def refresh(self) -> None:
        """Reload last 5 items of matching type from history database."""
        self._clear_layout(self._layout)

        items = list_items(type_filter=self.kind)[:5]
        if not items:
            self.setVisible(False)
            return

        self.setVisible(True)

        header = QLabel(f"Recently downloaded", self)
        header.setProperty("role", "strong")
        self._layout.addWidget(header)

        for item in items:
            row = RecentRow(item, self)
            self._layout.addWidget(row)

        # "See all" link labelled by tab
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.addStretch(1)

        link_text = f"See all {self.kind} history →"
        see_all_btn = QPushButton(link_text, self)
        see_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._see_all_btn = see_all_btn
        self._style_see_all()
        see_all_btn.clicked.connect(lambda: self.see_all_clicked.emit(self.kind))
        footer_layout.addWidget(see_all_btn)

        self._layout.addLayout(footer_layout)
