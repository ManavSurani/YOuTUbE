"""Queue list widget displaying active, waiting, and failed download jobs.

Fixes B5 (titles always come from job snapshots, never URLs).
Provides cancel/remove buttons and retry for failed items.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.jobs import DownloadJob
from app.ui.kit.thumb_label import ThumbLabel


class QueueRow(QWidget):
    """A row representing an active, waiting, or failed item in the queue."""

    def __init__(
        self,
        job: DownloadJob,
        status_text: str,
        status_color: str = "#AAAAAA",
        can_remove: bool = False,
        can_retry: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.job = job
        self.setFixedHeight(52)
        self.setStyleSheet("QueueRow { background-color: #1A1A1A; border-radius: 6px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Thumbnail
        is_audio = (job.kind == "audio")
        self.thumb = ThumbLabel(video_id=job.video_id, is_audio=is_audio, size=(54, 30), radius=4, parent=self)
        layout.addWidget(self.thumb)

        # Title & format
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        title_lbl = QLabel(job.title, self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        info_layout.addWidget(title_lbl)

        meta_lbl = QLabel(f"{job.kind.capitalize()} • {job.quality_label}", self)
        meta_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        info_layout.addWidget(meta_lbl)

        layout.addLayout(info_layout, 1)

        # Status text
        self.status_lbl = QLabel(status_text, self)
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {status_color};")
        layout.addWidget(self.status_lbl)

        # Action button (Remove or Retry)
        manager = get_download_manager()

        if can_retry:
            retry_btn = QPushButton("Retry", self)
            retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            retry_btn.setStyleSheet(
                "QPushButton { background: #333333; color: #3EA6FF; border-radius: 4px; padding: 4px 8px; font-size: 11px; } "
                "QPushButton:hover { background: #444444; }"
            )
            retry_btn.clicked.connect(lambda: manager.retry_job(job.job_id))
            layout.addWidget(retry_btn)

        if can_remove:
            remove_btn = QPushButton("✕", self)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setFixedSize(24, 24)
            remove_btn.setStyleSheet(
                "QPushButton { background: transparent; color: #888888; border: none; font-size: 12px; } "
                "QPushButton:hover { color: #FF4E45; }"
            )
            remove_btn.clicked.connect(lambda: manager.cancel_job(job.job_id))
            layout.addWidget(remove_btn)


class QueueWidget(QWidget):
    """Container displaying the shared download queue."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(6)

        manager = get_download_manager()
        manager.queue_changed.connect(self.refresh)
        manager.progress.connect(self._on_progress)
        manager.stage.connect(self._on_stage)

        self.refresh()

    def refresh(self) -> None:
        """Re-render queue items according to DownloadManager state."""
        # Clear layout
        while self._layout.count() > 0:
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        manager = get_download_manager()
        active = manager.active_job
        waiting = manager.waiting_jobs
        failed = manager.failed_jobs
        completed = manager.completed_jobs

        total_pending = (1 if active else 0) + len(waiting) + len(failed)
        if total_pending == 0 and not completed:
            self.setVisible(False)
            return

        self.setVisible(True)

        # Header: "Up next (N)"
        header_layout = QHBoxLayout()
        header_lbl = QLabel(f"Up next ({len(waiting)})" if waiting else "Queue", self)
        header_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #AAAAAA;")
        header_layout.addWidget(header_lbl, 1)

        if completed:
            clear_btn = QPushButton("Clear finished", self)
            clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; font-size: 12px; color: #888888; } "
                "QPushButton:hover { color: #FFFFFF; text-decoration: underline; }"
            )
            clear_btn.clicked.connect(manager.clear_finished)
            header_layout.addWidget(clear_btn)

        self._layout.addLayout(header_layout)

        # 1. Active item
        if active:
            self._active_row = QueueRow(
                job=active,
                status_text="Downloading…",
                status_color="#3EA6FF",
                can_remove=False,
                can_retry=False,
                parent=self,
            )
            self._layout.addWidget(self._active_row)

        # 2. Waiting items
        for job in waiting:
            row = QueueRow(
                job=job,
                status_text="Waiting",
                status_color="#AAAAAA",
                can_remove=True,
                can_retry=False,
                parent=self,
            )
            self._layout.addWidget(row)

        # 3. Failed items
        for job, reason in failed:
            row = QueueRow(
                job=job,
                status_text=f"Failed: {reason}",
                status_color="#FF4E45",
                can_remove=True,
                can_retry=True,
                parent=self,
            )
            self._layout.addWidget(row)

    def _on_progress(self, job: DownloadJob, pct: float, speed: str, eta: str, done: int, total: int) -> None:
        if hasattr(self, "_active_row") and self._active_row and self._active_row.job.job_id == job.job_id:
            pct_int = int(pct)
            self._active_row.status_lbl.setText(f"{pct_int}%")

    def _on_stage(self, job: DownloadJob, stage_name: str) -> None:
        if hasattr(self, "_active_row") and self._active_row and self._active_row.job.job_id == job.job_id:
            self._active_row.status_lbl.setText(stage_name)
