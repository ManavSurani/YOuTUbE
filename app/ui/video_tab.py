"""VideoTab implementing state-machine control, shared DownloadManager, and clean flow.

Fixes:
  B8: Delegated to central DownloadManager (no simultaneous dual-downloads).
  B9: Quality dropdown disabled when idle; empty Download click shows friendly InlineMessage.
  B15: Uses real output directory name on completion.
"""

from enum import Enum, auto
from pathlib import Path
from typing import Optional
import urllib.request

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.history_db import find_duplicate
from app.core.info_fetcher import InfoFetchWorker, VideoInfo
from app.core.jobs import DownloadJob
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.settings import load_settings
from app.core.url_tools import clean_url, extract_video_id, is_youtube_url
from app.ui.kit import (
    AnimatedButton,
    InlineMessage,
    ProgressCard,
)
from app.ui.queue_widget import QueueWidget
from app.ui.recent_list import RecentList


class TabState(Enum):
    IDLE = auto()
    FETCHING = auto()
    READY = auto()
    DOWNLOADING = auto()
    DONE = auto()
    OFFLINE = auto()


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
        except Exception as exc:
            get_logger().debug(f"Thumbnail load failed: {exc}")


class MediaInfoCard(QWidget):
    """Displays fetched video details (128x72 thumbnail, title, channel • duration)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.thumb_bytes: Optional[bytes] = None
        self._thumb_loader: Optional[ThumbnailLoader] = None
        self.setVisible(False)
        self._setup_ui()

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
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF;")
        text_layout.addWidget(self.title_label)

        self.meta_label = QLabel(self)
        self.meta_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
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
                target_w, target_h,
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
        self.thumb_label.clear()
        self.title_label.clear()
        self.meta_label.clear()
        self.setVisible(False)


class VideoTab(QWidget):
    """Video tab providing state-machine download controls, shared queue, and recent list."""

    download_completed = Signal(str)  # Emits downloaded video title

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._state = TabState.IDLE
        self._prev_state = TabState.IDLE
        self._current_info: Optional[VideoInfo] = None
        self._fetch_worker: Optional[InfoFetchWorker] = None
        self._last_fetched_url = ""

        # Test compatibility aliases
        self._is_downloading = False
        self._paused_for_offline = False

        self._setup_ui()
        self._wire_manager()
        self.set_state(TabState.IDLE)

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 16)
        layout.setSpacing(12)

        # 1. URL Input & Fetch Button
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.url_input = QLineEdit(container)
        self.url_input.setPlaceholderText("Paste a YouTube link")
        self.url_input.setFixedHeight(36)
        self.url_input.textChanged.connect(self._on_url_text_changed)
        input_row.addWidget(self.url_input, 1)

        self.fetch_btn = AnimatedButton("Fetch", role="secondary", parent=container)
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.clicked.connect(self.fetch_url)
        input_row.addWidget(self.fetch_btn)
        layout.addLayout(input_row)

        # 2. Inline Message (4s auto-hide)
        self.inline_msg = InlineMessage(container)
        layout.addWidget(self.inline_msg)

        # 3. Fetched Media Info Card
        self.info_card = MediaInfoCard(container)
        layout.addWidget(self.info_card)

        # 4. Action Row (Quality Combo, Download, Add to Queue, Cancel)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.quality_combo = QComboBox(container)
        self.quality_combo.setFixedHeight(36)
        self.quality_combo.setMinimumWidth(160)
        actions_row.addWidget(self.quality_combo)

        self.download_btn = AnimatedButton("Download", role="primary", parent=container)
        self.download_btn.setFixedWidth(110)
        self.download_btn.clicked.connect(self.start_download)
        actions_row.addWidget(self.download_btn)

        self.queue_btn = AnimatedButton("Add to queue", role="secondary", parent=container)
        self.queue_btn.setFixedWidth(110)
        self.queue_btn.clicked.connect(self.add_to_queue)
        actions_row.addWidget(self.queue_btn)

        self.cancel_btn = AnimatedButton("Cancel", role="secondary", parent=container)
        self.cancel_btn.setFixedWidth(90)
        self.cancel_btn.clicked.connect(self.cancel_download)
        actions_row.addWidget(self.cancel_btn)

        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        # 5. Active Progress Card
        self.progress_card = ProgressCard(container)
        layout.addWidget(self.progress_card)

        # Backward compatibility aliases for existing tests
        self.stage_label = self.progress_card.stage_label
        self.progress_bar = self.progress_card.progress_bar
        self.percent_label = self.progress_card.percent_label
        self.stats_label = self.progress_card.stats_label

        # 6. Queue Widget (Shared across Video and Audio)
        self.queue_widget = QueueWidget(container)
        layout.addWidget(self.queue_widget)

        # 7. Recently Downloaded List
        self.recent_list = RecentList(kind="video", parent=container)
        layout.addWidget(self.recent_list)

        layout.addStretch(1)
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _wire_manager(self) -> None:
        manager = get_download_manager()
        manager.job_started.connect(self._on_manager_job_started)
        manager.progress.connect(self._on_manager_progress)
        manager.stage.connect(self._on_manager_stage)
        manager.job_finished.connect(self._on_manager_finished)
        manager.job_failed.connect(self._on_manager_failed)
        manager.job_cancelled.connect(self._on_manager_cancelled)

    def set_state(self, state: TabState) -> None:
        """Drive widget visibility and enablement based on TabState."""
        self._prev_state = self._state
        self._state = state

        if state == TabState.IDLE:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.quality_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.download_btn.setVisible(True)
            self.queue_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self._is_downloading = False

        elif state == TabState.FETCHING:
            self.url_input.setEnabled(False)
            self.fetch_btn.set_loading(True)
            self.quality_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.queue_btn.setVisible(False)
            self.cancel_btn.setVisible(False)

        elif state == TabState.READY:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.quality_combo.setEnabled(True)
            self.download_btn.setEnabled(True)
            self.download_btn.setVisible(True)
            self.queue_btn.setVisible(True)
            self.queue_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self._is_downloading = False

        elif state == TabState.DOWNLOADING:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.download_btn.setVisible(False)
            self.queue_btn.setVisible(True)
            self.queue_btn.setEnabled(True)
            self.cancel_btn.setVisible(True)
            self.cancel_btn.setEnabled(True)
            self._is_downloading = True

        elif state == TabState.OFFLINE:
            self.url_input.setEnabled(False)
            self.fetch_btn.setEnabled(False)
            self.quality_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.queue_btn.setEnabled(False)
            if self._prev_state == TabState.DOWNLOADING:
                self.progress_card.set_stage("Waiting for internet…")
                self.cancel_btn.setEnabled(True)
            else:
                self.cancel_btn.setEnabled(False)

    def set_online(self, online: bool) -> None:
        """Handle network status change."""
        if not online:
            self._paused_for_offline = (self._state == TabState.DOWNLOADING)
            self.set_state(TabState.OFFLINE)
        else:
            self._paused_for_offline = False
            # Restore state before offline
            target_state = self._prev_state if self._prev_state != TabState.OFFLINE else (
                TabState.READY if self._current_info else TabState.IDLE
            )
            self.set_state(target_state)

    def _on_url_text_changed(self, text: str) -> None:
        clean = text.strip()
        if clean and is_youtube_url(clean) and clean != self._last_fetched_url:
            self.fetch_url()
        elif not clean:
            self.info_card.clear()
            self._current_info = None
            self.quality_combo.clear()
            self.set_state(TabState.IDLE)

    def fetch_url(self) -> None:
        """Fetch video metadata from YouTube via InfoFetchWorker."""
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self.inline_msg.show_error("Please paste a valid YouTube link.")
            return

        self._last_fetched_url = cleaned
        self.set_state(TabState.FETCHING)

        self._fetch_worker = InfoFetchWorker(cleaned, parent=self)
        self._fetch_worker.fetched.connect(self._on_info_fetched)
        self._fetch_worker.failed.connect(self._on_info_failed)
        self._fetch_worker.start()

    def _on_info_fetched(self, info: VideoInfo) -> None:
        self._current_info = info
        self.info_card.set_info(info)

        # Populate quality dropdown (real resolutions descending, 'Best available' first)
        self.quality_combo.clear()
        for label, height in info.qualities:
            self.quality_combo.addItem(label, height)

        self.set_state(TabState.READY)

    def _on_info_failed(self, error_msg: str) -> None:
        self.inline_msg.show_error(error_msg)
        self.info_card.clear()
        self._current_info = None
        self.set_state(TabState.IDLE)

    def start_download(self) -> None:
        """Start downloading current video or confirm duplicate."""
        job = self._build_job()
        if not job:
            return

        # Duplicate check (Chunk 4.3)
        dup = find_duplicate(job.video_id, job.kind, job.quality_label)
        if dup:
            reply = QMessageBox.question(
                self,
                "Already Downloaded",
                f"'{job.title}' ({job.quality_label}) has already been downloaded.\nDownload again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        manager = get_download_manager()
        manager.enqueue(job)

        # Clear inputs for next paste
        self.url_input.clear()
        self.info_card.clear()
        self._current_info = None

    def add_to_queue(self) -> None:
        """Add current video to queue without interrupting active download."""
        job = self._build_job()
        if not job:
            return

        manager = get_download_manager()
        manager.enqueue(job)

        self.url_input.clear()
        self.info_card.clear()
        self._current_info = None
        self.set_state(TabState.DOWNLOADING if manager.active_job else TabState.IDLE)

    def cancel_download(self) -> None:
        """Cancel active download."""
        manager = get_download_manager()
        manager.cancel_active()
        self.progress_card.set_stage("Cancelled.")
        self.set_state(TabState.IDLE)

    def _build_job(self) -> Optional[DownloadJob]:
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self.inline_msg.show_error("Please paste a valid YouTube link.")
            return None

        settings = load_settings()
        out_dir = settings.get("download_dir", str(DEFAULT_DOWNLOADS))
        chosen_height = self.quality_combo.currentData()
        quality_label = self.quality_combo.currentText() or "Best"

        if not self._current_info:
            # Fallback: create temporary info if info card wasn't fetched
            self._current_info = VideoInfo(
                url=cleaned,
                title="YouTube Video",
                channel="",
                duration=0,
                duration_str="",
                thumbnail_url="",
                qualities=[("Best", None)],
                filesize_approx=0,
            )

        try:
            return DownloadJob.create(
                info=self._current_info,
                kind="video",
                quality_label=quality_label,
                height=chosen_height,
                output_dir=out_dir,
                thumbnail_bytes=self.info_card.thumb_bytes,
            )
        except Exception as exc:
            self.inline_msg.show_error(f"Cannot start download: {exc}")
            return None

    def _on_manager_job_started(self, job: DownloadJob) -> None:
        if job.kind == "video":
            self.progress_card.bind_job(job)
            self.set_state(TabState.DOWNLOADING)

    def _on_manager_progress(self, job: DownloadJob, pct: float, speed: str, eta: str, done: int, total: int) -> None:
        if job.kind == "video":
            self.progress_card.set_progress(pct, speed, eta, done, total)

    def _on_manager_stage(self, job: DownloadJob, stage_name: str) -> None:
        if job.kind == "video":
            self.progress_card.set_stage(stage_name)

    def _on_manager_finished(self, job: DownloadJob, final_path: str) -> None:
        if job.kind == "video":
            self.progress_card.show_done(out_dir=job.output_dir)
            self.recent_list.refresh()
            self.download_completed.emit(job.title)
            # Reset tab state
            self.set_state(TabState.IDLE)

    def _on_manager_failed(self, job: DownloadJob, error_reason: str) -> None:
        if job.kind == "video":
            self.inline_msg.show_error(f"Download failed: {error_reason}")
            self.progress_card.reset()
            self.set_state(TabState.IDLE)

    def _on_manager_cancelled(self, job: DownloadJob) -> None:
        if job.kind == "video":
            self.progress_card.reset()
            self.set_state(TabState.IDLE)
