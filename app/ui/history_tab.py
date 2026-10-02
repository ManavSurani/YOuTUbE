"""History tab displaying downloaded items with search, filter, and file actions."""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QMessageBox,
    QButtonGroup,
)
from app.core.history_db import HistoryItem, list_items, delete_item
from app.core.proc import start_hidden


def format_size(size_bytes: int) -> str:
    """Format byte size into human readable string."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    return f"{size:.1f} {units[idx]}"


def format_date_str(date_str: Optional[str]) -> str:
    """Return short date from SQLite timestamp."""
    if not date_str:
        return ""
    # "2026-10-01 23:45:00" -> "2026-10-01"
    return date_str.split(" ")[0]


class HistoryRowWidget(QWidget):
    """A 72px tall row representing a downloaded history entry."""

    deleted = Signal()
    redownload = Signal(str, str)  # url, type

    def __init__(self, item: HistoryItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(72)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Thumbnail (64x36)
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(64, 36)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_thumbnail()
        layout.addWidget(self.thumb_label)

        # Info column (Title + metadata line)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(self.item.title, self)
        self.title_label.setStyleSheet("font-weight: 600;")
        info_layout.addWidget(self.title_label)

        meta_parts = [
            self.item.type.capitalize(),
            self.item.quality,
            format_size(self.item.size_bytes),
        ]
        date_str = format_date_str(self.item.created_at)
        if date_str:
            meta_parts.append(date_str)

        file_exists = Path(self.item.file_path).is_file()
        if not file_exists:
            meta_parts.append("File missing")

        meta_text = " • ".join(meta_parts)
        self.meta_label = QLabel(meta_text, self)
        self.meta_label.setProperty("role", "muted")
        info_layout.addWidget(self.meta_label)

        layout.addLayout(info_layout, 1)

        # Action text buttons (Play, Open folder, Copy link, Re-download, Delete)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_style = (
            "QPushButton { background: transparent; border: none; padding: 4px 6px; font-weight: normal; }"
            "QPushButton:hover { text-decoration: underline; }"
        )

        if file_exists:
            self.play_btn = QPushButton("Play", self)
            self.play_btn.setStyleSheet(btn_style)
            self.play_btn.clicked.connect(self._play_file)
            actions_layout.addWidget(self.play_btn)

            self.folder_btn = QPushButton("Open folder", self)
            self.folder_btn.setStyleSheet(btn_style)
            self.folder_btn.clicked.connect(self._open_folder)
            actions_layout.addWidget(self.folder_btn)

        self.copy_btn = QPushButton("Copy link", self)
        self.copy_btn.setStyleSheet(btn_style)
        self.copy_btn.clicked.connect(self._copy_link)
        actions_layout.addWidget(self.copy_btn)

        self.redownload_btn = QPushButton("Re-download", self)
        self.redownload_btn.setStyleSheet(btn_style)
        self.redownload_btn.clicked.connect(self._redownload)
        actions_layout.addWidget(self.redownload_btn)

        self.delete_btn = QPushButton("Delete", self)
        self.delete_btn.setStyleSheet(btn_style)
        self.delete_btn.clicked.connect(self._delete_prompt)
        actions_layout.addWidget(self.delete_btn)

        layout.addLayout(actions_layout)

    def _load_thumbnail(self) -> None:
        from app.core.thumbnails import get_rounded_pixmap
        vid = self.item.video_id or ""
        is_audio = (self.item.type.lower() == "audio")
        pix = get_rounded_pixmap(vid, size=(64, 36), is_audio=is_audio, radius=8)
        self.thumb_label.setPixmap(pix)

    def _play_file(self) -> None:
        p = Path(self.item.file_path)
        if p.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))

    def _open_folder(self) -> None:
        p = Path(self.item.file_path)
        if p.exists():
            # Use explorer /select to highlight file without flashing console
            start_hidden(["explorer", f"/select,{p.resolve()}"])
        else:
            parent = p.parent
            if parent.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent.resolve())))

    def _copy_link(self) -> None:
        QGuiApplication.clipboard().setText(self.item.url)

    def _redownload(self) -> None:
        self.redownload.emit(self.item.url, self.item.type)

    def _delete_prompt(self) -> None:
        from app.core.history_service import delete as delete_history

        msg = QMessageBox(self)
        msg.setWindowTitle("Delete History Item")
        msg.setText(f"Delete \"{self.item.title}\"?")
        
        btn_hist_only = msg.addButton("Remove from history only", QMessageBox.ButtonRole.ActionRole)
        btn_also_file = msg.addButton("Also delete the file", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        clicked = msg.clickedButton()

        if clicked == btn_cancel or self.item.id is None:
            return

        delete_file = (clicked == btn_also_file)
        ok, err_msg = delete_history(self.item.id, delete_file=delete_file)

        if not ok:
            QMessageBox.warning(self, "Delete Failed", err_msg)
            return

        self.deleted.emit()


class HistoryTab(QWidget):
    """History tab containing filter chips, search box, and download list."""

    redownload_requested = Signal(str, str)  # url, type

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_filter: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        # Controls row: Filter chips + Search input
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Filter Chips: All, Video, Audio
        self.chip_group = QButtonGroup(self)
        self.chip_group.setExclusive(True)

        self.chip_all = QPushButton("All", self)
        self.chip_all.setCheckable(True)
        self.chip_all.setChecked(True)
        self.chip_all.setFixedHeight(36)
        self.chip_group.addButton(self.chip_all)
        top_row.addWidget(self.chip_all)

        self.chip_video = QPushButton("Video", self)
        self.chip_video.setCheckable(True)
        self.chip_video.setFixedHeight(36)
        self.chip_group.addButton(self.chip_video)
        top_row.addWidget(self.chip_video)

        self.chip_audio = QPushButton("Audio", self)
        self.chip_audio.setCheckable(True)
        self.chip_audio.setFixedHeight(36)
        self.chip_group.addButton(self.chip_audio)
        top_row.addWidget(self.chip_audio)

        self.chip_all.clicked.connect(lambda: self._set_filter(None))
        self.chip_video.clicked.connect(lambda: self._set_filter("video"))
        self.chip_audio.clicked.connect(lambda: self._set_filter("audio"))

        top_row.addSpacing(8)

        # Search bar
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search history…")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_row.addWidget(self.search_input, 1)

        layout.addLayout(top_row)

        # Scroll area for rows
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.container_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        self.scroll_area.setWidget(self.container_widget)
        layout.addWidget(self.scroll_area, 1)

        # Empty state message
        self.empty_label = QLabel("Nothing here yet.", self)
        self.empty_label.setProperty("role", "muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload_history()

    def _set_filter(self, filter_type: Optional[str]) -> None:
        self._current_filter = filter_type
        self.reload_history()

    def _on_search_changed(self, text: str) -> None:
        self.reload_history()

    def reload_history(self) -> None:
        """Fetch records from SQLite and rebuild row widgets."""
        search_query = self.search_input.text().strip()
        items = list_items(type_filter=self._current_filter, search=search_query)

        # Clear existing rows
        while self.list_layout.count() > 1:
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not items:
            self.empty_label.setVisible(True)
            self.scroll_area.setVisible(False)
            return

        self.empty_label.setVisible(False)
        self.scroll_area.setVisible(True)

        for item in items:
            row = HistoryRowWidget(item, self.container_widget)
            row.deleted.connect(self.reload_history)
            row.redownload.connect(self.redownload_requested.emit)
            # Insert before stretch item
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
