"""History tab displaying downloaded items with search, filter chips, lazy loading, and safe file actions.

Implements Phase 5 specifications:
- Rounded thumbnail via ThumbLabel with neutral vector fallbacks (never letters)
- Action icon buttons with tooltips, press shrink, hover glow, and success tick
- Delete button turns red on hover
- Custom delete dialog (Recycle Bin via send2trash, locked file handling)
- Clear all history with confirmation
- Background file check worker with database caching (zero UI freeze)
- Search box does not steal focus on tab switch (B12 fix)
- Lazy loading (first 50 rows, loads on scroll, <1s for 500+ items)
- In-place row updates on relink and smooth collapse animation on delete
- Re-download with quality pre-selection
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QUrl,
    QThread,
    Signal,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.history_db import HistoryItem, list_items
import app.core.history_service as history_service
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.proc import start_hidden
from app.ui.kit.anim import is_animations_enabled
from app.ui.kit.buttons import AnimatedButton, IconButton
from app.ui.kit.checkbox import AnimatedCheckBox
from app.ui.kit.thumb_label import ThumbLabel


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
    return date_str.split(" ")[0]


class FileCheckWorker(QThread):
    """Background worker verifying file existence on disk without blocking the UI thread."""

    status_updated = Signal(int, bool)  # row_id, exists

    def __init__(self, items: List[Tuple[int, str, int]], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._items = items
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        for row_id, file_path, cached_missing in self._items:
            if not self._running:
                break
            exists = Path(file_path).is_file() if file_path else False
            is_missing = 0 if exists else 1
            if is_missing != cached_missing:
                try:
                    from app.core.history_db import get_item, update_item
                    item = get_item(row_id)
                    if item:
                        item.file_missing = is_missing
                        update_item(item)
                except Exception as exc:
                    get_logger().debug(f"Failed to update file_missing cache for row {row_id}: {exc}")
                self.status_updated.emit(row_id, exists)


class FilterChip(QPushButton):
    """Pill-shaped filter button with smooth active color transition."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("""
            QPushButton {
                background-color: #212121;
                color: #AAAAAA;
                border: none;
                border-radius: 16px;
                padding: 0 16px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #303030;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #CC0000;
                color: #FFFFFF;
                font-weight: 600;
            }
            QPushButton:checked:hover {
                background-color: #B30000;
                color: #FFFFFF;
            }
        """)


class HistoryDeleteDialog(QDialog):
    """Custom delete confirmation dialog with three clear options."""

    ACTION_CANCEL = 0
    ACTION_REMOVE_HISTORY_ONLY = 1
    ACTION_DELETE_FILE_TOO = 2

    def __init__(self, item: HistoryItem, file_exists: bool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item = item
        self.file_exists = file_exists
        self.selected_action = self.ACTION_CANCEL

        self.setWindowTitle("Delete from history")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #1F1F1F;
                border: 1px solid #333333;
                border-radius: 12px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title_label = QLabel("Delete from history?", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title_label)

        display_title = self.item.title
        if len(display_title) > 80:
            display_title = display_title[:77] + "…"

        msg_text = f'Are you sure you want to remove "{display_title}" from your download history?'
        if self.file_exists:
            msg_text += "\n\nYou can keep the downloaded file or send it to the Recycle Bin."

        msg_label = QLabel(msg_text, self)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 13px; color: #CCCCCC; line-height: 1.4;")
        layout.addWidget(msg_label)

        layout.addSpacing(8)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        if self.file_exists:
            self.btn_delete_file = AnimatedButton("Delete file too", role="primary", parent=self)
            self.btn_delete_file.clicked.connect(self._on_delete_file)
            btn_layout.addWidget(self.btn_delete_file)

        self.btn_history_only = AnimatedButton("Remove from history only", role="secondary", parent=self)
        self.btn_history_only.clicked.connect(self._on_history_only)
        btn_layout.addWidget(self.btn_history_only)

        self.btn_cancel = AnimatedButton("Cancel", role="ghost", parent=self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _on_delete_file(self) -> None:
        self.selected_action = self.ACTION_DELETE_FILE_TOO
        self.accept()

    def _on_history_only(self) -> None:
        self.selected_action = self.ACTION_REMOVE_HISTORY_ONLY
        self.accept()


class ClearAllDialog(QDialog):
    """Confirmation dialog for clearing entire download history."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.delete_files = False

        self.setWindowTitle("Clear download history")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #1F1F1F;
                border: 1px solid #333333;
                border-radius: 12px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title_label = QLabel("Clear download history?", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title_label)

        msg_label = QLabel("This will remove all downloaded items from your history list.", self)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 13px; color: #CCCCCC;")
        layout.addWidget(msg_label)

        self.chk_files = AnimatedCheckBox("Also delete the files from my computer", parent=self)
        self.chk_files.setChecked(False)
        layout.addWidget(self.chk_files)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)

        btn_cancel = AnimatedButton("Cancel", role="ghost", parent=self)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_clear = AnimatedButton("Clear history", role="primary", parent=self)
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

    def _on_clear(self) -> None:
        self.delete_files = self.chk_files.isChecked()
        self.accept()


class HistoryRowWidget(QWidget):
    """A 72px tall row representing a downloaded history entry with icon actions and animations."""

    deleted = Signal()
    redownload = Signal(str, str, str)  # url, type, quality

    def __init__(self, item: HistoryItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            HistoryRowWidget {
                background-color: transparent;
                border-radius: 8px;
            }
            HistoryRowWidget:hover {
                background-color: #1A1A1A;
            }
        """)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 1. Thumbnail (64x36) via ThumbLabel
        is_audio = (self.item.type.lower() == "audio")
        self.thumb_label = ThumbLabel(
            video_id=self.item.video_id or "",
            is_audio=is_audio,
            size=(64, 36),
            radius=6,
            parent=self,
        )
        layout.addWidget(self.thumb_label)

        # 2. Metadata column (Title + meta line)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(self.item.title, self)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF;")
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel(self)
        self.meta_label.setTextFormat(Qt.TextFormat.RichText)
        self._update_meta_text()
        info_layout.addWidget(self.meta_label)

        layout.addLayout(info_layout, 1)

        # 3. Icon buttons: Play / Locate, Open folder, Copy link, Re-download, Delete
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(6)

        # Play button
        self.play_btn = IconButton("play", size=32, tooltip="Play file", parent=self)
        self.play_btn.clicked.connect(self._play_file)
        self.actions_layout.addWidget(self.play_btn)

        # Locate button (replaces Play when file is missing)
        self.locate_btn = IconButton("locate", size=32, tooltip="Locate missing file", parent=self)
        self.locate_btn.clicked.connect(self.locate_file)
        self.actions_layout.addWidget(self.locate_btn)

        # Open folder button
        self.folder_btn = IconButton("folder", size=32, tooltip="Show in folder", parent=self)
        self.folder_btn.clicked.connect(self._open_folder)
        self.actions_layout.addWidget(self.folder_btn)

        # Copy link button
        self.copy_btn = IconButton("copy", size=32, tooltip="Copy link", parent=self)
        self.copy_btn.clicked.connect(self._copy_link)
        self.actions_layout.addWidget(self.copy_btn)

        # Re-download button
        self.redownload_btn = IconButton("redownload", size=32, tooltip="Re-download", parent=self)
        self.redownload_btn.clicked.connect(self._redownload)
        self.actions_layout.addWidget(self.redownload_btn)

        # Delete button (turns red on hover)
        self.delete_btn = IconButton("delete", is_danger=True, size=32, tooltip="Delete", parent=self)
        self.delete_btn.clicked.connect(self._delete_prompt)
        self.actions_layout.addWidget(self.delete_btn)

        layout.addLayout(self.actions_layout)

        # Apply initial file existence state from cache
        file_missing = bool(self.item.file_missing)
        self.play_btn.setVisible(not file_missing)
        self.locate_btn.setVisible(file_missing)

    def _update_meta_text(self) -> None:
        parts = [
            self.item.type.capitalize(),
            self.item.quality,
            format_size(self.item.size_bytes),
        ]
        date_str = format_date_str(self.item.created_at)
        if date_str:
            parts.append(date_str)

        if self.item.file_missing:
            parts.append('<span style="color: #AAAAAA; font-weight: 500;">File missing</span>')

        self.meta_label.setText(" • ".join(parts))

    def update_file_status(self, exists: bool) -> None:
        """Update file missing state in-place without reloading list."""
        self.item.file_missing = 0 if exists else 1
        self._update_meta_text()
        self.play_btn.setVisible(exists)
        self.locate_btn.setVisible(not exists)

    def _play_file(self) -> None:
        p = Path(self.item.file_path)
        if p.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))

    def _open_folder(self) -> None:
        p = Path(self.item.file_path)
        if p.is_file():
            start_hidden(["explorer", f"/select,{p.resolve()}"])
        elif p.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent.resolve())))

    def _copy_link(self) -> None:
        QGuiApplication.clipboard().setText(self.item.url)
        self.copy_btn.flash_success(1000)

    def _redownload(self) -> None:
        self.redownload.emit(self.item.url, self.item.type, self.item.quality)

    def locate_file(self) -> None:
        """Prompt user to relocate a missing downloaded file and relink record."""
        chosen_path, _ = QFileDialog.getOpenFileName(
            self,
            "Locate downloaded file",
            str(DEFAULT_DOWNLOADS),
            "All Files (*.*)",
        )
        if not chosen_path:
            return

        if self.item.id is None:
            return

        ok, err_msg = history_service.relink(self.item.id, chosen_path)
        if not ok:
            QMessageBox.warning(self, "Relink Failed", err_msg)
            return

        self.item.file_path = chosen_path
        p = Path(chosen_path)
        if p.is_file():
            self.item.size_bytes = p.stat().st_size
        self.update_file_status(exists=True)

    def _delete_prompt(self) -> None:
        if self.item.id is None:
            return

        file_exists = (not bool(self.item.file_missing)) and Path(self.item.file_path).is_file()
        dialog = HistoryDeleteDialog(self.item, file_exists=file_exists, parent=self)
        dialog.exec()

        if dialog.selected_action == HistoryDeleteDialog.ACTION_CANCEL:
            return

        delete_file = (dialog.selected_action == HistoryDeleteDialog.ACTION_DELETE_FILE_TOO)
        ok, err_msg = history_service.delete(self.item.id, delete_file=delete_file)

        if not ok:
            QMessageBox.warning(
                self,
                "Cannot delete file",
                f"The file could not be deleted:\n\n{err_msg}\n\nThe item was kept in history.",
            )
            return

        self.animate_delete(on_finished=self.deleted.emit)

    def animate_delete(self, on_finished) -> None:
        """Smoothly fade and collapse row without jumping."""
        if not is_animations_enabled():
            on_finished()
            return

        opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity_effect)

        self._anim_group = QParallelAnimationGroup(self)

        fade = QPropertyAnimation(opacity_effect, b"opacity", self)
        fade.setDuration(150)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_group.addAnimation(fade)

        collapse = QPropertyAnimation(self, b"maximumHeight", self)
        collapse.setDuration(150)
        collapse.setStartValue(self.height())
        collapse.setEndValue(0)
        collapse.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_group.addAnimation(collapse)

        self._anim_group.finished.connect(on_finished)
        self._anim_group.start()


class HistoryTab(QWidget):
    """History tab containing filter chips, search box, lazy loading, and actions."""

    redownload_requested = Signal(str, str, str)  # url, type, quality

    PAGE_SIZE = 50

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_filter: Optional[str] = None
        self._all_items: List[HistoryItem] = []
        self._rendered_rows: Dict[int, HistoryRowWidget] = {}
        self._rendered_count = 0
        self._file_worker: Optional[FileCheckWorker] = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        # 1. Top controls row: Filter chips + Search input + Clear all
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Filter Chips: All, Video, Audio
        self.chip_group = QButtonGroup(self)
        self.chip_group.setExclusive(True)

        self.chip_all = FilterChip("All", self)
        self.chip_all.setChecked(True)
        self.chip_group.addButton(self.chip_all)
        top_row.addWidget(self.chip_all)

        self.chip_video = FilterChip("Video", self)
        self.chip_group.addButton(self.chip_video)
        top_row.addWidget(self.chip_video)

        self.chip_audio = FilterChip("Audio", self)
        self.chip_group.addButton(self.chip_audio)
        top_row.addWidget(self.chip_audio)

        self.chip_all.clicked.connect(lambda: self._set_filter(None))
        self.chip_video.clicked.connect(lambda: self._set_filter("video"))
        self.chip_audio.clicked.connect(lambda: self._set_filter("audio"))

        top_row.addSpacing(8)

        # Search bar (ClickFocus ensures it does NOT steal focus on tab switch - B12 fix)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search history…")
        self.search_input.setFixedHeight(36)
        self.search_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_row.addWidget(self.search_input, 1)

        # Clear all history ghost button
        self.clear_all_btn = AnimatedButton("Clear all", role="ghost", parent=self)
        self.clear_all_btn.setToolTip("Clear download history")
        self.clear_all_btn.clicked.connect(self._on_clear_all)
        top_row.addWidget(self.clear_all_btn)

        layout.addLayout(top_row)

        # 2. Scroll area for lazy loading rows
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.container_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)
        self.list_layout.addStretch(1)

        self.scroll_area.setWidget(self.container_widget)
        layout.addWidget(self.scroll_area, 1)

        # 3. Empty state message
        self.empty_widget = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(6)

        self.empty_title = QLabel("Nothing here yet.", self.empty_widget)
        self.empty_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #FFFFFF;")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)

        self.empty_hint = QLabel("Paste a YouTube link in the Video or Audio tab to start downloading.", self.empty_widget)
        self.empty_hint.setStyleSheet("font-size: 13px; color: #888888;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_hint)

        layout.addWidget(self.empty_widget, 1)

        # Compatibility alias for tests
        self.empty_label = self.empty_title

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Prevent search box from taking focus when tab opens (B12 fix)
        self.scroll_area.setFocus()
        self.search_input.clearFocus()
        self.reload_history()

    def refresh_items(self) -> None:
        """Public alias for refreshing items on tab switch."""
        self.reload_history()

    def _set_filter(self, filter_type: Optional[str]) -> None:
        self._current_filter = filter_type
        self.reload_history()

    def _on_search_changed(self, text: str) -> None:
        self.reload_history()

    def reload_history(self) -> None:
        """Fetch records from SQLite and lazily render initial page."""
        if self._file_worker and self._file_worker.isRunning():
            self._file_worker.stop()
            self._file_worker.wait(200)

        search_query = self.search_input.text().strip()
        self._all_items = list_items(type_filter=self._current_filter, search=search_query)

        # Clear existing row widgets
        while self.list_layout.count() > 1:
            child = self.list_layout.takeAt(0)
            if child.widget():
                w = child.widget()
                w.setParent(None)
                w.deleteLater()

        self._rendered_rows.clear()
        self._rendered_count = 0

        if not self._all_items:
            self.empty_widget.setVisible(True)
            self.scroll_area.setVisible(False)
            self.clear_all_btn.setEnabled(False)
            return

        self.empty_widget.setVisible(False)
        self.scroll_area.setVisible(True)
        self.clear_all_btn.setEnabled(True)

        self._render_next_page()

    def _render_next_page(self) -> None:
        """Render next page of items lazily for fast scrolling."""
        if self._rendered_count >= len(self._all_items):
            return

        end_idx = min(self._rendered_count + self.PAGE_SIZE, len(self._all_items))
        batch = self._all_items[self._rendered_count:end_idx]
        worker_batch: List[Tuple[int, str, int]] = []

        for item in batch:
            row = HistoryRowWidget(item, self.container_widget)
            row.deleted.connect(lambda r=row: self._on_row_deleted(r))
            row.redownload.connect(self.redownload_requested.emit)

            # Insert before stretch item
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            if item.id is not None:
                self._rendered_rows[item.id] = row
                worker_batch.append((item.id, item.file_path, item.file_missing))

        self._rendered_count = end_idx

        # Start non-blocking file check worker for this batch
        if worker_batch:
            self._file_worker = FileCheckWorker(worker_batch, parent=self)
            self._file_worker.status_updated.connect(self._on_file_status_updated)
            self._file_worker.start()

    def _on_scroll(self, value: int) -> None:
        """Trigger lazy loading when scrolling near the bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()
        if value >= scrollbar.maximum() - 150:
            self._render_next_page()

    def _on_file_status_updated(self, row_id: int, exists: bool) -> None:
        """Update row status in place when worker verifies file on disk."""
        if row_id in self._rendered_rows:
            self._rendered_rows[row_id].update_file_status(exists)

    def _on_row_deleted(self, row: HistoryRowWidget) -> None:
        """Handle single row deletion without reloading entire list."""
        if row.item in self._all_items:
            self._all_items.remove(row.item)
        if row.item.id in self._rendered_rows:
            del self._rendered_rows[row.item.id]

        self.list_layout.removeWidget(row)
        row.deleteLater()

        if not self._all_items:
            self.empty_widget.setVisible(True)
            self.scroll_area.setVisible(False)
            self.clear_all_btn.setEnabled(False)

    def _on_clear_all(self) -> None:
        """Confirm and clear entire download history."""
        dialog = ClearAllDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        deleted_count, errors = history_service.clear_all(delete_files=dialog.delete_files)
        if errors:
            err_preview = "\n".join(errors[:3])
            if len(errors) > 3:
                err_preview += f"\n...and {len(errors) - 3} more."
            QMessageBox.warning(
                self,
                "Files locked",
                f"Some files could not be deleted because they are open in another program:\n\n{err_preview}",
            )

        self.reload_history()
