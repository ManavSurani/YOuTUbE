"""AudioTab implementing state-machine control, shared DownloadManager, and clean flow.

Fixes:
  B8: Delegated to central DownloadManager (no simultaneous dual-downloads).
  B9: Format dropdown disabled when idle; empty Download click shows friendly InlineMessage.
  B15: Uses real output directory name on completion.
"""

from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
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
from app.ui.video_tab import MediaInfoCard, TabState


class AudioTab(QWidget):
    """Audio tab offering format selection, metadata/art embedding, live progress, and queue."""

    download_completed = Signal(str)  # Emits downloaded audio title

    AUDIO_FORMATS = [
        ("Best original (Opus/M4A)", "best"),
        ("MP3 (320 kbps)", "mp3"),
        ("M4A (AAC)", "m4a"),
        ("Opus", "opus"),
        ("WAV (Lossless)", "wav"),
        ("FLAC (Lossless)", "flac"),
    ]

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
        self.url_input.setPlaceholderText("Paste a YouTube link for audio extraction")
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

        # 4. Audio Options (Format Dropdown & Bitrate Note)
        opts_layout = QVBoxLayout()
        opts_layout.setSpacing(4)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.format_combo = QComboBox(container)
        self.format_combo.setFixedHeight(36)
        self.format_combo.setMinimumWidth(210)
        for label, fmt_key in self.AUDIO_FORMATS:
            self.format_combo.addItem(label, fmt_key)
        actions_row.addWidget(self.format_combo)

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
        opts_layout.addLayout(actions_row)

        # Bitrate note (shortened and muted)
        self.bitrate_note = QLabel("Opus preserves native YouTube stream without re-encoding • MP3 converted at highest quality", container)
        self.bitrate_note.setStyleSheet("font-size: 11px; color: #777777;")
        opts_layout.addWidget(self.bitrate_note)

        layout.addLayout(opts_layout)

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

        # 7. Recently Downloaded List (Audio)
        self.recent_list = RecentList(kind="audio", parent=container)
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
            self.format_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.download_btn.setVisible(True)
            self.queue_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self._is_downloading = False

        elif state == TabState.FETCHING:
            self.url_input.setEnabled(False)
            self.fetch_btn.set_loading(True)
            self.format_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.queue_btn.setVisible(False)
            self.cancel_btn.setVisible(False)

        elif state == TabState.READY:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.format_combo.setEnabled(True)
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
            self.format_combo.setEnabled(False)
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
        self.set_state(TabState.READY)

    def _on_info_failed(self, error_msg: str) -> None:
        self.inline_msg.show_error(error_msg)
        self.info_card.clear()
        self._current_info = None
        self.set_state(TabState.IDLE)

    def start_download(self) -> None:
        """Start downloading current audio or confirm duplicate."""
        job = self._build_job()
        if not job:
            return

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

        self.url_input.clear()
        self.info_card.clear()
        self._current_info = None

    def add_to_queue(self) -> None:
        """Add current audio to queue without interrupting active download."""
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
        fmt_key = self.format_combo.currentData() or "best"
        quality_label = self.format_combo.currentText() or "Best original"

        if not self._current_info:
            self._current_info = VideoInfo(
                url=cleaned,
                title="YouTube Audio",
                channel="",
                duration=0,
                duration_str="",
                thumbnail_url="",
                qualities=[],
                filesize_approx=0,
            )

        try:
            return DownloadJob.create(
                info=self._current_info,
                kind="audio",
                quality_label=quality_label,
                audio_format=fmt_key,
                output_dir=out_dir,
                thumbnail_bytes=self.info_card.thumb_bytes,
            )
        except Exception as exc:
            self.inline_msg.show_error(f"Cannot start download: {exc}")
            return None

    def _on_manager_job_started(self, job: DownloadJob) -> None:
        if job.kind == "audio":
            self.progress_card.bind_job(job)
            self.set_state(TabState.DOWNLOADING)

    def _on_manager_progress(self, job: DownloadJob, pct: float, speed: str, eta: str, done: int, total: int) -> None:
        if job.kind == "audio":
            self.progress_card.set_progress(pct, speed, eta, done, total)

    def _on_manager_stage(self, job: DownloadJob, stage_name: str) -> None:
        if job.kind == "audio":
            self.progress_card.set_stage(stage_name)

    def _on_manager_finished(self, job: DownloadJob, final_path: str) -> None:
        if job.kind == "audio":
            self.progress_card.show_done(out_dir=job.output_dir)
            self.recent_list.refresh()
            self.download_completed.emit(job.title)
            self.set_state(TabState.IDLE)

    def _on_manager_failed(self, job: DownloadJob, error_reason: str) -> None:
        if job.kind == "audio":
            self.inline_msg.show_error(f"Download failed: {error_reason}")
            self.progress_card.reset()
            self.set_state(TabState.IDLE)

    def _on_manager_cancelled(self, job: DownloadJob) -> None:
        if job.kind == "audio":
            self.progress_card.reset()
            self.set_state(TabState.IDLE)
