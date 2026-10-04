"""ProgressCard component with smooth progress, job info header, and real folder completion text.

Fixes B15 (uses real folder name instead of hardcoded 'Downloads').
Provides monotonic progress bar and stage feedback.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
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


class ModernProgressBar(QProgressBar):
    """10 px height progress bar with fully rounded ends and a subtle moving highlight across the filled chunk."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(10)
        self.setTextVisible(False)
        self._highlight_pos = 0.0

    @Property(float)
    def highlight_pos(self) -> float:
        return self._highlight_pos

    @highlight_pos.setter
    def highlight_pos(self, pos: float) -> None:
        self._highlight_pos = pos
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0  # 5 px fully rounded ends

        # 1. Background groove (#282828)
        groove_path = QPainterPath()
        groove_path.addRoundedRect(0.0, 0.0, w, h, radius, radius)
        painter.fillPath(groove_path, QColor("#282828"))

        # 2. Filled chunk (#FF0000)
        val = self.value()
        max_val = max(1, self.maximum())
        chunk_w = w * (val / max_val)

        if chunk_w > 0:
            chunk_path = QPainterPath()
            chunk_path.addRoundedRect(0.0, 0.0, chunk_w, h, radius, radius)
            painter.fillPath(chunk_path, QColor("#FF0000"))

            # 3. Subtle moving highlight across the filled chunk
            if chunk_w >= 10:
                painter.save()
                painter.setClipPath(chunk_path)

                hl_center = chunk_w * self._highlight_pos
                hl_width = max(24.0, chunk_w * 0.35)

                grad = QLinearGradient(hl_center - hl_width / 2.0, 0.0, hl_center + hl_width / 2.0, 0.0)
                grad.setColorAt(0.0, QColor(255, 255, 255, 0))
                grad.setColorAt(0.5, QColor(255, 255, 255, 50))
                grad.setColorAt(1.0, QColor(255, 255, 255, 0))

                painter.fillRect(0, 0, int(chunk_w), int(h), grad)
                painter.restore()

        painter.end()


class ProgressCard(QWidget):
    """Full-featured progress card for active download with thumbnail, stats, and real folder name."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "ProgressCard { background: transparent; border: none; } "
            "QLabel { font-family: 'Segoe UI'; }"
        )

        self._active_job: Optional[DownloadJob] = None
        self._max_percent = 0.0

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._on_collapse_timeout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
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

        # 3. Progress bar (10 px, fully rounded, animated highlight)
        self.progress_bar = ModernProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Subtle moving highlight animation across filled chunk
        self.highlight_anim = QPropertyAnimation(self.progress_bar, b"highlight_pos", self)
        self.highlight_anim.setDuration(1600)
        self.highlight_anim.setStartValue(0.0)
        self.highlight_anim.setEndValue(1.0)
        self.highlight_anim.setLoopCount(-1)
        self._highlight_anim = self.highlight_anim
        self.anim = self.highlight_anim
        self._anim = self.highlight_anim

        # 4. Details line (Speed • ETA • Size)
        self.stats_label = QLabel("", self)
        self.stats_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(self.stats_label)

        self.setVisible(False)

    def _start_highlight_anim(self) -> None:
        if hasattr(self, "highlight_anim") and self.isVisible() and self._active_job is not None:
            if self.highlight_anim.state() != QPropertyAnimation.State.Running:
                self.highlight_anim.start()

    def _stop_highlight_anim(self) -> None:
        if hasattr(self, "highlight_anim") and self.highlight_anim.state() == QPropertyAnimation.State.Running:
            self.highlight_anim.stop()

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if not visible:
            self._stop_highlight_anim()
        elif self._active_job is not None:
            self._start_highlight_anim()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._stop_highlight_anim()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._active_job is not None:
            self._start_highlight_anim()

    def bind_job(self, job: DownloadJob) -> None:
        """Bind active job metadata to card."""
        self._collapse_timer.stop()
        self._active_job = job
        self._max_percent = 0.0
        self.title_lbl.setText(job.title)
        self.thumb.update_thumbnail(job.video_id, is_audio=(job.kind == "audio"))
        self.stage_label.setText("Starting…")
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.stats_label.setText("")
        self.setVisible(True)
        self._start_highlight_anim()

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
        self._stop_highlight_anim()
        folder_name = Path(out_dir).name if out_dir else "Downloads"
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.stage_label.setText(f"Done. Saved to {folder_name}.")
        self.stats_label.setText("")
        self.setVisible(True)
        self._collapse_timer.start(1200)

    def reset(self) -> None:
        self._stop_highlight_anim()
        self._collapse_timer.stop()
        self._active_job = None
        self._max_percent = 0.0
        self.setVisible(False)

    def _on_collapse_timeout(self) -> None:
        try:
            self.reset()
        except RuntimeError:
            pass

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
