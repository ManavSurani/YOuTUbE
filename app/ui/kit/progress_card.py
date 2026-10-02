"""ProgressCard component with smooth progress, job info header, and real folder completion text.

Fixes B15 (uses real folder name instead of hardcoded 'Downloads').
Provides monotonic progress bar and stage feedback.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.core.jobs import DownloadJob
from app.ui.kit.anim import is_animations_enabled
from app.ui.kit.thumb_label import ThumbLabel


class ProgressCard(QWidget):
    """Full-featured progress card for active download with thumbnail, stats, and real folder name."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setStyleSheet(
            "ProgressCard { background-color: #1A1A1A; border-radius: 8px; } "
            "QLabel { font-family: 'Segoe UI'; } "
            "QProgressBar { background-color: #282828; border: none; border-radius: 4px; min-height: 8px; max-height: 8px; text-align: right; } "
            "QProgressBar::chunk { background-color: #FF0000; border-radius: 4px; }"
        )

        self._active_job: Optional[DownloadJob] = None
        self._max_percent = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 1. Header with Thumbnail and Title
        self.header_widget = QWidget(self)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        self.thumb = ThumbLabel(size=(48, 27), radius=4, parent=self.header_widget)
        h_layout.addWidget(self.thumb)

        self.title_lbl = QLabel(self.header_widget)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        h_layout.addWidget(self.title_lbl, 1)

        layout.addWidget(self.header_widget)

        # 2. Stage and Percent Line
        meta_layout = QHBoxLayout()
        self.stage_label = QLabel("Starting…", self)
        self.stage_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #AAAAAA;")
        meta_layout.addWidget(self.stage_label, 1)

        self.percent_label = QLabel("0%", self)
        self.percent_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #FFFFFF;")
        meta_layout.addWidget(self.percent_label)
        layout.addLayout(meta_layout)

        # 3. Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 4. Details line (Speed • ETA • Size)
        self.stats_label = QLabel("", self)
        self.stats_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(self.stats_label)

    def bind_job(self, job: DownloadJob) -> None:
        """Bind active job metadata to card."""
        self._active_job = job
        self._max_percent = 0.0
        self.title_lbl.setText(job.title)
        self.thumb.update_thumbnail(job.video_id, is_audio=(job.kind == "audio"))
        self.stage_label.setText("Starting…")
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.stats_label.setText("")
        self.setVisible(True)

    def set_stage(self, stage_text: str) -> None:
        self.stage_label.setText(stage_text)

    def set_progress(
        self,
        percent: float,
        speed: str = "",
        eta: str = "",
        done_bytes: int = 0,
        total_bytes: int = 0,
        stats: str = "",
    ) -> None:
        # Never go backwards
        self._max_percent = max(self._max_percent, percent)
        pct_int = int(self._max_percent)
        self.progress_bar.setValue(pct_int)
        self.percent_label.setText(f"{pct_int}%")

        details = []
        if speed:
            details.append(speed)
        if eta:
            details.append(f"ETA {eta}")
        if stats:
            details.append(stats)
        elif done_bytes > 0 and total_bytes > 0:
            details.append(f"{self._fmt_bytes(done_bytes)} / {self._fmt_bytes(total_bytes)}")
        elif done_bytes > 0:
            details.append(self._fmt_bytes(done_bytes))

        self.stats_label.setText(" • ".join(details))

    def show_done(self, out_dir: str = "") -> None:
        """Show completion with real folder name (B15 fix)."""
        folder_name = Path(out_dir).name if out_dir else "Downloads"
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.stage_label.setText(f"Done. Saved to {folder_name}.")
        self.stats_label.setText("")

    def reset(self) -> None:
        self._active_job = None
        self._max_percent = 0.0
        self.setVisible(False)

    @staticmethod
    def _fmt_bytes(b: int) -> str:
        if b <= 0:
            return ""
        units = ["B", "KB", "MB", "GB", "TB"]
        v = float(b)
        idx = 0
        while v >= 1024.0 and idx < len(units) - 1:
            v /= 1024.0
            idx += 1
        return f"{v:.1f} {units[idx]}"
