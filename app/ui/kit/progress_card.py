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
    Signal,
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

from app.core.file_actions import open_file, reveal_in_folder
from app.core.jobs import DownloadJob
from app.core.thumbnails import get_thumbnail_path
from app.ui.kit.anim import BASE, CELEBRATE, SHIMMER_MS, is_animations_enabled
from app.ui.kit.buttons import AnimatedButton, IconButton
from app.ui.kit.elided_label import ElidedLabel
from app.ui.kit.thumb_label import ThumbLabel
from app.ui.theme import ThemeManager, qcolor


class ModernProgressBar(QProgressBar):
    """10 px height progress bar with fully rounded ends and a subtle moving highlight across the filled chunk."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(10)
        self.setTextVisible(False)
        self._highlight_pos = 0.0
        self._shown = 0.0  # value as drawn: glides toward value(); logic always reads value()
        self._glow = 0.0   # 0..1, the "done" pulse
        self._value_anim: Optional[QPropertyAnimation] = None
        self._pulse_anim: Optional[QPropertyAnimation] = None
        ThemeManager.instance().changed.connect(self.update)

    def _get_shown(self) -> float:
        return self._shown

    def _set_shown(self, value: float) -> None:
        self._shown = value
        self.update()

    shown_value = Property(float, _get_shown, _set_shown)

    def _get_glow(self) -> float:
        return self._glow

    def _set_glow(self, value: float) -> None:
        self._glow = value
        self.update()

    glow = Property(float, _get_glow, _set_glow)

    def setValue(self, value: int) -> None:
        super().setValue(value)
        target = float(self.value())
        if self._value_anim is not None:
            self._value_anim.stop()
            self._value_anim = None
        if target <= self._shown or not is_animations_enabled():
            self._set_shown(target)  # resets and reduced motion jump at once
            return
        self._value_anim = QPropertyAnimation(self, b"shown_value", self)
        self._value_anim.setDuration(BASE)
        self._value_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._value_anim.setStartValue(self._shown)
        self._value_anim.setEndValue(target)
        self._value_anim.start()

    def pulse(self) -> None:
        """One soft glow over the filled bar when a download finishes."""
        if not is_animations_enabled():
            self._pulse_anim = None
            return
        self._pulse_anim = QPropertyAnimation(self, b"glow", self)
        self._pulse_anim.setDuration(CELEBRATE)
        self._pulse_anim.setKeyValueAt(0.0, 0.0)
        self._pulse_anim.setKeyValueAt(0.4, 1.0)
        self._pulse_anim.setKeyValueAt(1.0, 0.0)
        self._pulse_anim.start()

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

        # 1. Background groove
        groove_path = QPainterPath()
        groove_path.addRoundedRect(0.0, 0.0, w, h, radius, radius)
        painter.fillPath(groove_path, qcolor("surface_hover"))

        # 2. Filled chunk
        val = self._shown
        max_val = max(1, self.maximum())
        chunk_w = w * (val / max_val)

        if chunk_w > 0:
            chunk_path = QPainterPath()
            chunk_path.addRoundedRect(0.0, 0.0, chunk_w, h, radius, radius)
            painter.fillPath(chunk_path, qcolor("accent"))

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

            if self._glow > 0:
                painter.fillPath(chunk_path, QColor(255, 255, 255, int(80 * self._glow)))

        painter.end()


class ProgressCard(QWidget):
    """Full-featured progress card for active download with thumbnail, stats, and real folder name."""

    pause_toggled = Signal()
    DONE_VISIBLE_MS = 4000

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "ProgressCard { background: transparent; border: none; } "
            "QLabel { font-family: 'Segoe UI'; }"
        )

        self._active_job: Optional[DownloadJob] = None
        self._max_percent = 0.0
        self._last_done = 0
        self._last_total = 0
        self._last_speed = ""
        self._last_eta = ""
        self._last_stage = ""

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

        self.title_lbl = ElidedLabel(parent=self.header_widget)
        self.title_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.title_lbl.setProperty("role", "strong")
        h_layout.addWidget(self.title_lbl, 1)

        # While downloading: pause / resume. When done: open the file or its folder.
        self.pause_btn = IconButton("pause", size=28, tooltip="Pause (Space)", parent=self.header_widget)
        self.pause_btn.clicked.connect(self.pause_toggled.emit)
        self.pause_btn.setVisible(False)
        h_layout.addWidget(self.pause_btn)

        self.open_btn = AnimatedButton("Open", role="ghost", parent=self.header_widget)
        self.open_btn.clicked.connect(lambda: open_file(self._final_path))
        self.folder_btn = AnimatedButton("Show in folder", role="ghost", parent=self.header_widget)
        self.folder_btn.clicked.connect(lambda: reveal_in_folder(self._final_path))
        for btn in (self.open_btn, self.folder_btn):
            btn.setVisible(False)
            h_layout.addWidget(btn)
        self._final_path = ""

        layout.addWidget(self.header_widget)

        # 2. Stage and Percent Line
        meta_layout = QHBoxLayout()
        self.stage_label = QLabel("Starting…", self)
        self.stage_label.setTextFormat(Qt.TextFormat.PlainText)
        self.stage_label.setProperty("role", "meta")
        meta_layout.addWidget(self.stage_label, 1)

        self.percent_label = QLabel("0%", self)
        self.percent_label.setTextFormat(Qt.TextFormat.PlainText)
        self.percent_label.setProperty("role", "strong")
        meta_layout.addWidget(self.percent_label)
        layout.addLayout(meta_layout)

        # 3. Progress bar (10 px, fully rounded, animated highlight)
        self.progress_bar = ModernProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Subtle moving highlight animation across filled chunk
        self.highlight_anim = QPropertyAnimation(self.progress_bar, b"highlight_pos", self)
        self.highlight_anim.setDuration(SHIMMER_MS)
        self.highlight_anim.setStartValue(0.0)
        self.highlight_anim.setEndValue(1.0)
        self.highlight_anim.setLoopCount(-1)
        self._highlight_anim = self.highlight_anim
        self.anim = self.highlight_anim
        self._anim = self.highlight_anim

        # 4. Details line (Speed • ETA • Size)
        self.stats_label = QLabel("", self)
        self.stats_label.setTextFormat(Qt.TextFormat.PlainText)
        self.stats_label.setProperty("role", "meta")
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
        self._last_done = 0
        self._last_total = 0
        self._last_speed = ""
        self._last_eta = ""
        self._last_stage = "Starting…"
        self.title_lbl.setText(job.title)
        self.thumb.update_thumbnail(job.video_id, is_audio=(job.kind == "audio"))
        if job.thumbnail_bytes and (not job.video_id or get_thumbnail_path(job.video_id) is None):
            self.thumb.set_image_bytes(job.thumbnail_bytes)
        self.set_paused(False)
        self.pause_btn.setVisible(True)
        self.open_btn.setVisible(False)
        self.folder_btn.setVisible(False)
        self.stage_label.setText("Starting…")
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.stats_label.setText("")
        self.setVisible(True)
        self._start_highlight_anim()

    def set_stage(self, stage_text: str) -> None:
        self.stage_label.setText(stage_text)
        if stage_text != self._last_stage:
            prev_stage = self._last_stage
            self._last_stage = stage_text
            is_non_downloading = not stage_text.startswith("Downloading")
            is_stream_change = prev_stage.startswith("Downloading") and stage_text.startswith("Downloading")
            if is_non_downloading or is_stream_change:
                self._last_eta = ""
                if self.stats_label.text():
                    self._update_stats_label()

    def _update_stats_label(self, stats: str = "") -> None:
        speed_slot = self._last_speed if self._last_speed else "-- MB/s"

        if stats:
            size_slot = stats
        elif self._last_done > 0:
            done = self._last_done
            if self._last_total > 0:
                total = max(self._last_total, done)
                size_slot = self._fmt_pair(done, total)
            else:
                size_slot = self._fmt_bytes(done)
        else:
            size_slot = "calculating…"

        if self._last_eta:
            eta_slot = self._last_eta if self._last_eta.startswith("ETA ") else f"ETA {self._last_eta}"
        else:
            eta_slot = "ETA --:--"

        self.stats_label.setText(f"{speed_slot} • {size_slot} • {eta_slot}")

    def set_progress(
        self,
        percent: float,
        speed: str = "",
        eta: str = "",
        done_bytes: int = 0,
        total_bytes: int = 0,
        stats: str = "",
    ) -> None:
        if percent > 0 or self._max_percent == 0:
            self._max_percent = percent
        pct_int = int(self._max_percent)
        self.progress_bar.setValue(pct_int)
        self.percent_label.setText(f"{pct_int}%")

        if done_bytes > 0:
            self._last_done = done_bytes
        if total_bytes > 0:
            self._last_total = total_bytes
        if speed:
            self._last_speed = speed
            if eta:
                self._last_eta = eta
            self._start_highlight_anim()
        else:
            # Stall / missing speed: clear stale ETA and stop the shimmer (nothing is moving)
            self._last_eta = ""
            self._stop_highlight_anim()

        self._update_stats_label(stats=stats)

    def show_done(self, out_dir: str = "", final_path: str = "") -> None:
        """Show completion with real folder name (B15 fix) and real size on disk."""
        self._stop_highlight_anim()
        folder_name = Path(out_dir).name if out_dir else "Downloads"
        self.progress_bar.setValue(100)
        self.progress_bar.pulse()
        self.percent_label.setText("100%")
        size = Path(final_path).stat().st_size if final_path and Path(final_path).is_file() else 0
        saved = f"Saved to {folder_name}"
        self.stage_label.setText(f"{saved} · {self._fmt_bytes(size)}" if size else saved)
        self.stats_label.setText("")
        self._final_path = final_path if size else ""
        self.pause_btn.setVisible(False)
        self.open_btn.setVisible(bool(self._final_path))
        self.folder_btn.setVisible(bool(self._final_path))
        self.setVisible(True)
        self._collapse_timer.start(self.DONE_VISIBLE_MS)

    def set_paused(self, paused: bool) -> None:
        self.pause_btn.icon_name = "play" if paused else "pause"
        self.pause_btn.setToolTip("Resume (Space)" if paused else "Pause (Space)")
        self.pause_btn.update()

    def enterEvent(self, event) -> None:
        # Keep the Done card while the pointer is on it
        super().enterEvent(event)
        if self._collapse_timer.isActive():
            self._collapse_timer.stop()
            self._hold_done = True

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if getattr(self, "_hold_done", False):
            self._hold_done = False
            self._collapse_timer.start(1500)

    def reset(self) -> None:
        self._stop_highlight_anim()
        self._collapse_timer.stop()
        self._active_job = None
        self._max_percent = 0.0
        self._last_done = 0
        self._last_total = 0
        self._last_speed = ""
        self._last_eta = ""
        self._last_stage = ""
        self.stats_label.setText("")
        self.pause_btn.setVisible(False)
        self.open_btn.setVisible(False)
        self.folder_btn.setVisible(False)
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

    @staticmethod
    def _fmt_pair(done: int, total: int) -> str:
        """Format done / total in the total's unit so the done number counts up smoothly."""
        units = ["B", "KB", "MB", "GB", "TB"]
        div = 1.0
        idx = 0
        while total / div >= 1024.0 and idx < len(units) - 1:
            div *= 1024.0
            idx += 1
        dec = 2 if idx >= 3 else 1
        return f"{done / div:.{dec}f} {units[idx]} / {total / div:.{dec}f} {units[idx]}"
