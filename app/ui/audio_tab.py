"""Audio download tab implementation with format selection, queue, and plain errors."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.downloader import DownloadWorker, build_audio_cmd
from app.core.errors import explain
from app.core.history_db import HistoryItem, add_item
from app.core.history_service import save_from_job
from app.core.jobs import DownloadJob
from app.core.info_fetcher import InfoFetchWorker, VideoInfo
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.settings import load_settings
from app.core.url_tools import clean_url, extract_video_id
from app.ui.video_tab import MediaInfoCard, check_free_space


@dataclass
class AudioQueueItem:
    """An item waiting in or processed by the audio queue."""

    url: str
    title: str
    fmt: str
    fmt_label: str
    embed_art: bool
    embed_meta: bool
    status: str = "waiting"  # "waiting", "downloading", "done", "failed", "cancelled"
    error_reason: str = ""
    job: Optional[DownloadJob] = None


class AudioTab(QWidget):
    """Audio tab offering format selection, metadata/art embedding, live progress, and queue."""

    download_completed = Signal(str)  # Emits downloaded audio title

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
        self._queue: List[AudioQueueItem] = []
        self._active_item: Optional[AudioQueueItem] = None

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

        # Reusable media card
        self.info_card = MediaInfoCard(self)
        layout.addWidget(self.info_card)

        # Audio format dropdown, Download, Add to queue, and Cancel buttons row
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(8)

        self.format_combo = QComboBox(self)
        self.format_combo.setFixedHeight(36)
        self.format_combo.setMinimumWidth(180)
        audio_formats = [
            ("Best original", "best"),
            ("MP3", "mp3"),
            ("M4A", "m4a"),
            ("Opus", "opus"),
            ("WAV", "wav"),
            ("FLAC", "flac"),
        ]
        for label, fmt in audio_formats:
            self.format_combo.addItem(label, fmt)
        self.action_row.addWidget(self.format_combo)

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

        # Embedding options row
        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        self.embed_cover_check = QCheckBox("Embed cover art", self)
        self.embed_cover_check.setChecked(True)
        options_row.addWidget(self.embed_cover_check)

        self.embed_meta_check = QCheckBox("Embed metadata", self)
        self.embed_meta_check.setChecked(True)
        options_row.addWidget(self.embed_meta_check)

        options_row.addStretch(1)
        layout.addLayout(options_row)

        # Informational note regarding YouTube audio bitrates
        self.note_label = QLabel(
            "YouTube audio is about 128 to 160 kbps. Converting to MP3 cannot improve it.", self
        )
        self.note_label.setProperty("role", "muted")
        layout.addWidget(self.note_label)

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

        # Stats label
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

        self._fetch_worker = InfoFetchWorker(cleaned, parent=self)
        self._fetch_worker.fetched.connect(self._on_info_fetched)
        self._fetch_worker.failed.connect(self._on_info_failed)
        self._fetch_worker.start()

    def _on_info_fetched(self, info: VideoInfo) -> None:
        self.fetch_btn.setEnabled(not self._is_offline)
        self.stage_label.setText("")
        self._current_info = info
        self.info_card.set_info(info)

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
            self.format_combo.setEnabled(False)
            self.embed_cover_check.setEnabled(False)
            self.embed_meta_check.setEnabled(False)
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
            self.format_combo.setEnabled(True)
            self.embed_cover_check.setEnabled(True)
            self.embed_meta_check.setEnabled(True)
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
        fmt = self.format_combo.currentData() or "best"
        fmt_label = self.format_combo.currentText()
        embed_art = self.embed_cover_check.isChecked()
        embed_meta = self.embed_meta_check.isChecked()
        settings = load_settings()
        out_dir = settings.get("download_dir", str(DEFAULT_DOWNLOADS))

        job = None
        if self._current_info:
            try:
                job = DownloadJob.create(
                    info=self._current_info,
                    kind="audio",
                    quality_label=fmt_label,
                    audio_format=fmt,
                    output_dir=out_dir,
                    thumbnail_bytes=self.info_card.thumb_bytes,
                )
            except Exception as exc:
                get_logger().warning(f"Could not build DownloadJob snapshot for audio: {exc}")

        item = AudioQueueItem(
            url=url,
            title=title,
            fmt=fmt,
            fmt_label=fmt_label,
            embed_art=embed_art,
            embed_meta=embed_meta,
            status="waiting",
            job=job,
        )
        self._queue.append(item)
        self._render_queue_ui()

    def _render_queue_ui(self) -> None:
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

            title_lbl = QLabel(f"{item.title} ({item.fmt_label})", row)
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
                remove_btn.clicked.connect(lambda _, it=item: self._remove_queue_item(it))
                row_layout.addWidget(remove_btn)

            self.queue_layout.addWidget(row)

    def _remove_queue_item(self, item: AudioQueueItem) -> None:
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
        cmd = build_audio_cmd(
            next_item.url,
            fmt=next_item.fmt,
            out_dir=out_dir,
            job_id=job_id,
        )
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
            is_dual_stream=False,
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

        title_saved = self._active_item.title if self._active_item else "audio"
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
                    logger.error(f"Failed to save audio history from job: {exc}")
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
                            type="audio",
                            quality=self._active_item.fmt_label if self._active_item else "MP3",
                            file_path=str(file_path),
                            size_bytes=size_bytes,
                            duration=0,
                            video_id=vid_id,
                        )
                    )
                except Exception as exc:
                    logger.error(f"Failed to save fallback audio history item: {exc}")

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

        # Move to next item in queue
        self._process_queue()

    def _reset_buttons(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.download_btn.setEnabled(not self._is_offline)
        self.queue_btn.setEnabled(not self._is_offline)
