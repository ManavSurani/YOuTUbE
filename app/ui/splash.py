"""Splash screen with quiet startup flow and offline setup handling."""

import socket
import sys
import time
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)
from app.version import APP_NAME
from app.core.paths import BIN_DIR
from app.core.settings import load_settings, save_settings
from app.core.tool_manager import missing_tools, install_tool, update_ytdlp
from app.core.shortcut import create_desktop_shortcut
from app.core.logger import get_logger


def check_internet(host: str = "youtube.com", port: int = 443, timeout: float = 3.0) -> bool:
    """Fast socket connection check for internet reachability."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


class StartupWorker(QThread):
    """Background startup coordinator executing startup flow off the UI thread."""

    status = Signal(str)
    progress = Signal(int)
    offline_blocked = Signal()
    finished = Signal()

    def run(self) -> None:
        logger = get_logger()
        logger.info("Startup sequence initiated.")

        # 1. Check internet
        self.status.emit("Connecting…")
        self.progress.emit(10)
        is_online = check_internet()

        # 2. Check tools
        missing = missing_tools()
        if missing:
            if not is_online:
                logger.warning("First-time setup blocked: missing tools and offline.")
                self.offline_blocked.emit()
                return

            total_missing = len(missing)
            for idx, tool_name in enumerate(missing):
                key = "yt-dlp" if "yt-dlp" in tool_name else ("ffmpeg" if "ffmpeg" in tool_name or "ffprobe" in tool_name else "deno")
                self.status.emit(f"Downloading components ({idx + 1}/{total_missing})…")
                install_tool(key, progress_cb=lambda p: self.progress.emit(20 + int(p * 0.6)))

        self.progress.emit(80)

        # 3. Check for 24h tool updates if online
        if is_online and not missing:
            settings = load_settings()
            last_check = settings.get("last_tool_check", 0)
            now = time.time()
            if now - last_check > 86400:  # 24 hours
                self.status.emit("Checking for tool updates…")
                update_ytdlp()
                settings["last_tool_check"] = int(now)
                save_settings(settings)

        self.progress.emit(90)

        # 4. Check Desktop shortcut creation (first run)
        create_desktop_shortcut()

        self.progress.emit(100)
        self.status.emit("Starting…")
        time.sleep(0.15)
        self.finished.emit()


class SplashScreen(QWidget):
    """Clean frameless splash screen with 150ms fade animations."""

    startup_completed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(360, 260)
        self._setup_ui()
        self._start_worker()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered 96px logo
        self.logo_label = QLabel(self)
        self.logo_label.setFixedSize(96, 96)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if hasattr(sys, "_MEIPASS"):
            logo_path = Path(sys._MEIPASS) / "assets" / "logo_512.png"
        else:
            logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_512.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                96, 96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(pix)
        layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # App title
        self.title_label = QLabel(APP_NAME, self)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Status text
        self.status_label = QLabel("Starting…", self)
        self.status_label.setProperty("role", "muted")
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)

        # 6px progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Retry button (visible only if first-run offline setup is blocked)
        self.retry_btn = QPushButton("Retry", self)
        self.retry_btn.setProperty("role", "secondary")
        self.retry_btn.setFixedHeight(32)
        self.retry_btn.setVisible(False)
        self.retry_btn.clicked.connect(self._on_retry)
        layout.addWidget(self.retry_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def _start_worker(self) -> None:
        self.worker = StartupWorker(self)
        self.worker.status.connect(self.status_label.setText)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.offline_blocked.connect(self._on_offline_blocked)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_offline_blocked(self) -> None:
        self.status_label.setText("Internet is required for first-time setup.")
        self.retry_btn.setVisible(True)

    def _on_retry(self) -> None:
        self.retry_btn.setVisible(False)
        self._start_worker()

    def _on_finished(self) -> None:
        # 150 ms fade-out animation
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(150)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._finish_close)
        self.anim.start()

    def _finish_close(self) -> None:
        self.close()
        self.startup_completed.emit()
