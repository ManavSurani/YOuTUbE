"""Video download tab implementation with auto-fetch, dynamic quality, queue, and plain errors."""

import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.downloader import DownloadWorker, build_video_cmd
from app.core.errors import explain
from app.core.history_db import HistoryItem, add_item
from app.core.history_service import save_from_job
from app.core.jobs import DownloadJob
from app.core.info_fetcher import InfoFetchWorker, VideoInfo
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.settings import load_settings
from app.core.url_tools import clean_url, extract_video_id, is_youtube_url


@dataclass
class VideoQueueItem:
    """An item waiting in or processed by the video queue."""

    url: str
    title: str
    height: Optional[int]
    quality_label: str
    status: str = "waiting"  # "waiting", "downloading", "done", "failed", "cancelled"
    error_reason: str = ""
    job: Optional[DownloadJob] = None


class ThumbnailLoader(QThread):
    """Background loader for video thumbnail fetching raw image bytes."""

    loaded = Signal(bytes)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            self.loaded.emit(data)
        except Exception:
            pass


class MediaInfoCard(QWidget):
    """Shared widget displaying video thumbnail, title, and metadata."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._thumb_loader: Optional[ThumbnailLoader] = None
        self.thumb_bytes: Optional[bytes] = None
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(128, 72)
        layout.addWidget(self.thumb_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(self)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        text_layout.addWidget(self.title_label)

        self.meta_label = QLabel(self)
        self.meta_label.setProperty("role", "muted")
        text_layout.addWidget(self.meta_label)

        layout.addLayout(text_layout, 1)

    def set_info(self, info: VideoInfo) -> None:
        self.title_label.setText(info.title)
        meta_parts = []
        if info.channel:
            meta_parts.append(info.channel)
        if info.duration_str:
            meta_parts.append(info.duration_str)
        self.meta_label.setText(" • ".join(meta_parts))

        # Clear existing thumbnail
        self.thumb_label.clear()
        if info.thumbnail_url:
            self._thumb_loader = ThumbnailLoader(info.thumbnail_url, self)
            self._thumb_loader.loaded.connect(self._on_thumbnail_loaded)
            self._thumb_loader.start()

        self.setVisible(True)

    def _on_thumbnail_loaded(self, data: bytes) -> None:
        pix = QPixmap()
        if pix.loadFromData(data):
            target_w, target_h = 128, 72
            scaled = pix.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = max(0, (scaled.width() - target_w) // 2)
            y = max(0, (scaled.height() - target_h) // 2)
            cropped = scaled.copy(x, y, target_w, target_h)

            rounded = QPixmap(target_w, target_h)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, target_w, target_h, 8, 8)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.end()

            self.thumb_bytes = data
            self.thumb_label.setPixmap(rounded)

    def clear(self) -> None:
        self.thumb_bytes = None
        self.title_label.setText("")
        self.meta_label.setText("")
        self.thumb_label.clear()
        self.setVisible(False)


def check_free_space(out_dir: Path | str, needed_bytes: int) -> Tuple[bool, str]:
    """Check if destination folder has enough disk space."""
    if needed_bytes <= 0:
        return True, ""
    try:
        free_bytes = shutil.disk_usage(str(out_dir)).free
        if free_bytes < needed_bytes:
            return False, explain("", free_bytes=free_bytes, needed_bytes=needed_bytes)
    except Exception:
        pass
    return True, ""


class VideoTab(QWidget):
    """Complete Video download tab with queue, plain-language error reporting, and pause/resume."""

    download_completed = Signal(str)  # Emits downloaded video title

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_info: Optional[VideoInfo] = None
        self._fetch_worker: Optional[InfoFetchWorker] = None
        self._download_worker: Optional[DownloadWorker] = None
        self._last_fetched_url = ""
        self._last_raw_error = ""

        # Network and download state
        self._is_offline = False
        self._is_downloading = False
        self._paused_for_offline = False
        self._saved_cmd: List[str] = []
        self._saved_out_dir = ""

        # Queue tracking
        self._queue: List[VideoQueueItem] = []
        self._active_item: Optional[VideoQueueItem] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        # Input row: URL box + Fetch button
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Paste a YouTube link")
        self.url_input.setFixedHeight(36)
        self.url_input.textChanged.connect(self._on_url_changed)
        self.url_input.returnPressed.connect(self.fetch_url)
        input_row.addWidget(self.url_input)

        self.fetch_btn = QPushButton("Fetch", self)
        self.fetch_btn.setProperty("role", "secondary")
        self.fetch_btn.setFixedHeight(36)
        self.fetch_btn.clicked.connect(self.fetch_url)
        input_row.addWidget(self.fetch_btn)

        layout.addLayout(input_row)

        # Status / Error row with "Copy error details" text button
        error_row = QHBoxLayout()
        error_row.setSpacing(8)

        self.error_label = QLabel(self)
        self.error_label.setProperty("role", "error")
        self.error_label.setVisible(False)
        error_row.addWidget(self.error_label)

        self.copy_err_btn = QPushButton("Copy error details", self)
        self.copy_err_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #AAAAAA; font-size: 11px; text-decoration: underline; padding: 0px 4px; } "
            "QPushButton:hover { color: #FFFFFF; }"
        )
        self.copy_err_btn.setVisible(False)
        self.copy_err_btn.clicked.connect(self._on_copy_error_details)
        error_row.addWidget(self.copy_err_btn)

        error_row.addStretch(1)
        layout.addLayout(error_row)

        # Video metadata card (thumbnail, title, channel • duration)
        self.info_card = MediaInfoCard(self)
        layout.addWidget(self.info_card)

        # Quality dropdown, Download, Add to queue, and Cancel buttons
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(8)

        self.quality_combo = QComboBox(self)
        self.quality_combo.setFixedHeight(36)
        self.quality_combo.setMinimumWidth(180)
        self.quality_combo.addItem("Best available", None)
        self.action_row.addWidget(self.quality_combo)

        self.download_btn = QPushButton("Download", self)
        self.download_btn.setProperty("role", "primary")
        self.download_btn.setFixedHeight(36)
        self.download_btn.clicked.connect(self.start_download)
        self.action_row.addWidget(self.download_btn)

        self.queue_btn = QPushButton("Add to queue", self)
        self.queue_btn.setProperty("role", "secondary")
        self.queue_btn.setFixedHeight(36)
        self.queue_btn.clicked.connect(self.add_to_queue)
        self.action_row.addWidget(self.queue_btn)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setProperty("role", "secondary")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.action_row.addWidget(self.cancel_btn)

        self.action_row.addStretch(1)
        layout.addLayout(self.action_row)

        # Stage label
        self.stage_label = QLabel(self)
        self.stage_label.setProperty("role", "muted")
        layout.addWidget(self.stage_label)

        # Progress bar row with percent label
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_row.addWidget(self.progress_bar)

        self.percent_label = QLabel("0%", self)
        self.percent_label.setProperty("role", "muted")
        self.percent_label.setFixedWidth(45)
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.percent_label)

        layout.addLayout(progress_row)

        # Stats label (speed • ETA • size)
        self.stats_label = QLabel(self)
        self.stats_label.setProperty("role", "muted")
        layout.addWidget(self.stats_label)

        # Queue list area
        self.queue_container = QWidget(self)
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 4, 0, 0)
        self.queue_layout.setSpacing(6)
        self.queue_container.setVisible(False)
        layout.addWidget(self.queue_container)

        layout.addStretch(1)

    def _on_url_changed(self, text: str) -> None:
        cleaned = clean_url(text.strip())
        if cleaned and cleaned != self._last_fetched_url:
            self.fetch_url()

    def fetch_url(self) -> None:
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self._set_error("Please paste a valid YouTube link.")
            return

        self._last_fetched_url = cleaned
        self._clear_error()
        self.stage_label.setText("Fetching video information…")
        self.fetch_btn.setEnabled(False)

        self.info_card.clear()
        self.quality_combo.clear()
        self.quality_combo.addItem("Best available", None)

        self._fetch_worker = InfoFetchWorker(cleaned, parent=self)
        self._fetch_worker.fetched.connect(self._on_info_fetched)
        self._fetch_worker.failed.connect(self._on_info_failed)
        self._fetch_worker.start()

    def _on_info_fetched(self, info: VideoInfo) -> None:
        self.fetch_btn.setEnabled(not self._is_offline)
        self.stage_label.setText("")
        self._current_info = info
        self.info_card.set_info(info)

        self.quality_combo.clear()
        for label, height_val in info.qualities:
            self.quality_combo.addItem(label, height_val)

    def _on_info_failed(self, error_msg: str) -> None:
        self.fetch_btn.setEnabled(not self._is_offline)
        self.stage_label.setText("")
        self._last_raw_error = error_msg
        self._set_error(explain(error_msg), raw=error_msg)

    def _set_error(self, message: str, raw: str = "") -> None:
        self._last_raw_error = raw or message
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.copy_err_btn.setText("Copy error details")
        self.copy_err_btn.setVisible(bool(raw))

    def _clear_error(self) -> None:
        self.error_label.setVisible(False)
        self.copy_err_btn.setVisible(False)

    def _on_copy_error_details(self) -> None:
        if self._last_raw_error:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(self._last_raw_error)
            self.copy_err_btn.setText("Copied!")

    def set_online(self, is_online: bool) -> None:
        self._is_offline = not is_online
        if not is_online:
            self.url_input.setEnabled(False)
            self.fetch_btn.setEnabled(False)
            self.quality_combo.setEnabled(False)
            self.queue_btn.setEnabled(False)
            if self._is_downloading:
                self._paused_for_offline = True
                if self._download_worker and self._download_worker.isRunning():
                    self._download_worker.pause()
                self.stage_label.setText("Waiting for internet…")
                self.stats_label.setText("")
                self.download_btn.setEnabled(False)
                self.cancel_btn.setEnabled(True)
            else:
                self.download_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
        else:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.quality_combo.setEnabled(True)
            self.queue_btn.setEnabled(True)
            if self._paused_for_offline and self._saved_cmd:
                self._paused_for_offline = False
                self.stage_label.setText("Resuming download…")
                self.download_btn.setEnabled(False)
                self.cancel_btn.setEnabled(True)
                self._start_worker(initial_percent=float(self.progress_bar.value()))
            elif not self._is_downloading:
                self.download_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)

    def start_download(self) -> None:
        if self._is_offline:
            return

        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self._set_error("Please paste a valid YouTube link.")
            return

        # Add to queue and trigger queue execution
        self._enqueue_item(cleaned)
        if not self._is_downloading:
            self._process_queue()

    def add_to_queue(self) -> None:
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self._set_error("Please paste a valid YouTube link.")
            return

        self._enqueue_item(cleaned)
        # Clear inputs so user can paste next link
        self.url_input.clear()
        self.info_card.clear()
        self._current_info = None

        if not self._is_downloading and not self._is_offline:
            self._process_queue()

    def _enqueue_item(self, url: str) -> None:
        title = self._current_info.title if self._current_info else url
        chosen_height = self.quality_combo.currentData()
        quality_label = self.quality_combo.currentText()
        settings = load_settings()
        out_dir = settings.get("download_dir", str(DEFAULT_DOWNLOADS))

        job = None
        if self._current_info:
            try:
                job = DownloadJob.create(
                    info=self._current_info,
                    kind="video",
                    quality_label=quality_label,
                    height=chosen_height,
                    output_dir=out_dir,
                    thumbnail_bytes=self.info_card.thumb_bytes,
                )
            except Exception as exc:
                get_logger().warning(f"Could not build DownloadJob snapshot: {exc}")

        item = VideoQueueItem(
            url=url,
            title=title,
            height=chosen_height,
            quality_label=quality_label,
            status="waiting",
            job=job,
        )
        self._queue.append(item)
        self._render_queue_ui()

    def _render_queue_ui(self) -> None:
        # Clear existing items in layout
        while self.queue_layout.count() > 0:
            child = self.queue_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._queue:
            self.queue_container.setVisible(False)
            return

        self.queue_container.setVisible(True)
        waiting_count = sum(1 for it in self._queue if it.status == "waiting")

        header = QLabel(f"Queue ({waiting_count} waiting)", self.queue_container)
        header.setStyleSheet("font-size: 13px; font-weight: 600; color: #AAAAAA;")
        self.queue_layout.addWidget(header)

        for idx, item in enumerate(self._queue):
            row = QWidget(self.queue_container)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)
            row.setStyleSheet("background-color: #1A1A1A; border-radius: 6px;")

            title_lbl = QLabel(f"{item.title} ({item.quality_label})", row)
            title_lbl.setStyleSheet("font-size: 12px; color: #FFFFFF;")
            row_layout.addWidget(title_lbl, 1)

            status_lbl = QLabel(row)
            if item.status == "waiting":
                status_lbl.setText("Waiting")
                status_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            elif item.status == "downloading":
                status_lbl.setText("Downloading…")
                status_lbl.setStyleSheet("color: #3EA6FF; font-size: 11px; font-weight: 600;")
            elif item.status == "done":
                status_lbl.setText("Done")
                status_lbl.setStyleSheet("color: #2BA640; font-size: 11px;")
            elif item.status == "failed":
                status_lbl.setText(f"Failed: {item.error_reason}")
                status_lbl.setStyleSheet("color: #CC0000; font-size: 11px;")
            elif item.status == "cancelled":
                status_lbl.setText("Cancelled")
                status_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px;")

            row_layout.addWidget(status_lbl)

            if item.status == "waiting":
                remove_btn = QPushButton("Remove", row)
                remove_btn.setStyleSheet(
                    "QPushButton { border: none; background: transparent; color: #888888; font-size: 11px; padding: 2px 6px; } "
                    "QPushButton:hover { color: #CC0000; }"
                )
                # Capture item in closure
                remove_btn.clicked.connect(lambda _, it=item: self._remove_queue_item(it))
                row_layout.addWidget(remove_btn)

            self.queue_layout.addWidget(row)

    def _remove_queue_item(self, item: VideoQueueItem) -> None:
        if item in self._queue and item.status == "waiting":
            self._queue.remove(item)
            self._render_queue_ui()

    def _process_queue(self) -> None:
        if self._is_offline:
            return

        next_item = next((it for it in self._queue if it.status == "waiting"), None)
        if not next_item:
            self._is_downloading = False
            self._active_item = None
            self._reset_buttons()
            return

        self._active_item = next_item
        next_item.status = "downloading"
        self._render_queue_ui()

        settings = load_settings()
        out_dir = settings.get("download_dir")
        import uuid
        job_id = str(uuid.uuid4())
        cmd = build_video_cmd(next_item.url, height=next_item.height, out_dir=out_dir, job_id=job_id)
        self._saved_job_id = job_id
        self._saved_cmd = cmd
        self._saved_out_dir = out_dir
        self._is_downloading = True
        self._paused_for_offline = False

        self._clear_error()
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.stage_label.setText(f"Starting {next_item.title}…")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.stats_label.setText("")

        self._start_worker(initial_percent=0.0)

    def _start_worker(self, initial_percent: float = 0.0) -> None:
        video_id = getattr(self, "_current_video_id", "")
        job_id = getattr(self, "_saved_job_id", None)
        self._download_worker = DownloadWorker(
            self._saved_cmd,
            out_dir=self._saved_out_dir,
            job_id=job_id,
            video_id=video_id,
            is_dual_stream=True,
            parent=self,
        )
        self._download_worker.stage.connect(self._on_stage)
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.finished.connect(self._on_finished)
        self._download_worker.failed.connect(self._on_failed)
        self._download_worker.start()

    def cancel_download(self) -> None:
        if self._download_worker:
            self._download_worker.cancel()

        self._is_downloading = False
        self._paused_for_offline = False
        if self._active_item:
            self._active_item.status = "cancelled"
            self._active_item = None

        self.stage_label.setText("Cancelled.")
        self.stats_label.setText("")
        self._render_queue_ui()
        self._reset_buttons()
        # Cancelling stops the queue from automatically continuing

    def _on_stage(self, stage_text: str) -> None:
        self.stage_label.setText(stage_text)

    def _on_progress(self, percent: float, speed: str, eta: str, done_bytes: int, total_bytes: int) -> None:
        pct_int = int(percent)
        self.progress_bar.setValue(pct_int)
        self.percent_label.setText(f"{pct_int}%")

        def _fmt_bytes(b: int) -> str:
            if b <= 0:
                return ""
            for unit in ("B", "KB", "MB", "GB"):
                if b < 1024:
                    return f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} TB"

        details = []
        if speed:
            details.append(speed)
        if eta:
            details.append(f"ETA {eta}")
        done_s = _fmt_bytes(done_bytes)
        total_s = _fmt_bytes(total_bytes)
        if done_s and total_s:
            details.append(f"{done_s} / {total_s}")
        elif done_s:
            details.append(done_s)

        self.stats_label.setText(" • ".join(details))

    def _on_finished(self, file_path: str) -> None:
        self._is_downloading = False
        self._paused_for_offline = False
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.stage_label.setText("Done. Saved to Downloads.")
        self.stats_label.setText("")

        title_saved = self._active_item.title if self._active_item else "video"
        if self._active_item:
            self._active_item.status = "done"
            title_saved = self._active_item.title
            self._render_queue_ui()

        if file_path:
            logger = get_logger()
            if self._active_item and self._active_item.job:
                try:
                    save_from_job(self._active_item.job, file_path)
                except Exception as exc:
                    logger.error(f"Failed to save history from job: {exc}")
            else:
                try:
                    real_path = Path(file_path)
                    size_bytes = real_path.stat().st_size if real_path.is_file() else 0
                    fallback_url = self._active_item.url if self._active_item else ""
                    vid_id = extract_video_id(fallback_url) or ""
                    add_item(
                        HistoryItem(
                            id=None,
                            title=title_saved,
                            url=fallback_url,
                            type="video",
                            quality=self._active_item.quality_label if self._active_item else "Best",
                            file_path=str(file_path),
                            size_bytes=size_bytes,
                            duration=0,
                            video_id=vid_id,
                        )
                    )
                except Exception as exc:
                    logger.error(f"Failed to save fallback history item: {exc}")

        self.download_completed.emit(title_saved)

        # Move to next queued item automatically
        self._process_queue()

    def _on_failed(self, raw_text: str) -> None:
        if self._paused_for_offline:
            return

        self._is_downloading = False
        self._paused_for_offline = False
        reason = explain(raw_text)

        if self._active_item:
            self._active_item.status = "failed"
            self._active_item.error_reason = reason
            self._render_queue_ui()

        self.stage_label.setText("Download failed.")
        self._set_error(reason, raw=raw_text)

        # Automatically advance queue so other items still finish
        self._process_queue()

    def _reset_buttons(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.download_btn.setEnabled(not self._is_offline)
        self.queue_btn.setEnabled(not self._is_offline)
