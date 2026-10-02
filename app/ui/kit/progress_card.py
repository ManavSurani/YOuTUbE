"""ProgressCard component skeleton (expanded and completed in Phase 4)."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ProgressCard(QWidget):
    """Progress card displaying active download stage, thick bar, speed, and ETA."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "ProgressCard { background-color: #1A1A1A; border-radius: 8px; } "
            "QLabel { font-family: 'Segoe UI'; } "
            "QProgressBar { background-color: #282828; border: none; border-radius: 4px; min-height: 8px; max-height: 8px; text-align: right; } "
            "QProgressBar::chunk { background-color: #FF0000; border-radius: 4px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header: Stage and Percent
        header_layout = QHBoxLayout()
        self.stage_label = QLabel("Starting…", self)
        self.stage_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        self.percent_label = QLabel("0%", self)
        self.percent_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        header_layout.addWidget(self.stage_label, 1)
        header_layout.addWidget(self.percent_label)
        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Sub-stats line: 63% • 12.4 MB/s • ETA 01:20 • 1.2 / 1.9 GB
        self.stats_label = QLabel("", self)
        self.stats_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        layout.addWidget(self.stats_label)

    def set_progress(self, percent: float, speed: str = "", eta: str = "", stats: str = "") -> None:
        pct_int = int(percent)
        self.progress_bar.setValue(pct_int)
        self.percent_label.setText(f"{pct_int}%")

        parts = []
        if speed:
            parts.append(speed)
        if eta:
            parts.append(f"ETA {eta}")
        if stats:
            parts.append(stats)
        self.stats_label.setText(" • ".join(parts))

    def set_stage(self, stage: str) -> None:
        self.stage_label.setText(stage)

    def reset(self) -> None:
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.stage_label.setText("Starting…")
        self.stats_label.setText("")
