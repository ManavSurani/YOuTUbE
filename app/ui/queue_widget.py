"""Queue list widget displaying active, waiting, and failed download jobs.

Fixes B5 (titles always come from job snapshots, never URLs).
Provides cancel/remove buttons and retry for failed items.
"""

from typing import Optional, Tuple, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.jobs import DownloadJob
from app.core.logger import get_logger
from app.ui.kit.buttons import AnimatedButton, IconButton
from app.ui.kit.progress_card import ModernProgressBar
from app.ui.kit.thumb_label import ThumbLabel


class QueueRow(QWidget):
    """A row representing an active, waiting, or failed item in the queue."""

    def __init__(
        self,
        job: Union[DownloadJob, Tuple[DownloadJob, str]],
        status_text: Optional[str] = None,
        status_color: Optional[str] = None,
        can_remove: bool = False,
        can_retry: bool = False,
        parent: Optional[QWidget] = None,
        failure_reason: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        if isinstance(job, tuple):
            job_item, reason = job
            self.job = job_item
            failure_reason = reason
            can_retry = True
            can_remove = True
        else:
            self.job = job

        target_job = self.job
        manager = get_download_manager(target_job.kind)

        deferred_ids = set()
        if hasattr(manager, "deferred_job_ids"):
            try:
                deferred_ids = manager.deferred_job_ids()
            except Exception:
                deferred_ids = set()

        if can_retry or failure_reason is not None:
            cleaned_reason = failure_reason.strip() if (failure_reason and isinstance(failure_reason, str)) else ""
            display_reason = cleaned_reason if cleaned_reason else "Something went wrong"
            status_text = f"Failed: {display_reason}"
            status_color = status_color or "#FF4E45"
        elif status_text is None:
            if target_job.job_id in deferred_ids:
                status_text = "Waiting for the same video to finish"
            else:
                status_text = "Waiting"
            status_color = status_color or "#AAAAAA"
        else:
            if status_text == "Waiting" and target_job.job_id in deferred_ids:
                status_text = "Waiting for the same video to finish"
            status_color = status_color or ("#FF4E45" if "Failed" in status_text else "#AAAAAA")

        self.setFixedHeight(58)
        self.setStyleSheet("QueueRow { background-color: #1A1A1A; border-radius: 6px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Thumbnail
        is_audio = (target_job.kind == "audio")
        self.thumb = ThumbLabel(video_id=target_job.video_id, is_audio=is_audio, size=(54, 30), radius=4, parent=self)
        layout.addWidget(self.thumb)

        # Title, format, and 6px progress bar
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        title_lbl = QLabel(target_job.title, self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        info_layout.addWidget(title_lbl)

        meta_lbl = QLabel(f"{target_job.kind.capitalize()} • {target_job.quality_label}", self)
        meta_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        info_layout.addWidget(meta_lbl)

        self.progress_bar = ModernProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        info_layout.addWidget(self.progress_bar)

        layout.addLayout(info_layout, 1)

        # Status text
        self.status_lbl = QLabel(status_text, self)
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {status_color};")
        layout.addWidget(self.status_lbl)

        # Action buttons (Retry and/or Remove)
        self.retry_btn = None
        if can_retry:
            self.retry_btn = IconButton("redownload", size=28, tooltip="Retry", parent=self)
            self.retry_btn.clicked.connect(lambda: manager.retry_job(target_job.job_id))
            layout.addWidget(self.retry_btn)

        self.remove_btn = None
        if can_remove:
            self.remove_btn = IconButton("close", is_danger=True, size=28, tooltip="Remove", parent=self)
            self.remove_btn.clicked.connect(lambda: manager.cancel_job(target_job.job_id))
            layout.addWidget(self.remove_btn)


class QueueWidget(QWidget):
    """Container displaying the download queue for a specific lane."""

    def __init__(self, kind: str = "video", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind.lower()
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(6)

        self.manager = get_download_manager(self.kind)
        # Connect strictly ONCE here. Do NOT connect inside refresh() or to progress.
        self.manager.queue_changed.connect(self.refresh)

        self.refresh()

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

    def refresh(self) -> None:
        """Re-render queue items according to DownloadManager state."""
        self._clear_layout(self._layout)

        waiting_lane = []
        for job in self.manager.waiting_jobs:
            if job.kind != self.kind:
                get_logger().warning(
                    f"Skipping wrong-kind waiting job {job.job_id} ({job.kind}) in {self.kind} queue"
                )
                continue
            waiting_lane.append(job)

        failed_lane = []
        for item in self.manager.failed_jobs:
            if isinstance(item, tuple):
                job, reason = item
            else:
                job, reason = item, ""
            if job.kind != self.kind:
                get_logger().warning(
                    f"Skipping wrong-kind failed job {job.job_id} ({job.kind}) in {self.kind} queue"
                )
                continue
            failed_lane.append((job, reason))

        drawn_count = len(waiting_lane) + len(failed_lane)
        if drawn_count == 0:
            self.setVisible(False)
            return

        self.setVisible(True)

        # Header: "Up next (N)"
        header_layout = QHBoxLayout()
        header_lbl = QLabel(f"Up next ({drawn_count})", self)
        header_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #AAAAAA;")
        header_layout.addWidget(header_lbl, 1)

        if failed_lane:
            clear_btn = AnimatedButton("Clear failed", role="ghost", parent=self)
            clear_btn.clicked.connect(self._clear_failed)
            header_layout.addWidget(clear_btn)

        self._layout.addLayout(header_layout)

        # 1. Waiting items
        for job in waiting_lane:
            row = QueueRow(
                job=job,
                can_remove=True,
                can_retry=False,
                parent=self,
            )
            self._layout.addWidget(row)

        # 2. Failed items
        for job, reason in failed_lane:
            row = QueueRow(
                job=job,
                can_remove=True,
                can_retry=True,
                failure_reason=reason,
                parent=self,
            )
            self._layout.addWidget(row)

    def _clear_failed(self) -> None:
        if hasattr(self.manager, "clear_failed"):
            self.manager.clear_failed()
        elif hasattr(self.manager, "_failed_jobs"):
            self.manager._failed_jobs.clear()
            self.manager.queue_changed.emit()
